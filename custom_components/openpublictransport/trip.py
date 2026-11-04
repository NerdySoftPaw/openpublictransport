"""Trip planner for Open Public Transport integration.

Provides both a service (on-demand) and a sensor (polling) for
route planning from A to B with connections and transfers.
"""

import asyncio
import hashlib
import inspect
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from openpublictransport import (
    ApiConnectionError,
    ApiError,
    ApiResponseError,
    ApiTimeoutError,
    AuthenticationError,
)
from openpublictransport.providers import get_all_provider_ids, get_provider_class
from openpublictransport.providers.hafas_mgate_base import HafasMgateBaseProvider

_LOGGER = logging.getLogger(__name__)

# EFA Trip API base URLs (same as DM base URLs but different endpoint)
EFA_TRIP_ENDPOINTS = {
    "vrr": "https://openservice.vrr.de/static03/XML_TRIP_REQUEST2",
    "kvv": "https://projekte.kvv-efa.de/sl3-alone/XML_TRIP_REQUEST2",
    "hvv": "https://hvv.efa.de/efa/XML_TRIP_REQUEST2",
    "mvv": "https://efa.mvv-muenchen.de/ng/XML_TRIP_REQUEST2",
    "vvs": "https://www3.vvs.de/mngvvs/XML_TRIP_REQUEST2",
    "vgn": "https://efa.vgn.de/vgnExt_oeffi/XML_TRIP_REQUEST2",
    "vagfr": "https://efa.vagfr.de/vagfr3/XML_TRIP_REQUEST2",
    "vrn": "https://www.vrn.de/mngvrn/XML_TRIP_REQUEST2",
    "vvo": "https://efa.vvo-online.de/VMSSL3/XML_TRIP_REQUEST2",
    "ding": "https://www.ding.eu/ding3/XML_TRIP_REQUEST2",
    "avv_augsburg": "https://fahrtauskunft.avv-augsburg.de/efa/XML_TRIP_REQUEST2",
    "rvv": "https://efa.rvv.de/efa/XML_TRIP_REQUEST2",
    "bsvg": "https://bsvg.efa.de/bsvagstd/XML_TRIP_REQUEST2",
    "nwl": "https://westfalenfahrplan.de/nwl-efa/XML_TRIP_REQUEST2",
    "vmv": "https://fahrplanauskunft-mv.de/vmv-efa/XML_TRIP_REQUEST2",
    "gvh": "https://www.efa.de/efa/XML_TRIP_REQUEST2",
}

# OTP-based providers plan trips through their own endpoints, not EFA.
OTP2_TRIP_PROVIDERS = frozenset({"otp_custom"})
OTP_REST_TRIP_PROVIDERS = frozenset({"vbn_otp"})

# Every modern HAFAS mgate provider plans trips through its TripSearch service.
# Derived from the library so a new mgate network is trip-capable right away.
HAFAS_MGATE_TRIP_PROVIDERS = frozenset(
    provider_id
    for provider_id in get_all_provider_ids()
    if issubclass(get_provider_class(provider_id) or object, HafasMgateBaseProvider)
)

# Every provider that can plan a trip. Providers outside this set (legacy HAFAS,
# FPTF, TRIAS, GTFS-RT …) are departure monitors only — the config flow refuses a
# trip entry for them and the docs are checked against this set (issue #80).
TRIP_CAPABLE_PROVIDERS = (
    frozenset(EFA_TRIP_ENDPOINTS) | OTP2_TRIP_PROVIDERS | OTP_REST_TRIP_PROVIDERS | HAFAS_MGATE_TRIP_PROVIDERS
)


def supports_trip_planning(provider: Optional[str]) -> bool:
    """Return True when the provider can plan trips."""
    return provider in TRIP_CAPABLE_PROVIDERS


def _efa_id_type(efa_id: str) -> str:
    """Return the EFA location type an ID has to be sent as.

    An EFA location ID carries its kind in front of the first colon: `streetID:`
    for a street or an address, `poiID:` for a point of interest, `suburbID:` for
    a district, `coord:` for a plain coordinate. A stop is the exception — its ID
    is either a DELFI one (`de:08111:6056`) or provider-internal (`5030028`,
    `5005296:$51`).

    That matters because EFA accepts `type=stop` only for a real stop ID.
    Anything else is answered with `origin: stop invalid` and no journeys at all,
    so the trip sensor sits on "No connections" forever with nothing in the log —
    and the other kinds do reach here: the stopfinder is queried with
    `type_sf=any` whenever the search term contains a comma, and its locations
    are passed through unfiltered. Sent as `any` they resolve, and the footpath
    from an address to the first stop gets planned, which is the point of picking
    an address as the origin.
    """
    kind = efa_id.split(":", 1)[0].lower()
    return "any" if kind == "coord" or kind.endswith("id") else "stop"


# OTP 2.x planConnection query — routes stop-to-stop via stopLocationId, so no
# coordinates and no street-network access/egress are needed (works on a
# transit-only graph). %s = origin id, dest id, optional dateTime clause,
# optional via clause.
_GRAPHQL_PLAN_CONNECTION = """{
  planConnection(
    origin:      { location: { stopLocation: { stopLocationId: "%s" } } }
    destination: { location: { stopLocation: { stopLocationId: "%s" } } }
    %s
    %s
    first: 3
  ) {
    edges { node {
      duration
      numberOfTransfers
      legs {
        mode
        transitLeg
        duration
        from { name }
        to   { name }
        start { scheduledTime estimated { time delay } }
        end   { scheduledTime estimated { time delay } }
        trip { route { shortName } }
        route { shortName }
      }
    } }
  }
}"""

# OTP GTFS mode → unified product name
_OTP_MODE_TO_PRODUCT = {
    "BUS": "bus",
    "COACH": "bus",
    "RAIL": "train",
    "TRAM": "tram",
    "SUBWAY": "subway",
    "FERRY": "ferry",
    "GONDOLA": "tram",
    "FUNICULAR": "train",
    "CABLE_CAR": "tram",
    "WALK": "walk",
}

# EFA models the walk to the platform (or between two nearby stations) as a leg
# of the journey. Such a leg ends exactly when the connecting vehicle departs,
# so rating it like a transfer marks every walk-in journey as "missed" — which
# is what made the trip planner unusable in issue #72. Detected by product
# class, with a name fallback for providers that omit the class.
_NON_TRANSIT_PRODUCT_CLASSES = {98, 99, 100}
_NON_TRANSIT_PRODUCT_NAMES = {
    "footpath",
    "fussweg",
    "fußweg",
    "walk",
    "gesicherter anschluss",
    "bicycle",
    "fahrrad",
}


def _is_transit_product(product: Dict[str, Any]) -> bool:
    """Return True when an EFA product describes an actual vehicle."""
    if product.get("class") in _NON_TRANSIT_PRODUCT_CLASSES:
        return False
    return str(product.get("name") or "").strip().lower() not in _NON_TRANSIT_PRODUCT_NAMES


# EFA product name → unified transport type, for providers whose numeric product
# class is missing from their mapping. Mirrors the library's departure parser so
# a leg is typed the same way whether it arrives on the departure board or in a
# journey.
_EFA_NAME_TYPE_PATTERNS = (
    (("u-bahn", "u_bahn", "ubahn", "subway", "metro"), "subway"),
    (("straßenbahn", "strassenbahn", "stadtbahn", "tram"), "tram"),
    (("fähre", "faehre", "schiff", "ferry"), "ferry"),
    (("bus", "ast", "ruf", "ersatz"), "bus"),
    (("bahn", "zug", "train"), "train"),
)


def _transport_type_from_name(name: str) -> str:
    """Best-effort unified transport type from an EFA product name."""
    lowered = (name or "").lower()
    for needles, transport_type in _EFA_NAME_TYPE_PATTERNS:
        if any(needle in lowered for needle in needles):
            return transport_type
    return "unknown"


def _leg_transport_type(product: Dict[str, Any], type_mapping: Optional[Dict[Any, str]]) -> str:
    """Return a leg's unified transport type ("bus", "subway", "walk", …).

    Journeys carry the provider's own product *name* ("Stadtbahn", "Bus"), which
    is useless for matching the transport types configured on the entry. The
    numeric product class resolves through the provider's mapping, exactly like a
    departure does; an unmapped class falls back to the name, and anything still
    unrecognised stays "unknown" so filters can let it pass rather than drop a
    connection they cannot judge (issue #87).
    """
    if not _is_transit_product(product):
        return "walk"
    transport_type = (type_mapping or {}).get(product.get("class"), "unknown")
    if transport_type == "unknown":
        transport_type = _transport_type_from_name(str(product.get("name") or ""))
    return transport_type


def _rate_transfers(transit_legs: List[Dict[str, Any]]) -> tuple[bool, str, Optional[int]]:
    """Rate a journey's transfers from the gaps between consecutive transit legs.

    ``transit_legs`` must hold vehicle legs only, in travel order, each carrying
    the internal ``_departure_s`` / ``_arrival_s`` epoch keys. Walking legs are
    not transfers and must be filtered out by the caller.

    Each leg a traveller changes out of is annotated with ``transfer_minutes``,
    the wait before the next vehicle leaves. The journey-wide minimum says how
    tight the journey is; this says where, which is what a traveller standing on
    the platform after one of the legs actually needs.

    Returns ``(connection_feasible, transfer_risk, min_transfer_time)``; the
    minimum transfer time is ``None`` for a journey without a transfer.
    """
    feasible = True
    risk = "low"
    min_transfer: Optional[int] = None

    for current, following in zip(transit_legs, transit_legs[1:]):
        arrival = current.get("_arrival_s") or 0
        departure = following.get("_departure_s") or 0
        if not arrival or not departure:
            continue
        gap_min = int((departure - arrival) // 60)
        current["transfer_minutes"] = gap_min
        if min_transfer is None or gap_min < min_transfer:
            min_transfer = gap_min
        if gap_min <= 0:
            feasible = False
            risk = "missed"
        elif gap_min <= 3 and risk != "missed":
            risk = "high"
        elif gap_min <= 5 and risk not in ("missed", "high"):
            risk = "medium"

    return feasible, risk, min_transfer


def _journey_bounds(legs: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    """Return a journey's start and end as local ISO-8601 timestamps.

    The start is the first leg's departure — including an initial walk, because
    that is when the traveller has to set off. Consumers need the full timestamp
    (not just ``HH:MM``) to tell a connection that is still ahead from one that
    has already left.
    """
    return (
        _epoch_to_local_iso(legs[0].get("_departure_s") or 0),
        _epoch_to_local_iso(legs[-1].get("_arrival_s") or 0),
    )


def _journey_id(legs: List[Dict[str, Any]]) -> str:
    """Return a stable identifier for a journey, derived from its own legs.

    A caller that showed a summary and later asks for the detail has to say
    which connection it means, and no combination of the summary's own fields
    says it reliably: a board regularly holds two connections that leave and
    arrive on the same minute with the same number of changes, and two routes
    on parallel lines can agree on all of that and still be different journeys.

    The identity comes from the route itself — each leg's line, where it is
    boarded and when it is *timetabled* to leave. Planned times are used on
    purpose: an estimate moves as the delay is revised, and an id that changed
    between two polls would not identify anything. Walking legs carry no line,
    which is why the origin and the time are in the digest too.
    """
    material = ";".join(
        f"{leg.get('line', '')}|{leg.get('origin', '')}|{leg.get('departure_planned', '')}" for leg in legs
    )
    # A name, not a secret: SHA-1 is only a short, stable digest here.
    return hashlib.sha1(material.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def _with_ids(journeys: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """Stamp every journey with its id, whichever provider parsed it."""
    if journeys is None:
        return None
    for journey in journeys:
        journey["id"] = _journey_id(journey.get("legs", []))
    return journeys


def _epoch_to_local_iso(epoch_s: float) -> Optional[str]:
    """Format an epoch timestamp as a local ISO-8601 string (None if unknown)."""
    if not epoch_s:
        return None
    try:
        return dt_util.as_local(datetime.fromtimestamp(epoch_s, tz=timezone.utc)).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


class TripOptionNotSupportedError(Exception):
    """A trip option (via stop, dwell time) the provider cannot honour.

    Raised instead of quietly planning without it (issue #110): a journey that
    skips the stop the user asked for looks like an answer and is not one.
    ``option`` is ``"via"`` or ``"dwell"``.
    """

    def __init__(self, provider: str, option: str, detail: str = "") -> None:
        self.provider = provider
        self.option = option
        what = "a via stop" if option == "via" else "a dwell time at the via stop"
        super().__init__(f"{provider} does not support {what}" + (f" ({detail})" if detail else ""))


def via_support(provider: Optional[str]) -> tuple[bool, bool]:
    """Return ``(via, dwell)``: whether ``provider`` can route through a via stop
    and keep a minimum stay there (issue #110).

    EFA routes through a via stop natively; its ``dwellTime_via`` is documented
    but ignored by every server tried (VRR, VVS, KVV, MVV), so the stay is
    emulated with two requests (see :func:`_async_plan_trip_efa_with_dwell`).
    HAFAS mgate and OTP2 support both. The legacy OTP REST endpoint supports
    neither.
    """
    if provider in EFA_TRIP_ENDPOINTS or provider in HAFAS_MGATE_TRIP_PROVIDERS or provider in OTP2_TRIP_PROVIDERS:
        return True, True
    return False, False


def _check_via_options(provider: str, via_id: Optional[str], via_name: Optional[str], dwell: int) -> None:
    """Raise when a via stop or a dwell time is asked of a provider without it."""
    can_via, can_dwell = via_support(provider)
    if (via_id or via_name) and not can_via:
        raise TripOptionNotSupportedError(provider, "via")
    if dwell and not (via_id or via_name):
        raise ValueError("A dwell time needs a via stop")
    if dwell and not can_dwell:
        raise TripOptionNotSupportedError(provider, "dwell")


async def async_plan_trip(
    hass: HomeAssistant,
    provider: str,
    origin_name: str,
    origin_place: str,
    dest_name: str,
    dest_place: str,
    departure_time: Optional[datetime] = None,
    origin_id: Optional[str] = None,
    dest_id: Optional[str] = None,
    api_key: Optional[str] = None,
    custom_url: Optional[str] = None,
    arrival_time: Optional[datetime] = None,
    via_id: Optional[str] = None,
    via_name: Optional[str] = None,
    via_place: Optional[str] = None,
    via_dwell_minutes: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip from origin to destination.

    Dispatches to OTP2 GraphQL for otp_custom, OTP REST for vbn_otp, the
    HAFAS mgate TripSearch service for mgate providers, and EFA XML for all
    other supported providers.
    Uses the stored location IDs when available (more reliable), falls back to
    name+place search.

    ``arrival_time``, when given, switches every backend into "arrive by" mode
    (latest departure that still lands by that time) and takes priority over
    ``departure_time`` — the two are mutually exclusive query modes.

    ``via_id`` (or ``via_name``/``via_place``) routes every connection through
    that stop, and ``via_dwell_minutes`` keeps at least that long a stay there
    (issue #110). A provider that cannot do either raises
    :class:`TripOptionNotSupportedError` rather than planning without it.
    Returns a list of journey options, each with legs and transfer info.
    """
    from openpublictransport import get_provider

    dwell = max(0, int(via_dwell_minutes or 0))
    _check_via_options(provider, via_id, via_name, dwell)

    # OTP2 GraphQL providers (self-hosted instances)
    if provider in OTP2_TRIP_PROVIDERS:
        if not origin_id or not dest_id or ((via_name or dwell) and not via_id):
            _LOGGER.warning("OTP2 trip planning requires stop IDs — search for stops first")
            return None
        session = async_get_clientsession(hass)
        provider_instance = get_provider(provider, session, api_key=api_key, custom_url=custom_url)
        return _with_ids(
            await _async_plan_trip_otp2_graphql(
                origin_id,
                dest_id,
                departure_time,
                provider_instance,
                arrival_time,
                via_id=via_id,
                via_dwell_minutes=dwell,
            )
        )

    # HAFAS mgate — TripSearch between two stop ids
    if provider in HAFAS_MGATE_TRIP_PROVIDERS:
        if not origin_id or not dest_id or (via_name and not via_id):
            _LOGGER.warning("HAFAS trip planning requires stop IDs — search for stops first")
            return None
        provider_instance = get_provider(provider, async_get_clientsession(hass))
        kwargs: Dict[str, Any] = {"departure_time": departure_time, "arrival_time": arrival_time}
        if via_id:
            # The library learnt via stops in 0.3.4; an older one would raise a
            # TypeError here, so say what is missing instead.
            params = inspect.signature(provider_instance.search_trips).parameters
            takes_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
            if "via_id" not in params and not takes_kwargs:
                raise TripOptionNotSupportedError(provider, "via", "needs python-openpublictransport 0.3.4")
            kwargs["via_id"] = via_id
            if dwell:
                kwargs["via_dwell_minutes"] = dwell
        trips = await provider_instance.search_trips(origin_id, dest_id, **kwargs)
        return _with_ids(_parse_hafas_trips(trips))

    # VBN OTP — legacy OTP REST plan endpoint
    if provider in OTP_REST_TRIP_PROVIDERS:
        if not origin_id or not dest_id:
            _LOGGER.warning("VBN OTP trip planning requires stop IDs — search for stops first")
            return None
        session = async_get_clientsession(hass)
        provider_instance = get_provider(provider, session, api_key=api_key)
        return _with_ids(
            await _async_plan_trip_otp(origin_id, dest_id, departure_time, provider_instance, arrival_time)
        )

    # EFA providers
    base_url = EFA_TRIP_ENDPOINTS.get(provider)
    if not base_url:
        _LOGGER.debug("Trip planning not supported for provider: %s", provider)
        return None

    session = async_get_clientsession(hass)
    # The trip endpoint is queried directly rather than through the library, so
    # the provider is instantiated purely for its product-class mapping — that is
    # what lets a leg be matched against the entry's transport types (issue #87).
    efa_provider = get_provider(provider, session)
    efa = _EfaTripRequest(
        session=session,
        provider=provider,
        base_url=base_url,
        type_mapping=efa_provider.get_transport_type_mapping() if efa_provider else {},
        timezone_name=efa_provider.get_timezone() if efa_provider else None,
    )
    origin = _EfaPoint(origin_id, origin_name, origin_place)
    destination = _EfaPoint(dest_id, dest_name, dest_place)
    via = _EfaPoint(via_id, via_name or "", via_place or "") if (via_id or via_name) else None

    if via is not None and dwell:
        journeys = await _async_plan_trip_efa_with_dwell(
            efa, origin, via, destination, dwell, departure_time, arrival_time
        )
    else:
        journeys = await efa.plan(origin, destination, departure_time, arrival_time, via=via)
    return _with_ids(journeys)


class _EfaPoint:
    """An EFA origin, destination or via: a stored id, or a name and place."""

    def __init__(self, point_id: Optional[str], name: str, place: str) -> None:
        self.id = point_id or ""
        self.name = name or ""
        self.place = place or ""

    def params(self, usage: str) -> str:
        if self.id:
            return f"&type_{usage}={_efa_id_type(self.id)}&name_{usage}={quote(self.id, safe='')}"
        return (
            f"&type_{usage}=any&name_{usage}={quote(self.name, safe='')}" f"&place_{usage}={quote(self.place, safe='')}"
        )


class _EfaTripRequest:
    """One EFA XML_TRIP_REQUEST2 endpoint, with what parsing its answer needs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        provider: str,
        base_url: str,
        type_mapping: Dict[Any, str],
        timezone_name: Optional[str],
    ) -> None:
        self.session = session
        self.provider = provider
        self.base_url = base_url
        self.type_mapping = type_mapping
        self.timezone_name = timezone_name

    async def plan(
        self,
        origin: _EfaPoint,
        destination: _EfaPoint,
        departure_time: Optional[datetime],
        arrival_time: Optional[datetime],
        via: Optional[_EfaPoint] = None,
    ) -> List[Dict[str, Any]]:
        """Plan one EFA trip request and return the parsed journeys."""
        # EFA reads itdDate/itdTime as the network's local time, not Home Assistant's.
        dep_arr_flag = "arr" if arrival_time is not None else "dep"
        target = arrival_time or departure_time or dt_util.now()
        if self.timezone_name:
            target = target.astimezone(dt_util.get_time_zone(self.timezone_name) or target.tzinfo)
        date_str = target.strftime("%Y%m%d")
        time_str = target.strftime("%H%M")

        params = (
            "outputFormat=rapidJSON"
            + origin.params("origin")
            + destination.params("destination")
            + (via.params("via") if via is not None else "")
            + f"&itdDate={date_str}&itdTime={time_str}"
            + f"&itdTripDateTimeDepArr={dep_arr_flag}"
            + "&useRealtime=1"
        )
        url = f"{self.base_url}?{params}"
        provider = self.provider

        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status in (401, 403):
                    raise AuthenticationError(provider, response.status)
                if response.status != 200:
                    raise ApiError(provider, response.status)

                # content_type=None: VGN sends RapidJSON with a text/xml header (issue #79).
                data = await response.json(content_type=None)
        except asyncio.TimeoutError as e:
            raise ApiTimeoutError(f"{provider}: trip planning timed out after 15s") from e
        except aiohttp.ClientError as e:
            raise ApiConnectionError(f"{provider}: trip planning connection failed ({e})") from e

        if not isinstance(data, dict):
            raise ApiResponseError(f"{provider}: trip API returned {type(data).__name__} instead of an object")

        return _parse_journeys(data.get("journeys", []), self.type_mapping)


def _ts(journey: Dict[str, Any], key: str) -> Optional[datetime]:
    value = journey.get(key)
    return dt_util.parse_datetime(value) if isinstance(value, str) and value else None


async def _async_plan_trip_efa_with_dwell(
    efa: _EfaTripRequest,
    origin: _EfaPoint,
    via: _EfaPoint,
    destination: _EfaPoint,
    dwell: int,
    departure_time: Optional[datetime],
    arrival_time: Optional[datetime],
) -> List[Dict[str, Any]]:
    """Plan origin → via → destination with at least ``dwell`` minutes at the via.

    EFA documents ``dwellTime_via`` but none of the servers tried honours it
    (issue #110), so the stay is built from two requests: the first half, then
    the second half from the via, timed by the first. Arriving by a set time
    runs the other way round: the second half is planned against the arrival,
    the first half against the second's departure.
    """
    stay = timedelta(minutes=dwell)
    if arrival_time is None:
        first = await efa.plan(origin, via, departure_time, None)
        arrivals = [t for t in (_ts(j, "arrival_timestamp") for j in first) if t]
        if not arrivals:
            return []
        second = await efa.plan(via, destination, min(arrivals) + stay, None)
        pairs = _pair_halves(first, second, stay, forward=True)
    else:
        second = await efa.plan(via, destination, None, arrival_time)
        departures = [t for t in (_ts(j, "departure_timestamp") for j in second) if t]
        if not departures:
            return []
        first = await efa.plan(origin, via, None, max(departures) - stay)
        pairs = _pair_halves(first, second, stay, forward=False)
    return [_join_halves(a, b, via.name or (a.get("legs") or [{}])[-1].get("destination", "")) for a, b in pairs]


def _pair_halves(
    first: List[Dict[str, Any]], second: List[Dict[str, Any]], stay: timedelta, forward: bool
) -> List[tuple[Dict[str, Any], Dict[str, Any]]]:
    """Match each first half with a second half that leaves at least ``stay`` later.

    Going forward, every first half takes the earliest second half it can make,
    and when several first halves land on the same one only the latest of them
    is kept — the others would just wait longer for the same train. Arriving by
    a time, every second half takes the latest first half that reaches it.
    """
    pairs: Dict[int, tuple[Dict[str, Any], Dict[str, Any]]] = {}
    if forward:
        seconds = sorted(
            (j for j in second if _ts(j, "departure_timestamp")), key=lambda j: _ts(j, "departure_timestamp")
        )
        for a in first:
            arrive = _ts(a, "arrival_timestamp")
            if not arrive:
                continue
            match = next((b for b in seconds if _ts(b, "departure_timestamp") >= arrive + stay), None)
            if match is None:
                continue
            key = id(match)
            if key not in pairs or _ts(pairs[key][0], "departure_timestamp") < _ts(a, "departure_timestamp"):
                pairs[key] = (a, match)
    else:
        firsts = sorted((j for j in first if _ts(j, "arrival_timestamp")), key=lambda j: _ts(j, "arrival_timestamp"))
        for b in second:
            leave = _ts(b, "departure_timestamp")
            if not leave:
                continue
            match = next((a for a in reversed(firsts) if _ts(a, "arrival_timestamp") + stay <= leave), None)
            if match is None:
                continue
            key = id(match)
            if key not in pairs or _ts(pairs[key][1], "arrival_timestamp") > _ts(b, "arrival_timestamp"):
                pairs[key] = (match, b)
    return sorted(pairs.values(), key=lambda p: _ts(p[0], "departure_timestamp"))


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "missed": 3}


def _join_halves(first: Dict[str, Any], second: Dict[str, Any], via_name: str) -> Dict[str, Any]:
    """One journey out of the two halves of a trip with a stay at the via."""
    start = _ts(first, "departure_timestamp")
    end = _ts(second, "arrival_timestamp")
    stay_s = (_ts(second, "departure_timestamp") - _ts(first, "arrival_timestamp")).total_seconds()
    legs = [dict(leg) for leg in first.get("legs", [])] + [dict(leg) for leg in second.get("legs", [])]
    split = len(first.get("legs", []))
    if split:
        # The stay is planned, not a change to hurry for: mark it as such and
        # keep it out of the transfer risk.
        legs[split - 1]["transfer"] = legs[split - 1].get("transfer") or "via"
        legs[split - 1]["transfer_minutes"] = int(stay_s // 60)
        legs[split - 1]["via_stay"] = True
    mins = [m for m in (first.get("min_transfer_time"), second.get("min_transfer_time")) if m is not None]
    risk = max(
        first.get("transfer_risk", "low"), second.get("transfer_risk", "low"), key=lambda r: _RISK_ORDER.get(r, 0)
    )
    return {
        "departure": first.get("departure"),
        "arrival": second.get("arrival"),
        "departure_timestamp": first.get("departure_timestamp"),
        "arrival_timestamp": second.get("arrival_timestamp"),
        "duration_minutes": round((end - start).total_seconds() / 60) if start and end else 0,
        # Changing at the via is a change of vehicle too.
        "transfers": (first.get("transfers") or 0) + (second.get("transfers") or 0) + 1,
        "connection_feasible": bool(first.get("connection_feasible", True) and second.get("connection_feasible", True)),
        "transfer_risk": risk,
        "min_transfer_time": min(mins) if mins else None,
        "via": via_name,
        "via_dwell_minutes": int(stay_s // 60),
        "legs": legs,
    }


_GRAPHQL_PARENT = '{ stop(id: "%s") { parentStation { gtfsId } } }'


async def _resolve_station_id(provider_instance, stop_id: str) -> str:
    """Return a stop's parent-station id, or the stop id itself if it has none.

    A multi-platform station (e.g. a Hauptbahnhof) has one stop id per platform.
    Routing from the parent station lets OTP consider every platform; pinning an
    arbitrary single platform can yield a slower or wrong-direction journey.
    """
    body = await provider_instance._graphql(_GRAPHQL_PARENT % stop_id.replace('"', '\\"'))
    parent = (((body or {}).get("data") or {}).get("stop") or {}).get("parentStation") or {}
    return parent.get("gtfsId") or stop_id


async def _async_plan_trip_otp2_graphql(
    origin_id: str,
    dest_id: str,
    departure_time: Optional[datetime],
    provider_instance,
    arrival_time: Optional[datetime] = None,
    via_id: Optional[str] = None,
    via_dwell_minutes: int = 0,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip via the OTP2 planConnection query (self-hosted instances).

    Routes stop-to-stop using `stopLocationId`, so OTP takes the transit stops
    directly as origin/destination — no coordinates, no street-network
    access/egress. This is what lets the OTP graph be built transit-only (no
    OSM). Requires an OTP 2.x server exposing the planConnection API.

    ``arrival_time`` switches the query to "arrive by" mode and wins over
    ``departure_time`` when both are given.

    ``via_id`` adds a visit via-location, ``via_dwell_minutes`` its
    ``minimumWaitTime`` (issue #110). Via locations need a recent OTP 2.x; an
    older server answers with a schema error, which is raised as
    :class:`TripOptionNotSupportedError` rather than logged and lost.
    """
    # Compound stop IDs are pipe-separated — use the first platform ID
    from_id = origin_id.split("|")[0]
    to_id = dest_id.split("|")[0]

    # Route from the parent station rather than a single platform, so OTP
    # considers every platform of a multi-platform station.
    from_id, to_id = await asyncio.gather(
        _resolve_station_id(provider_instance, from_id),
        _resolve_station_id(provider_instance, to_id),
    )

    # Only pin a time when the caller asked for one; otherwise let OTP default
    # to "now" (a live server tracks the clock better than we do).
    dt_clause = ""
    if arrival_time is not None:
        dt_clause = 'dateTime: { latestArrival: "%s" }' % arrival_time.isoformat()
    elif departure_time is not None:
        dt_clause = 'dateTime: { earliestDeparture: "%s" }' % departure_time.isoformat()

    via_clause = ""
    if via_id:
        via_stop = await _resolve_station_id(provider_instance, via_id.split("|")[0])
        wait = f', minimumWaitTime: "PT{int(via_dwell_minutes)}M"' if via_dwell_minutes else ""
        via_clause = 'via: [{ visit: { stopLocationIds: ["%s"]%s } }]' % (via_stop.replace('"', '\\"'), wait)

    query = _GRAPHQL_PLAN_CONNECTION % (
        from_id.replace('"', '\\"'),
        to_id.replace('"', '\\"'),
        dt_clause,
        via_clause,
    )
    body = await provider_instance._graphql(query)
    if body is None:
        return None

    if body.get("errors"):
        _LOGGER.warning("OTP2 planConnection GraphQL errors: %s", body["errors"])
        if via_clause and not ((body.get("data") or {}).get("planConnection")):
            raise TripOptionNotSupportedError(
                "otp_custom", "dwell" if via_dwell_minutes else "via", "this OTP server rejects via locations"
            )

    edges = (((body.get("data") or {}).get("planConnection") or {}).get("edges")) or []
    if not edges:
        _LOGGER.warning("OTP2 planConnection: no itineraries for %s → %s", from_id, to_id)
        return None

    return _parse_otp_plan_connection([e["node"] for e in edges if e.get("node")])


async def _async_plan_trip_otp(
    origin_id: str,
    dest_id: str,
    departure_time: Optional[datetime],
    provider_instance,
    arrival_time: Optional[datetime] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Plan a trip using the OTP 2.x REST /plan endpoint.

    ``arrival_time`` switches the query to "arrive by" mode (OTP's
    ``arriveBy=true``) and wins over ``departure_time`` when both are given.
    """
    target = arrival_time or departure_time or dt_util.now()
    base_url = provider_instance.otp_base_url

    # Resolve stop coordinates concurrently — OTP /plan needs lat,lon not stop IDs
    origin_stop, dest_stop = await asyncio.gather(
        provider_instance._get(f"{base_url}/index/stops/{quote(origin_id, safe='')}"),
        provider_instance._get(f"{base_url}/index/stops/{quote(dest_id, safe='')}"),
    )
    if not origin_stop or not dest_stop:
        _LOGGER.warning("VBN OTP trip: could not resolve stop coordinates for %s / %s", origin_id, dest_id)
        return None

    from_place = f"{origin_stop['lat']},{origin_stop['lon']}"
    to_place = f"{dest_stop['lat']},{dest_stop['lon']}"

    params = {
        "fromPlace": from_place,
        "toPlace": to_place,
        "date": target.strftime("%Y-%m-%d"),
        "time": target.strftime("%H:%M:%S"),
        "numItineraries": "5",
        "mode": "TRANSIT,WALK",
        # Without a window OTP only looks a short time ahead, so a line that
        # runs once an hour yielded a single connection (issue #92).
        "searchWindow": str(4 * 3600),
    }
    if arrival_time is not None:
        params["arriveBy"] = "true"

    data = await provider_instance._get(f"{base_url}/plan", params)
    if not data:
        return None

    itineraries = data.get("plan", {}).get("itineraries", [])
    if not itineraries:
        _LOGGER.debug("VBN OTP trip: no itineraries returned")
        return None

    return _parse_otp_itineraries(itineraries)


def _parse_otp_itineraries(itineraries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse OTP 2.x plan itineraries into the unified journey dict format."""
    results = []

    for itin in itineraries:
        transit_legs: List[Dict[str, Any]] = []

        for leg in itin.get("legs", []):
            if not leg.get("transitLeg", False):
                continue

            start_ms: int = leg.get("startTime", 0)
            end_ms: int = leg.get("endTime", 0)
            dep_delay_s: int = leg.get("departureDelay", 0)
            arr_delay_s: int = leg.get("arrivalDelay", 0)

            # planned = actual minus delay
            planned_start_ms = start_ms - dep_delay_s * 1000
            planned_end_ms = end_ms - arr_delay_s * 1000

            dep_estimated = _ms_to_hhmm(start_ms)
            dep_planned = _ms_to_hhmm(planned_start_ms)
            arr_estimated = _ms_to_hhmm(end_ms)
            arr_planned = _ms_to_hhmm(planned_end_ms)

            delay_min = dep_delay_s // 60
            product = _OTP_MODE_TO_PRODUCT.get(leg.get("mode", ""), leg.get("mode", "").lower())

            transit_legs.append(
                {
                    "origin": leg.get("from", {}).get("name", ""),
                    "destination": leg.get("to", {}).get("name", ""),
                    "line": (leg.get("trip") or {}).get("route", {}).get("shortName") or leg.get("route", ""),
                    "product": product,
                    # OTP modes already are the unified types, so the leg needs no
                    # mapping to be matched against the entry's transport types.
                    "transport_type": product,
                    "departure_planned": dep_planned,
                    "departure_estimated": dep_estimated,
                    "arrival_planned": arr_planned,
                    "arrival_estimated": arr_estimated,
                    "delay": delay_min,
                    "duration_minutes": round(leg.get("duration", 0) / 60),
                    "platform": "",
                    # Internal epoch seconds for transfer-gap calculation
                    "_arrival_s": end_ms / 1000,
                    "_departure_s": start_ms / 1000,
                }
            )

        if not transit_legs:
            continue

        connection_feasible, transfer_risk, min_transfer_time = _rate_transfers(transit_legs)
        departure_ts, arrival_ts = _journey_bounds(transit_legs)

        # Strip internal keys before returning
        for leg in transit_legs:
            leg.pop("_arrival_s", None)
            leg.pop("_departure_s", None)

        first_dep = transit_legs[0].get("departure_estimated") or transit_legs[0].get("departure_planned", "")
        last_arr = transit_legs[-1].get("arrival_estimated") or transit_legs[-1].get("arrival_planned", "")

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "departure_timestamp": departure_ts,
                "arrival_timestamp": arrival_ts,
                "duration_minutes": round(itin.get("duration", 0) / 60),
                "transfers": itin.get("numberOfTransfers", itin.get("transfers", len(transit_legs) - 1)),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": transit_legs,
            }
        )

    return results


def _ms_to_hhmm(ms: int) -> str:
    """Convert OTP millisecond Unix timestamp to HH:MM in local time."""
    if not ms:
        return ""
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt_util.as_local(dt).strftime("%H:%M")
    except (ValueError, OSError):
        return ""


def _iso_to_hhmm(iso: Optional[str]) -> str:
    """Convert an ISO-8601 datetime string to HH:MM in local time."""
    if not iso:
        return ""
    dt = dt_util.parse_datetime(iso)
    return dt_util.as_local(dt).strftime("%H:%M") if dt else ""


def _iso_to_epoch(iso: Optional[str]) -> float:
    """Convert an ISO-8601 datetime string to a Unix timestamp (seconds)."""
    if not iso:
        return 0.0
    dt = dt_util.parse_datetime(iso)
    return dt.timestamp() if dt else 0.0


_ISO_DURATION_RE = re.compile(
    r"^(?P<sign>-)?P(?:(?P<days>\d+)D)?T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?$",
    re.IGNORECASE,
)


def _duration_to_seconds(value: Any) -> int:
    """Coerce an OTP2 ``Duration`` value to whole seconds.

    OTP2's ``planConnection`` returns durations (leg/itinerary ``duration`` and
    realtime ``delay``) as the ``Duration`` scalar, serialised as an ISO-8601
    string like ``"PT3M"`` / ``"-PT90S"``. Older/other schemas return a plain
    number of seconds. Handle both (and ``None``) so a real-time delay no longer
    crashes the trip planner.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))  # plain numeric string (seconds)
    except ValueError:
        pass
    match = _ISO_DURATION_RE.match(text)
    if not match:
        return 0
    parts = match.groupdict()
    total = (
        int(parts["days"] or 0) * 86400
        + int(parts["h"] or 0) * 3600
        + int(parts["m"] or 0) * 60
        + int(float(parts["s"] or 0))
    )
    return -total if parts["sign"] else total


def _parse_otp_plan_connection(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse OTP2 planConnection nodes into the unified journey dict format."""
    results = []

    for node in nodes:
        transit_legs = []
        for leg in node.get("legs", []):
            if not leg.get("transitLeg", False):
                continue

            start = leg.get("start") or {}
            end = leg.get("end") or {}
            dep_planned = start.get("scheduledTime")
            dep_estimated = ((start.get("estimated") or {}).get("time")) or dep_planned
            arr_planned = end.get("scheduledTime")
            arr_estimated = ((end.get("estimated") or {}).get("time")) or arr_planned
            delay_s = (start.get("estimated") or {}).get("delay")
            route = (leg.get("trip") or {}).get("route") or leg.get("route") or {}
            product = _OTP_MODE_TO_PRODUCT.get(leg.get("mode", ""), (leg.get("mode") or "").lower())

            transit_legs.append(
                {
                    "origin": (leg.get("from") or {}).get("name", ""),
                    "destination": (leg.get("to") or {}).get("name", ""),
                    "line": route.get("shortName") or "",
                    "product": product,
                    "transport_type": product,
                    "departure_planned": _iso_to_hhmm(dep_planned),
                    "departure_estimated": _iso_to_hhmm(dep_estimated),
                    "arrival_planned": _iso_to_hhmm(arr_planned),
                    "arrival_estimated": _iso_to_hhmm(arr_estimated),
                    "delay": _duration_to_seconds(delay_s) // 60,
                    "duration_minutes": round(_duration_to_seconds(leg.get("duration")) / 60),
                    "platform": "",
                    # Internal epoch seconds for transfer-gap calculation
                    "_arrival_s": _iso_to_epoch(arr_estimated),
                    "_departure_s": _iso_to_epoch(dep_estimated),
                }
            )

        if not transit_legs:
            continue

        connection_feasible, transfer_risk, min_transfer_time = _rate_transfers(transit_legs)
        departure_ts, arrival_ts = _journey_bounds(transit_legs)

        for leg in transit_legs:
            leg.pop("_arrival_s", None)
            leg.pop("_departure_s", None)

        first_dep = transit_legs[0].get("departure_estimated") or transit_legs[0].get("departure_planned", "")
        last_arr = transit_legs[-1].get("arrival_estimated") or transit_legs[-1].get("arrival_planned", "")

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "departure_timestamp": departure_ts,
                "arrival_timestamp": arrival_ts,
                "duration_minutes": round(_duration_to_seconds(node.get("duration")) / 60),
                "transfers": node.get("numberOfTransfers", len(transit_legs) - 1),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": transit_legs,
            }
        )

    return results


def _parse_hafas_trips(trips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert HAFAS mgate trips from the library into the unified journey format.

    Like the OTP2 path, only vehicle legs are kept — walks are not transfers.
    A connection with a cancelled leg cannot be travelled and is dropped.
    """
    results = []

    for trip in trips:
        transit = [leg for leg in trip.get("legs", []) if leg.get("mode") == "transit"]
        if not transit or any(leg.get("cancelled") for leg in transit):
            continue

        transit_legs = []
        for leg in transit:
            dep_planned, dep = leg["departure_planned"], leg["departure"]
            arr_planned, arr = leg["arrival_planned"], leg["arrival"]
            transit_legs.append(
                {
                    "origin": leg.get("origin", ""),
                    "destination": leg.get("destination", ""),
                    "line": leg.get("line", ""),
                    "product": leg.get("product", ""),
                    "transport_type": leg.get("transport_type", "unknown"),
                    # The vehicle's headsign, same as the EFA legs (#95)
                    "direction": leg.get("direction", ""),
                    "departure_planned": dt_util.as_local(dep_planned).strftime("%H:%M"),
                    "departure_estimated": dt_util.as_local(dep).strftime("%H:%M"),
                    "arrival_planned": dt_util.as_local(arr_planned).strftime("%H:%M"),
                    "arrival_estimated": dt_util.as_local(arr).strftime("%H:%M"),
                    "delay": int((dep - dep_planned).total_seconds() // 60),
                    "duration_minutes": int((arr - dep).total_seconds() // 60),
                    "platform": leg.get("platform", ""),
                    # Internal epoch seconds for transfer-gap calculation
                    "_departure_s": dep.timestamp(),
                    "_arrival_s": arr.timestamp(),
                }
            )

        connection_feasible, transfer_risk, min_transfer_time = _rate_transfers(transit_legs)
        departure_ts, arrival_ts = _journey_bounds(transit_legs)
        for leg in transit_legs:
            leg.pop("_departure_s", None)
            leg.pop("_arrival_s", None)

        results.append(
            {
                "departure": transit_legs[0]["departure_estimated"],
                "arrival": transit_legs[-1]["arrival_estimated"],
                "departure_timestamp": departure_ts,
                "arrival_timestamp": arrival_ts,
                "duration_minutes": trip.get("duration_minutes") or 0,
                "transfers": trip.get("transfers", len(transit_legs) - 1),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": transit_legs,
            }
        )

    return results


def _parse_journeys(
    journeys: List[Dict[str, Any]],
    type_mapping: Optional[Dict[Any, str]] = None,
) -> List[Dict[str, Any]]:
    """Parse EFA journey data into a clean format.

    ``type_mapping`` is the provider's product-class mapping; without it every
    leg's transport type is derived from the product name alone.
    """
    results = []

    for journey in journeys:
        legs = []
        # Vehicle legs only — walking legs are not transfers (see _rate_transfers)
        transit_legs: List[Dict[str, Any]] = []
        total_duration = 0

        for leg in journey.get("legs", []):
            origin = leg.get("origin") or {}
            destination = leg.get("destination") or {}
            transport = leg.get("transportation") or {}
            product = transport.get("product") or {}
            interchange = leg.get("interchange") or {}

            dep_planned = origin.get("departureTimePlanned", "")
            dep_estimated = origin.get("departureTimeEstimated", "")
            arr_planned = destination.get("arrivalTimePlanned", "")
            arr_estimated = destination.get("arrivalTimeEstimated", "")

            # Calculate delay
            dep_delay = 0
            if dep_planned and dep_estimated:
                try:
                    p = dt_util.parse_datetime(dep_planned)
                    e = dt_util.parse_datetime(dep_estimated)
                    if p and e:
                        dep_delay = int((e - p).total_seconds() / 60)
                except (ValueError, TypeError):
                    pass

            duration = leg.get("duration", 0)
            total_duration += duration

            leg_data = {
                "origin": origin.get("name", ""),
                "destination": destination.get("name", ""),
                "line": transport.get("number", ""),
                # Where the vehicle itself is headed. EFA carries the headsign
                # as the transportation's own destination, which is not the leg's
                # destination: an S1 to Herrenberg is boarded for two stops as
                # readily as for twenty, and the headsign is what is written on
                # the front of the train and on the platform display.
                "direction": (transport.get("destination") or {}).get("name", ""),
                "product": product.get("name", ""),
                "transport_type": _leg_transport_type(product, type_mapping),
                "departure_planned": _format_time(dep_planned),
                "departure_estimated": _format_time(dep_estimated),
                "arrival_planned": _format_time(arr_planned),
                "arrival_estimated": _format_time(arr_estimated),
                "delay": dep_delay,
                "duration_minutes": round(duration / 60) if duration else 0,
                "platform": (origin.get("platform") or {}).get("name", ""),
                # Internal epoch seconds for transfer-gap calculation. Derived
                # from the full timestamps rather than the HH:MM strings, so a
                # transfer across midnight is no longer a negative gap.
                "_departure_s": _iso_to_epoch(dep_estimated or dep_planned),
                "_arrival_s": _iso_to_epoch(arr_estimated or arr_planned),
            }

            # Add transfer info if present
            if interchange and interchange.get("desc"):
                leg_data["transfer"] = interchange.get("desc", "")

            legs.append(leg_data)
            if _is_transit_product(product):
                transit_legs.append(leg_data)

        if not legs:
            continue

        # Journey summary
        first_dep = legs[0].get("departure_estimated") or legs[0].get("departure_planned", "")
        last_arr = legs[-1].get("arrival_estimated") or legs[-1].get("arrival_planned", "")

        connection_feasible, transfer_risk, min_transfer_time = _rate_transfers(transit_legs)
        departure_ts, arrival_ts = _journey_bounds(legs)

        # The journey lasts from the first departure to the last arrival. Leg
        # durations only cover time on board (and walking), so their sum leaves
        # out the wait at every change (#105). Fall back to that sum only when
        # the timestamps are missing.
        start_s = legs[0].get("_departure_s") or 0
        end_s = legs[-1].get("_arrival_s") or 0
        if start_s and end_s and end_s >= start_s:
            total_duration = end_s - start_s

        for leg_data in legs:
            leg_data.pop("_departure_s", None)
            leg_data.pop("_arrival_s", None)

        results.append(
            {
                "departure": first_dep,
                "arrival": last_arr,
                "departure_timestamp": departure_ts,
                "arrival_timestamp": arrival_ts,
                "duration_minutes": round(total_duration / 60) if total_duration else 0,
                "transfers": journey.get("interchanges", 0),
                "connection_feasible": connection_feasible,
                "transfer_risk": transfer_risk,
                "min_transfer_time": min_transfer_time,
                "legs": legs,
            }
        )

    return results


def _format_time(iso_str: str) -> str:
    """Format ISO datetime string to HH:MM in local time."""
    if not iso_str:
        return ""
    try:
        dt = dt_util.parse_datetime(iso_str)
        if dt:
            local_dt = dt_util.as_local(dt)
            return local_dt.strftime("%H:%M")
    except (ValueError, TypeError):
        pass
    return ""
