"""Departure filters that distinguish one entry for a station from another.

Shared by the config flow (which freezes a discriminator into the entry at
creation time, issue #55) and the sensor platform (which renders the current
filters into the device name).
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, List, Mapping, Set, Tuple

from .const import (
    CONF_ARRIVAL_OFFSET,
    CONF_ARRIVAL_TIME,
    CONF_ARRIVAL_TIME_ENTITY,
    CONF_DESTINATION_FILTER,
    CONF_LINE_FILTER,
    CONF_PLATFORM_FILTER,
)

# The filters that make two entries for one station genuinely different,
# paired with how each reads in the entry title and device name.
#
# Deliberately excludes favourite lines and walking time: those change how
# departures are presented, not which departures the entry is about, so two
# entries differing only there are still duplicates.
DISCRIMINATING_FILTERS = (
    (CONF_LINE_FILTER, "{}"),
    (CONF_DESTINATION_FILTER, "→ {}"),
    (CONF_PLATFORM_FILTER, "Pl. {}"),
)


def filter_values(source: Mapping[str, Any], key: str) -> List[str]:
    """Split one comma-separated filter field into its trimmed values."""
    return [value.strip() for value in str(source.get(key) or "").split(",") if value.strip()]


def filter_discriminator(source: Mapping[str, Any]) -> str:
    """Return a stable short id for this filter set, "" when unfiltered.

    Order- and case-insensitive, so "S1, S2" and "s2,s1" are recognised as the
    same configuration and the second one is rejected as already_configured.

    Frozen into ``entry.data`` at creation: entity unique IDs are built on it,
    so it must not move when the filters are later edited under Options.
    """
    canonical = {
        key: sorted({value.casefold() for value in filter_values(source, key)}) for key, _ in DISCRIMINATING_FILTERS
    }
    if not any(canonical.values()):
        return ""

    fingerprint = "|".join(f"{key}={','.join(values)}" for key, values in sorted(canonical.items()))
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8]


def filter_label(source: Mapping[str, Any]) -> str:
    """Return a short human-readable form of the filters, "" when unfiltered."""
    bits = []
    for key, template in DISCRIMINATING_FILTERS:
        values = filter_values(source, key)
        if values:
            bits.append(template.format(", ".join(values)))
    return " ".join(bits)


def current_filters(entry: Any) -> dict:
    """Return an entry's filters as they are configured *right now*.

    Options win over data, matching how every consumer reads them.
    """
    return {key: entry.options.get(key, entry.data.get(key, "")) for key, _ in DISCRIMINATING_FILTERS}


def split_filter(raw: str, normalize: Callable[[str], str]) -> Tuple[List[str], List[str]]:
    """Split a comma-separated filter into (include, exclude) values.

    A value starting with "!" excludes instead of includes (issue #93), so
    "!Hauptbahnhof" hides every departure towards Hauptbahnhof and "U43, !U47"
    shows U43 only. Values are passed through ``normalize``; empty ones drop out.
    """
    include: List[str] = []
    exclude: List[str] = []
    for value in str(raw or "").split(","):
        value = value.strip()
        target = exclude if value.startswith("!") else include
        normalized = normalize(value.lstrip("!").strip())
        if normalized:
            target.append(normalized)
    return include, exclude


def matches_filter(
    value: str, include: Set[str] | List[str], exclude: Set[str] | List[str], *, substring: bool
) -> bool:
    """True when ``value`` passes an include/exclude filter.

    With ``substring`` a filter value matches anywhere in ``value`` (destinations),
    otherwise it must match exactly (lines, platforms). An empty include list
    lets everything through that is not excluded.
    """

    def hit(term: str) -> bool:
        return term in value if substring else term == value

    if any(hit(term) for term in exclude):
        return False
    return not include or any(hit(term) for term in include)


# Trip arrival configuration that distinguishes one trip entry for a route
# from another. Two trip entries for the same origin/destination are
# otherwise indistinguishable, which blocked configuring e.g. one entry per
# child, each arriving by a different first-lesson time ("already
# configured"). Deliberately excludes nothing here — unlike departure
# filters, every arrival field changes *which* connection is being asked
# for, not just how it's presented.
_TRIP_ARRIVAL_KEYS = (CONF_ARRIVAL_TIME, CONF_ARRIVAL_TIME_ENTITY, CONF_ARRIVAL_OFFSET)


def trip_arrival_discriminator(source: Mapping[str, Any]) -> str:
    """Return a stable short id for a trip's arrival config, "" when unset.

    Frozen into ``entry.data`` at creation, same as ``filter_discriminator``:
    entity unique IDs are built on it, so it must not move when the arrival
    settings are later edited under Options.
    """
    arrival_time = str(source.get(CONF_ARRIVAL_TIME) or "").strip().casefold()
    arrival_time_entity = str(source.get(CONF_ARRIVAL_TIME_ENTITY) or "").strip().casefold()
    if not arrival_time and not arrival_time_entity:
        return ""

    offset = source.get(CONF_ARRIVAL_OFFSET, "")
    fingerprint = f"time={arrival_time}|entity={arrival_time_entity}|offset={offset}"
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8]


def trip_arrival_label(source: Mapping[str, Any]) -> str:
    """Return a short human-readable form of the arrival config, "" when unset."""
    arrival_time_entity = str(source.get(CONF_ARRIVAL_TIME_ENTITY) or "").strip()
    if arrival_time_entity:
        return f"→ {arrival_time_entity}"
    arrival_time = str(source.get(CONF_ARRIVAL_TIME) or "").strip()
    if arrival_time:
        return f"arrive {arrival_time}"
    return ""


def current_trip_arrival(entry: Any) -> dict:
    """Return a trip entry's arrival config as it is set *right now*.

    Options win over data, matching how the coordinator reads them.
    """
    return {key: entry.options.get(key, entry.data.get(key, "")) for key in _TRIP_ARRIVAL_KEYS}
