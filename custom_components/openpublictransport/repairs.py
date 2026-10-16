"""Repairs for Open Public Transport."""

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a flow to fix a fixable issue."""
    # The only fixable issue is the community-server removal notice — confirming dismisses it.
    return ConfirmRepairFlow()
