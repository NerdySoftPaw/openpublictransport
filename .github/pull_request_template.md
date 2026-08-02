<!--
  Thanks for contributing! Keep this short — delete any section that does not apply.
-->

## What does this change?

<!-- One or two sentences. Link the issue: Fixes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] New provider
- [ ] Translation
- [ ] Documentation
- [ ] Refactor / maintenance
- [ ] Breaking change

## How was it tested?

<!--
  Which provider and stop did you test against, on which Home Assistant version?
  "Set up VVS / Stuttgart Hbf on HA 2026.7.2, departures and delays correct over 30 min."
-->

## Checklist

- [ ] `pytest tests/ -v` passes
- [ ] `pre-commit run --all-files` passes
- [ ] No API keys, tokens or personal stop data left in the diff
- [ ] Tested against a real Home Assistant instance, not only unit tests

<!-- ─────────── delete the sections below if they do not apply ─────────── -->

### New provider

- [ ] Added to the provider table in `README.md` and to the docs
- [ ] Stop search, departures and delays verified against the provider's own app
- [ ] API key requirement documented (none / free / paid)
- [ ] Data licence and terms of use checked and noted
- [ ] Error handling for empty responses and upstream outages

### Translations

- [ ] All keys present, none left in English by accident
- [ ] `en.json` updated too if new strings were introduced
- [ ] Placeholders like `{stop}` and `{minutes}` kept intact

### Breaking change

<!-- What breaks, and what do users need to do? This goes into the release notes. -->

- [ ] Migration steps documented in `MIGRATION.md`
