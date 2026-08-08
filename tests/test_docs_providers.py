"""The provider docs must describe exactly what the code ships.

`docs/providers/index.md` carries the provider comparison and the timezone
table. Both drifted before — the comparison showed providers as columns and
stopped at 35 of 38, and `db`, `rejseplanen` and `national_rail` appeared
nowhere on the page at all. These tests pin the four columns that have a source
of truth in code; the rest (platform info, alerts, stop search style) is a
documentation claim with nothing to check it against.
"""

import re
from pathlib import Path

import yaml
from openpublictransport.providers import get_provider_class

from custom_components.openpublictransport.const import PROVIDERS
from custom_components.openpublictransport.trip import TRIP_CAPABLE_PROVIDERS

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_PROVIDERS = REPO_ROOT / "docs" / "providers"
INDEX = DOCS_PROVIDERS / "index.md"
MKDOCS = REPO_ROOT / "mkdocs.yml"

# Row shape: | [Name](page.md) | `id` | Region | API Type | API Key | Real-time | … |
_MATRIX_ROW = re.compile(r"^\| \[([^\]]+)\]\(([^)]+)\) \| `([a-z0-9_]+)` \|(.+)\|\s*$", re.M)
# Row shape: | Name | `id` | Timezone |
_TIMEZONE_ROW = re.compile(r"^\| ([^|]+?) \| `([a-z0-9_]+)` \| ([^|]+?) \|\s*$", re.M)

# Documented values the code cannot express.
#   otp_custom: the class reports no key requirement, but a self-hosted instance
#   may well be protected — the docs say "Optional" on purpose.
API_KEY_EXCEPTIONS = {"otp_custom": "Optional"}
#   These two have no single fixed zone.
TIMEZONE_EXCEPTIONS = {
    "transitous": "Per-stop (automatic)",
    "otp_custom": "Europe/Berlin (or per OTP2 config)",
}


def _matrix_rows():
    """Return {provider_id: (name, page, [cells…])} from the comparison table."""
    rows = {}
    for name, page, provider_id, rest in _MATRIX_ROW.findall(INDEX.read_text(encoding="utf-8")):
        rows[provider_id] = (name, page, [cell.strip() for cell in rest.split("|")])
    return rows


def _timezone_rows():
    """Return {provider_id: timezone} from the timezone table."""
    section = INDEX.read_text(encoding="utf-8").split("## Timezone Handling", 1)[1]
    section = section.split("## Transport Type Mapping", 1)[0]
    return {provider_id: tz.strip() for _, provider_id, tz in _TIMEZONE_ROW.findall(section)}


def test_comparison_lists_every_provider():
    assert set(_matrix_rows()) == set(PROVIDERS)


def test_timezone_table_lists_every_provider():
    assert set(_timezone_rows()) == set(PROVIDERS)


def test_api_key_column_matches_the_providers():
    """"Yes" in the docs must mean the provider class demands a key."""
    mismatches = []
    for provider_id, (_, _, cells) in _matrix_rows().items():
        documented = cells[2]
        if API_KEY_EXCEPTIONS.get(provider_id) == documented:
            continue
        required = get_provider_class(provider_id)(None).requires_api_key
        if documented.startswith("Yes") is not required:
            mismatches.append(f"{provider_id}: docs say {documented!r}, code says {required}")
    assert not mismatches, mismatches


def test_trip_planner_column_matches_the_capability_set():
    documented = {pid for pid, (_, _, cells) in _matrix_rows().items() if cells[6] == "Yes"}
    assert documented == set(TRIP_CAPABLE_PROVIDERS)


def test_timezones_match_the_providers():
    mismatches = []
    for provider_id, documented in _timezone_rows().items():
        if TIMEZONE_EXCEPTIONS.get(provider_id) == documented:
            continue
        actual = get_provider_class(provider_id)(None).get_timezone()
        if documented != actual:
            mismatches.append(f"{provider_id}: docs say {documented!r}, code says {actual!r}")
    assert not mismatches, mismatches


def test_every_provider_links_to_an_existing_page():
    missing = [
        f"{provider_id} -> {page}"
        for provider_id, (_, page, _) in _matrix_rows().items()
        if not (DOCS_PROVIDERS / page).is_file()
    ]
    assert not missing, missing


def test_every_provider_page_is_in_the_nav():
    """An unreferenced page still builds, just unreachable — catches orphans."""
    # mkdocs.yml uses !!python/name: tags for some extensions; ignore what we can't load.
    nav_text = MKDOCS.read_text(encoding="utf-8")
    referenced = set(re.findall(r"providers/([a-z0-9_-]+\.md)", nav_text)) - {"index.md"}
    on_disk = {path.name for path in DOCS_PROVIDERS.glob("*.md")} - {"index.md"}
    assert on_disk - referenced == set(), sorted(on_disk - referenced)
    assert referenced - on_disk == set(), sorted(referenced - on_disk)


def test_nav_is_valid_yaml():
    """Guard against a broken nav block after hand-editing."""
    text = MKDOCS.read_text(encoding="utf-8")
    text = re.sub(r"!!python/name:\S+", "null", text)
    config = yaml.safe_load(text)
    assert any("Providers" in entry for entry in config["nav"] if isinstance(entry, dict))
