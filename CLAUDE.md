# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PyPI package `runtilities` (import name `running` — intentionally confusing, per the README). A grab-bag of
running-related utilities: API clients for race-registration/results platforms, GPS track parsers, and CLI
scripts for age-grading and club stats. There is no single application entry point — each module in `running/`
is largely independent.

Much of this codebase is old and not actively maintained (some modules still have Python 2-era code and imports
of packages not in `requirements.txt`, e.g. `competitor.py` imports `IPython.core.debugger.Tracer` and
`runningclub`). Don't assume a module works or is in active use just because it's in the package — check git log
history for a file before assuming it's current. The actively maintained modules (per git history) are
`runsignup.py` and `runningahead.py`.

## Environment

- Windows dev machine; a `.venv` already exists at the repo root (Python 3.10 venv, not committed — it's
  gitignored — but present locally). Activate it before running anything: `.venv\Scripts\activate` (or use
  `.venv/scripts/activate` from Git Bash).
- Dependencies are pinned in `requirements.txt` (this is a snapshot of the working venv, not a curated list —
  it's broader than `setup.py`'s `install_requires`, which is the actual runtime dependency list for the
  package). Regenerate with `pip freeze` when it drifts from the venv rather than hand-editing individual lines.
- No linting/CI config exists in this repo.

## Testing

- `tests/` (added 2026-07) holds the only test suite in this repo, currently covering `runsignup.py` /
  `runsignup_fluent.py` only — nothing else in `running/` has tests. Run with
  `.venv/Scripts/python -m pytest tests/` (or `pytest tests/` with the venv active).
- `pytest` and `responses` are dev-only test dependencies — they're in `requirements.txt` (the venv snapshot)
  but deliberately not in `setup.py`'s `install_requires`, since they're not needed at runtime by consumers of
  the package.
- `test_runsignup.py` / `test_runsignup_fluent.py` are mocked (via `responses`) and hit no network — they verify
  the `RunSignupBase`/`RunSignUp`/`RunSignupFluent` credential and session wiring, in particular the
  `api_reg_token`/`api_reg_secret` handling (`api_reg_token` sent as `rsu_api_reg` GET param, `api_reg_secret`
  sent as `X-RSU-API-REG-SECRET` header) required per
  https://info.runsignup.com/2026/07/17/new-api-registration-requirements/.
- `test_runsignup_live.py` makes real calls to `api.runsignup.com` and is skipped by default — it's gated by
  environment variables (`RSU_TEST_RACE_ID` required; `RSU_KEY`/`RSU_SECRET`, `RSU_API_REG_TOKEN`/
  `RSU_API_REG_SECRET`, and `RSU_TEST_CLUB_ID` optionally enable more tests) so a plain `pytest` run never
  touches the network or needs credentials. Besides the happy-path calls, it also confirms *rejection*:
  `RSU_KEY`/`RSU_SECRET` + `RSU_TEST_CLUB_ID` enables a wrong-secret-gets-rejected test, and additionally
  enables a wrong-api_reg_token/api_reg_secret-gets-rejected test. Confirmed live 2026-07-30: RunSignUp already
  validates a *supplied* api_reg_token/api_reg_secret and rejects a bad one today, even though it doesn't
  require one until 2027-01-01 (omitting it entirely still works, as expected pre-enforcement).
- No `python-dotenv` in this project, so a `.env` file (already covered by `.gitignore`'s `.env` line) isn't
  auto-loaded — the user loads it into their own shell before running pytest, e.g. Git Bash
  `set -a; source .env; set +a`, or a small `Get-Content .env | ForEach-Object {...}` loop in PowerShell. This
  is how the live-test env vars below are expected to be supplied.
- Don't run `test_runsignup_live.py` yourself with real credentials, and don't create/read a file holding them
  (e.g. a `.env`) — the user sets those env vars and runs it in their own terminal, then reports back pass/fail.
  A failed assertion in this file prints the actual param/header values, so real credentials must never pass
  through a shell command or file you execute.

## Build / release

- Version lives in exactly one place: `running/version.py` (`__version__`). Bump it there before a release; the
  commit convention is a standalone commit `version X.Y.Z`.
- `setup.py` reads the version from `running/version.py`. Build with `python -m build` (there's a VS Code task
  "push to pypi" in `.vscode/tasks.json` that runs `python -m build; twine upload dist/*-<version>.*`) — this
  publishes to PyPI, so don't run it without the user's explicit intent.
- Console scripts are registered as entry points in `setup.py` (`entry_points.console_scripts`) — if you add a
  new CLI script under `running/`, register it there (and in `scripts=[...]` for direct install) to match the
  existing pattern.

## Architecture notes

### API client modules (the actively maintained core)

- **`runsignup.py`** — client for the RunSignUp.com REST API (`api.runsignup.com`, migrated from the old
  `runsignup.com/rest` host — see the comment at the top of the file). Contains multiple layers:
  - `RunSignupBase` — session/auth/low-level-request base class (`__init__`, `open`/`close`,
    `__enter__`/`__exit__`, `_rsuget`, `_rsugetcsv`). Split out from `RunSignUp` (2026-07) specifically so it
    can be imported without pulling in `RunSignupFluent`'s `universalclient`/`rauth` dependency — the intent is
    that `contracts/contracts/app/src/contracts/runsignup.py`'s independent `RunSignUp` fork (see "Downstream
    consumers" below) could eventually inherit from this instead of hand-duplicating the same session/auth
    code; that port hasn't been done yet, only the base class exists so far.
  - `RunSignUp(RunSignupBase)` — the main session-based client (`with RunSignUp(key=..., secret=...) as rsu:`),
    adding the domain methods (`members`, `getrace`, `getraceevents`, `getracedivisions`, `getresultsets`,
    `geteventresults`, `geteventresultscsv`) on top of the base. Supports `key`/`secret` credentials or no
    credentials for public endpoints (`credentials_type` in `__init__` is `'key'` or `'none'`). The old
    `email`/`password` Login API mode was removed 2026-07 — RunSignUp's Login API is deprecated; only key/secret
    auth remains.
  - Separately, per https://info.runsignup.com/2026/07/17/new-api-registration-requirements/, RunSignUp requires
    all API callers to register (free) and pass the resulting `api_reg_token`/`api_reg_secret` on every call
    starting 2027-01-01 — enforced alongside `key`/`secret`, not a replacement for it. Both `RunSignUp` (via
    `RunSignupBase`) and `RunSignupFluent` accept these as constructor params (`api_reg_token` sent as
    `rsu_api_reg` GET param, `api_reg_secret` sent as `X-RSU-API-REG-SECRET` header); `updatemembercache`/
    `members2csv` pass them through.
  - `ClubMembership` / `ClubMember` / `ClubMemberships` — value objects and an indexed collection for club
    roster processing, with a membership-key caching mechanism (`add2cache`/`incache`) used to detect
    duplicate/renewed memberships across sync runs.
  - Module-level functions (`updatemembercache`, `members2csv`) are batch/CSV-oriented helpers layered on top
    of the class-based client.
- **`runsignup_fluent.py`** — `RunSignupFluent`, a fluent-style client built on `universalclient.Client`
  (e.g. `rsu.race._(raceid).participants.get(...)`), split out of `runsignup.py` (2026-07) into its own module
  so importing `runsignup.py` (and specifically `RunSignupBase`) doesn't require `universalclient`/`rauth` to be
  installed. Prefer this for new work unless there's a reason to match existing `RunSignUp` call sites.
- **`runningahead.py`** — client for the RunningAhead API (`RunningAhead` class), OAuth2-based
  (`requests_oauthlib`). Includes unit-conversion helpers (`dist2miles`, `dist2meters`) for RunningAhead's
  `{'value':..., 'unit':...}` distance representation.
- **`ultrasignup.py`**, **`athlinks.py`** — similar-shaped scraper/API clients for those platforms (HTML
  scraping via `httplib2`/`BeautifulSoup` rather than a clean REST API in some cases — check the module before
  assuming a JSON API).
- Each `*.py` client module generally pairs with a `*results.py` CLI script (e.g. `runningaheadresults.py`,
  `ultrasignupresults.py`, `athlinksresults.py`) that wraps the client to fetch and write out race results, and
  `runningaheadmembers.py`/`runningaheadparticipants.py`/`ra2membersfile.py` for membership/participant sync
  scripts.

### GPS/track parsing

- `gpx2kml.py`, `parsetcx.py`, `comparegpx.py`, `parserun-bk3.py`, `parseralogxml.py` — independent parsers/
  converters for GPX, TCX, and vendor-specific track/log formats (Garmin, RideWithGPS-style `.alr`/log XML).
  These don't share a common base class; each is a standalone script with a `main()`.

### Results/scoring

- `competitor.py` — legacy scraper for competitor.com results (see "not actively maintained" note above).
- `parseresults.py`, `analyzeagegrade.py`, `renderclubagstats.py`, `competitor2csv.py` — post-processing of
  race results into age-grade statistics and club standings; these are the heavier CLI scripts (700-800 lines).
- `xmldict.py` / `xmldict1.py` / `xmldict2.py` / `xmlreader.py` — XML<->dict conversion utilities used by
  several of the parsers above. Note `xmldict1.py`, `xmldict2.py`, and `parserun-bk3.py` are explicitly excluded
  from git tracking in `.gitignore` ("specific project files") even though committed copies exist in `build/` —
  treat these three as scratch/backup files, not canonical source.

### Shared exceptions

`running/__init__.py` defines base `parameterError` / `accessError` exceptions; several modules redeclare
identical local versions instead of importing the shared ones (e.g. `runsignup.py`, `runningahead.py` each
define their own `accessError`/`parameterError`). This is existing inconsistency, not a bug to silently "fix" —
match whatever the file you're editing already does.

## Downstream consumers

This package isn't standalone — breaking changes to `runsignup.py` (e.g. constructor signatures) ripple into
sibling repos under `Documents\Lou's Software\projects\`. Known consumers of `running.runsignup` (`RunSignUp`,
`members2csv`) and `running.runsignup_fluent` (`RunSignupFluent`):
- `members/members/app/src/members/community.py`, `.../scripts/membership_cli.py`,
  `.../members/views/admin/awards_admin.py` — via `members/helpers.py`'s `make_runsignup_client()` /
  `make_runsignup_fluent_client()` factories, which as of 2026-07 import `RunSignupFluent` from
  `running.runsignup_fluent` (it moved out of `running.runsignup`) — this requires `runtilities` to be bumped
  past the pinned `3.0.0.dev1` in `members/app/requirements.txt` before that import works.
- `rrwebapp/rrwebapp/app/src/rrwebapp/views/admin/results.py`, `.../views/admin/member.py`

`contracts/contracts/app/src/contracts/runsignup.py` is **not** an import of this package — it's an independent
forked copy (per its header: "Create from loutilities.runsignup") with its own `RunSignUp` class. Changes made
here (e.g. the 2026-07 removal of `email`/`password` login, or the `api_reg_token`/`api_reg_secret` support for
RunSignUp's Jan 2027 API registration requirement) do not propagate there automatically and must be ported by
hand if wanted.

When wiring `api_reg_token`/`api_reg_secret` into a downstream app's config, the chosen key names are
`RSU_API_REG_TOKEN` / `RSU_API_REG_SECRET`, matching the existing `RSU_KEY`/`RSU_SECRET` convention.

`runningclub/` also references an old `runsignup`-style API but looks abandoned (not a git repo, files dated
2013–2021, Python 2.7 build artifacts) — verify before assuming it needs updates for changes here.

## `build/` directory

`build/lib/running/` and `build/scripts-*/` contain stale copies of the package from previous `setup.py build`
runs, for multiple old Python versions (2.7, 3.6). These are build artifacts, not source — never edit files
under `build/`; edit the corresponding file under `running/` instead.
