DOMAIN = "openpublictransport"
DEFAULT_PLACE = "Düsseldorf"
DEFAULT_NAME = "Elbruchstrasse"
DEFAULT_DEPARTURES = 10
DEFAULT_SCAN_INTERVAL = 60

# When a line/destination/platform filter is active, fetch a larger raw board from the API
# so client-side filtering isn't starved before truncating to the display count (issue #43).
FILTERED_FETCH_LIMIT = 100

# Configuration keys
CONF_PROVIDER = "provider"  # NEU
CONF_STATION_ID = "station_id"
CONF_DEPARTURES = "departures"
CONF_TRANSPORTATION_TYPES = "transportation_types"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TRAFIKLAB_API_KEY = "trafiklab_api_key"  # For Trafiklab API
CONF_NTA_API_KEY = "nta_api_key"  # For NTA Ireland API (Primary Key)
CONF_NTA_API_KEY_SECONDARY = "nta_api_key_secondary"  # For NTA Ireland API (Secondary Key, optional)
CONF_USE_PROVIDER_LOGO = "use_provider_logo"  # Show provider logo instead of transport icon
CONF_DELAY_THRESHOLD = "delay_threshold"  # Minutes threshold for delay binary sensor
CONF_LINE_FILTER = "line_filter"  # Comma-separated line numbers to show
CONF_DESTINATION_FILTER = "destination_filter"  # Comma-separated destinations (substring match) to show
CONF_PLATFORM_FILTER = "platform_filter"  # Comma-separated platforms/tracks to show
# Discriminator that lets the same station be configured more than once with
# different filters (issue #55). Absent on entries created before that, which
# is what keeps their unique IDs byte-identical.
CONF_ENTRY_SUFFIX = "entry_suffix"
CONF_ENTRY_LABEL = "entry_label"  # Human-readable form of that discriminator, e.g. "S1 → Plochingen"
CONF_WALKING_TIME = "walking_time"  # Minutes to walk to the stop
CONF_FAVORITE_LINES = "favorite_lines"  # Comma-separated favorite lines (shown first)
DEFAULT_DELAY_THRESHOLD = 5
DEFAULT_WALKING_TIME = 0

# Provider
PROVIDER_VRR = "vrr"
PROVIDER_KVV = "kvv"
PROVIDER_HVV = "hvv"
PROVIDER_HVV_GTI = "hvv_gti"  # HVV via the official Geofox GTI API (credentials required)
CONF_HVV_GTI_USER = "hvv_gti_user"  # GTI application ID (geofox-auth-user)
CONF_HVV_GTI_PASSWORD = "hvv_gti_password"  # GTI password, used as the HMAC-SHA1 key
PROVIDER_BVG = "bvg"
PROVIDER_MVV = "mvv"
PROVIDER_VVS = "vvs"
PROVIDER_VGN = "vgn"
PROVIDER_VAGFR = "vagfr"
PROVIDER_RMV = "rmv"
CONF_RMV_API_KEY = "rmv_api_key"  # For RMV HAFAS API
PROVIDER_TRAFIKLAB_SE = "trafiklab_se"
PROVIDER_NTA_IE = "nta_ie"
PROVIDER_VRN = "vrn"
PROVIDER_VVO = "vvo"
PROVIDER_DING = "ding"
PROVIDER_AVV_AUGSBURG = "avv_augsburg"
PROVIDER_RVV = "rvv"
PROVIDER_BSVG = "bsvg"
PROVIDER_NWL = "nwl"
PROVIDER_NVBW = "nvbw"
PROVIDER_BEG = "beg"
PROVIDER_SBB = "sbb"
PROVIDER_OEBB = "oebb"
PROVIDER_TRANSITOUS = "transitous"
PROVIDER_DB = "db"
PROVIDER_VBN_OTP = "vbn_otp"
PROVIDER_VBN_TRIAS = "vbn_trias"
CONF_VBN_API_KEY = "vbn_api_key"
PROVIDER_OPT = "openpublictransport"  # community server at api.openpublictransport.net
PROVIDER_OTP_CUSTOM = "otp_custom"  # user-provided OTP2 instance
CONF_OTP_BASE_URL = "otp_base_url"  # custom URL for otp_custom provider
CONF_OPT_API_KEY = "opt_api_key"  # API key for community OTP server
CONF_OTP_CUSTOM_API_KEY = "otp_custom_api_key"  # API key for custom OTP instance
PROVIDER_NATIONAL_RAIL = "national_rail"  # National Rail (UK) via OpenLDBWS
CONF_NATIONAL_RAIL_API_KEY = "national_rail_api_key"
PROVIDER_REJSEPLANEN = "rejseplanen"  # Rejseplanen (Denmark) via HAFAS REST API
CONF_REJSEPLANEN_API_KEY = "rejseplanen_api_key"
PROVIDER_NS_NL = "ns_nl"  # NS (Netherlands) via HAFAS Scotty
PROVIDER_MOBILITEIT_LU = "mobiliteit_lu"  # mobilitéit.lu (Luxembourg) via HAFAS Scotty
PROVIDER_ENTUR_NO = "entur_no"  # Entur (Norway) via OTP transmodel GraphQL
PROVIDER_BART_US = "bart_us"  # BART (San Francisco) via HAFAS mgate
PROVIDER_DART_US = "dart_us"  # DART (Des Moines) via HAFAS mgate
PROVIDER_IRISHRAIL_IE = "irishrail_ie"  # Iarnród Éireann / Irish Rail via HAFAS mgate
PROVIDER_TPG_CH = "tpg_ch"  # TPG (Geneva) via HAFAS mgate
PROVIDERS = [
    PROVIDER_VRR,
    PROVIDER_KVV,
    PROVIDER_HVV,
    PROVIDER_HVV_GTI,
    PROVIDER_BVG,
    PROVIDER_MVV,
    PROVIDER_VVS,
    PROVIDER_VGN,
    PROVIDER_VAGFR,
    PROVIDER_RMV,
    PROVIDER_TRAFIKLAB_SE,
    PROVIDER_NTA_IE,
    PROVIDER_VRN,
    PROVIDER_VVO,
    PROVIDER_DING,
    PROVIDER_AVV_AUGSBURG,
    PROVIDER_RVV,
    PROVIDER_BSVG,
    PROVIDER_NWL,
    PROVIDER_NVBW,
    PROVIDER_BEG,
    PROVIDER_SBB,
    PROVIDER_OEBB,
    PROVIDER_TRANSITOUS,
    PROVIDER_DB,
    PROVIDER_VBN_OTP,
    PROVIDER_VBN_TRIAS,
    PROVIDER_OPT,
    PROVIDER_OTP_CUSTOM,
    PROVIDER_NATIONAL_RAIL,
    PROVIDER_REJSEPLANEN,
    PROVIDER_NS_NL,
    PROVIDER_MOBILITEIT_LU,
    PROVIDER_ENTUR_NO,
    PROVIDER_BART_US,
    PROVIDER_DART_US,
    PROVIDER_IRISHRAIL_IE,
    PROVIDER_TPG_CH,
]

# Transportation types mapping
TRANSPORTATION_TYPES = {"bus": "Bus", "tram": "Tram", "subway": "U-Bahn", "train": "S-Bahn/Train"}

# API Configuration
API_RATE_LIMIT_PER_MINUTE = 60
API_RATE_LIMIT_PER_HOUR = 1000
API_RATE_LIMIT_PER_DAY = 60000
API_BASE_URL_VRR = "https://openservice-test.vrr.de/static03/XML_DM_REQUEST"
API_BASE_URL_KVV = "https://projekte.kvv-efa.de/sl3-alone/XSLT_DM_REQUEST"
API_BASE_URL_HVV = "https://hvv.efa.de/efa/XML_DM_REQUEST"
API_BASE_URL_TRAFIKLAB = "https://realtime-api.trafiklab.se/v1"
API_BASE_URL_NTA_GTFSR = "https://api.nationaltransport.ie/gtfsr"
# Note: per-provider product-class mappings live in the python-openpublictransport
# library (each provider's get_transport_type_mapping); they are not duplicated here.

# Provider-specific icons (MDI icons as fallback)
PROVIDER_ICONS = {
    "vrr": "mdi:bus-clock",
    "kvv": "mdi:tram",
    "hvv": "mdi:ferry",
    "hvv_gti": "mdi:ferry",
    "bvg": "mdi:subway-variant",
    "mvv": "mdi:tram",
    "vvs": "mdi:train",
    "vgn": "mdi:subway-variant",
    "vagfr": "mdi:tram",
    "rmv": "mdi:train",
    "trafiklab_se": "mdi:train",
    "nta_ie": "mdi:bus-multiple",
    "sbb": "mdi:train",
    "oebb": "mdi:train",
    "transitous": "mdi:earth",
    "db": "mdi:train",
    "vrn": "mdi:train",
    "vvo": "mdi:tram",
    "ding": "mdi:bus",
    "avv_augsburg": "mdi:tram",
    "rvv": "mdi:bus",
    "bsvg": "mdi:bus",
    "nwl": "mdi:train",
    "nvbw": "mdi:train",
    "beg": "mdi:train",
    "vbn_otp": "mdi:bus-clock",
    "vbn_trias": "mdi:bus-clock",
    "openpublictransport": "mdi:train-variant",
    "otp_custom": "mdi:server-network",
    "national_rail": "mdi:train",
    "rejseplanen": "mdi:train",
}

# Provider-specific entity pictures (logos)
# These can be overridden by the user or use external URLs
# Format: URL to a small logo image (recommended: 256x256 or smaller)
PROVIDER_ENTITY_PICTURES = {
    "vrr": "https://www.vrr.de/favicon.ico",
    "kvv": "https://www.kvv.de/favicon.ico",
    "hvv": "https://www.hvv.de/favicon.ico",
    "hvv_gti": "https://www.hvv.de/favicon.ico",
    "bvg": "https://www.bvg.de/favicon.ico",
    "mvv": "https://www.mvv-muenchen.de/favicon.ico",
    "vvs": "https://www.vvs.de/favicon.ico",
    "vgn": "https://www.vgn.de/favicon.ico",
    "vagfr": "https://www.vagfr.de/favicon.ico",
    "rmv": "https://www.rmv.de/favicon.ico",
    "trafiklab_se": "https://www.trafiklab.se/favicon.ico",
    "nta_ie": "https://www.transportforireland.ie/favicon.ico",
    "sbb": "https://www.sbb.ch/favicon.ico",
    "oebb": "https://www.oebb.at/favicon.ico",
    "transitous": "https://transitous.org/favicon.ico",
    "vrn": "https://www.vrn.de/favicon.ico",
    "vvo": "https://www.vvo-online.de/favicon.ico",
    "ding": "https://www.ding.eu/favicon.ico",
    "avv_augsburg": "https://www.avv-augsburg.de/favicon.ico",
    "rvv": "https://www.rvv.de/favicon.ico",
    "bsvg": "https://www.bsvg.net/favicon.ico",
    "nwl": "https://www.westfalenfahrplan.de/favicon.ico",
    "nvbw": "https://www.efa-bw.de/favicon.ico",
    "beg": "https://www.bahnland-bayern.de/favicon.ico",
    "db": "https://www.bahn.de/favicon.ico",
    "vbn_otp": "https://www.vbn.de/favicon.ico",
    "vbn_trias": "https://www.vbn.de/favicon.ico",
    "openpublictransport": "https://openpublictransport.net/favicon.ico",
    "national_rail": "https://www.nationalrail.co.uk/favicon.ico",
    "rejseplanen": "https://www.rejseplanen.dk/favicon.ico",
}
