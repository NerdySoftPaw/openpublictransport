"""Departure filters that distinguish one entry for a station from another.

Shared by the config flow (which freezes a discriminator into the entry at
creation time, issue #55) and the sensor platform (which renders the current
filters into the device name).
"""

from __future__ import annotations

import hashlib
from typing import Any, List, Mapping

from .const import CONF_DESTINATION_FILTER, CONF_LINE_FILTER, CONF_PLATFORM_FILTER

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
