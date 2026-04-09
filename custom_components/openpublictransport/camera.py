"""Camera platform for Open Public Transport integration.

Renders a departure board image (like a real station display) that
updates with each coordinator refresh. Yellow on black, classic look.
"""

import io
import logging
from datetime import datetime

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from PIL import Image, ImageDraw, ImageFont

from .const import CONF_TRANSPORTATION_TYPES, DOMAIN, TRANSPORTATION_TYPES
from .sensor import PublicTransportDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Board styling
BG_COLOR = (0, 0, 0)
HEADER_COLOR = (255, 200, 0)
TEXT_COLOR = (255, 200, 0)
DELAY_COLOR = (255, 80, 80)
ON_TIME_COLOR = (80, 255, 80)
LINE_COLOR = (60, 60, 60)
BOARD_WIDTH = 800
ROW_HEIGHT = 36
HEADER_HEIGHT = 50
PADDING = 16
MAX_ROWS = 10


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font with Unicode support (for umlauts etc.), falling back gracefully."""
    font_paths = [
        # Linux (HAOS, Docker)
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        # macOS
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Font names (PIL searches system paths)
        "DejaVuSansMono.ttf",
        "DejaVuSans.ttf",
        "LiberationMono-Regular.ttf",
        "FreeMono.ttf",
    ]
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default(size=size)


def render_departure_board(
    station_name: str,
    departures: list[dict],
    now: datetime,
) -> bytes:
    """Render a departure board image as PNG bytes."""
    num_rows = min(len(departures), MAX_ROWS)
    board_height = HEADER_HEIGHT + (num_rows * ROW_HEIGHT) + PADDING * 2

    if num_rows == 0:
        board_height = HEADER_HEIGHT + ROW_HEIGHT + PADDING * 2

    img = Image.new("RGB", (BOARD_WIDTH, board_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_header = _get_font(22)
    font_row = _get_font(18)
    font_small = _get_font(14)

    # Header bar
    draw.rectangle([(0, 0), (BOARD_WIDTH, HEADER_HEIGHT)], fill=(20, 20, 20))
    draw.text((PADDING, 12), station_name, fill=HEADER_COLOR, font=font_header)
    time_str = now.strftime("%H:%M")
    time_bbox = draw.textbbox((0, 0), time_str, font=font_header)
    time_width = time_bbox[2] - time_bbox[0]
    draw.text((BOARD_WIDTH - PADDING - time_width, 12), time_str, fill=HEADER_COLOR, font=font_header)

    if num_rows == 0:
        y = HEADER_HEIGHT + PADDING
        draw.text((PADDING, y + 8), "Keine Abfahrten / No departures", fill=LINE_COLOR, font=font_row)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # Column positions
    col_time = PADDING
    col_line = 90
    col_dest = 200
    col_platform = 620
    col_delay = 710

    # Column headers
    y = HEADER_HEIGHT + 4
    draw.text((col_time, y), "Zeit", fill=LINE_COLOR, font=font_small)
    draw.text((col_line, y), "Linie", fill=LINE_COLOR, font=font_small)
    draw.text((col_dest, y), "Ziel", fill=LINE_COLOR, font=font_small)
    draw.text((col_platform, y), "Gleis", fill=LINE_COLOR, font=font_small)
    draw.text((col_delay, y), "Delay", fill=LINE_COLOR, font=font_small)

    # Departure rows
    for i, dep in enumerate(departures[:MAX_ROWS]):
        y = HEADER_HEIGHT + 20 + (i * ROW_HEIGHT)

        # Separator line
        draw.line([(PADDING, y), (BOARD_WIDTH - PADDING, y)], fill=LINE_COLOR, width=1)

        row_y = y + 8

        # Time
        dep_time = dep.get("departure_time", "")
        draw.text((col_time, row_y), dep_time, fill=TEXT_COLOR, font=font_row)

        # Line number
        line = dep.get("line", "")
        draw.text((col_line, row_y), line[:12], fill=TEXT_COLOR, font=font_row)

        # Destination (truncate)
        dest = dep.get("destination", "")
        if len(dest) > 30:
            dest = dest[:28] + "…"
        draw.text((col_dest, row_y), dest, fill=TEXT_COLOR, font=font_row)

        # Platform
        platform = dep.get("platform", "")
        if platform:
            draw.text((col_platform, row_y), str(platform)[:6], fill=TEXT_COLOR, font=font_row)

        # Delay
        delay = dep.get("delay", 0)
        if delay > 0:
            delay_text = f"+{delay}"
            draw.text((col_delay, row_y), delay_text, fill=DELAY_COLOR, font=font_row)
        elif dep.get("is_realtime"):
            draw.text((col_delay, row_y), "✓", fill=ON_TIME_COLOR, font=font_row)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera from a config entry."""
    coordinator_key = f"{config_entry.entry_id}_coordinator"
    coordinator = hass.data[DOMAIN].get(coordinator_key)

    if not coordinator:
        return

    async_add_entities([DepartureBoardCamera(coordinator, config_entry)])


class DepartureBoardCamera(CoordinatorEntity, Camera):
    """Camera entity rendering a departure board image."""

    _attr_is_streaming = False

    def __init__(
        self,
        coordinator: PublicTransportDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ):
        """Initialize the camera."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._config_entry = config_entry
        self._image: bytes | None = None

        provider = coordinator.provider
        station_id = coordinator.station_id
        place_dm = coordinator.place_dm
        name_dm = coordinator.name_dm
        station_key = station_id or f"{place_dm}_{name_dm}".lower().replace(" ", "_")

        self._station_name = f"{place_dm} - {name_dm}" if place_dm else name_dm
        self._attr_unique_id = f"{provider}_{station_key}_board"
        self._attr_name = f"{provider.upper()} {place_dm} - {name_dm} Board"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{provider}_{station_key}")},
            suggested_area=place_dm,
        )

        self._transportation_types = set(
            config_entry.options.get(
                CONF_TRANSPORTATION_TYPES,
                config_entry.data.get(CONF_TRANSPORTATION_TYPES, list(TRANSPORTATION_TYPES.keys())),
            )
        )

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return the departure board image."""
        return self._image

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-render the board when data updates."""
        if not self.coordinator.data or not self.coordinator.provider_instance:
            self._image = render_departure_board(self._station_name, [], dt_util.now())
            self.async_write_ha_state()
            return

        provider_instance = self.coordinator.provider_instance
        stop_events = self.coordinator.data.get("stopEvents", [])
        tz = dt_util.get_time_zone(provider_instance.get_timezone())
        now = dt_util.now()

        departures = []
        for stop in stop_events:
            dep = provider_instance.parse_departure(stop, tz, now)
            if dep and dep.transportation_type in self._transportation_types:
                departures.append(dep.to_dict())

        departures.sort(key=lambda d: d.get("departure_time", ""))
        self._image = render_departure_board(self._station_name, departures, now)
        self.async_write_ha_state()
