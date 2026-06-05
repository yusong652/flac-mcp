# Changelog

All notable changes to `flac-mcp` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Add a new section per release before tagging. The publish workflow extracts
the section matching the tag version and uses it as the GitHub release body.
The release will fail to publish if no matching entry is found.

## [x.y.z] - YYYY-MM-DD

Description of the release.
-->

## [0.5.1] - 2026-06-06

### Fixed
- Replaced leftover PFC examples in MCP tool descriptions with FLAC
  equivalents (descriptions only — no behavior change). Affects
  `flac_browse_python_api` / `flac_query_python_api` (API-path and keyword
  examples), the shared command/API search-query field descriptions,
  `flac_browse_commands`, and `flac_execute_code`: e.g.
  `itasca.ball` / `itasca.wall.facet` → `itasca.zone` / `itasca.interface.node`,
  `ball create` / `contact force` → `zone create` / `gridpoint velocity`. All
  new examples verified against the live FLAC3D 9.0 Python API.

## [0.5.0] - 2026-06-04

### Added
- `--bridge-port` CLI argument to override the bridge connection port —
  shorthand for `--bridge-url ws://localhost:PORT`. When a full
  `--bridge-url` / `FLAC_MCP_BRIDGE_URL` is also supplied, only its port is
  overridden.

### Changed
- `flac_execute_task` now submits over the bridge's `execute_task` message
  (renamed from `pfc_task` so the shared bridge protocol is product-neutral;
  the bridge keeps `pfc_task` as a deprecated alias). **Requires
  `itasca-mcp-bridge >= 0.1.5`** — older bridges silently ignore the message
  and submission times out. If that happens, confirm the bridge version with
  `flac_execute_code` (`import itasca_mcp_bridge;
  print(itasca_mcp_bridge.__version__)`) and upgrade by re-running addon.py.
- Slimmed `flac_check_task_status` pagination to `total_lines` + `line_range`,
  replacing the heavier pagination object. Output windows are still selected
  with `skip_newest` / `limit` / `filter_text`.
- Bumped `itasca-mcp-bridge` to `0.1.5` (submodule pin). Picks up the PySide6
  Qt task-pump fix so the bridge starts on PFC 9.7+ (Python 3.10 / Qt6) and
  the `execute_task` protocol rename.

## [0.1.1] - 2026-06-03

### Fixed
- Bumped `itasca-mcp-bridge` to `0.1.3` (submodule pin `25668d7`), picking up
  the command-log and task-log abspath-vs-CWD fixes. `itasca.command()` output
  and `flac_check_task_status` no longer come back empty when the engine's
  working directory diverges from Python's (headless consoles, or after a task
  `os.chdir()`): the task log and `tasks.json` are now read from a bridge root
  frozen at startup rather than the live working directory.

### Changed
- Task `elapsed_time` is now rounded to 2 decimals in `flac_check_task_status`
  and `flac_list_tasks` (e.g. `0.01` instead of `0.010000944137573242`). The
  field stays numeric; the bridge still reports full precision, with rounding
  applied at the MCP presentation layer alongside `start_time` / `end_time`.

### Documentation
- Added a README header image (#51).

## [0.1.0] - 2026-05-20

Initial release of `flac-mcp`. Scaffolded from `pfc-mcp` 0.3.15: the MCP
server was renamed (`flac_*` tools, `src/flac_mcp` package) and retargeted
to the ITASCA FLAC product family (FLAC2D/FLAC3D); the in-product bridge
runtime was extracted to the standalone `itasca-mcp-bridge` package. The
bundled command/API/reference knowledge base is inherited from `pfc-mcp`
and currently covers ITASCA command documentation.

## [0.3.15] - 2026-05-16

Version-aware reference documentation. The `contact-models` reference grows
from 5 to 22 models (all PFC mechanical + thermal contact models) and
`pfc_browse_reference` becomes version-aware for PFC 6.0/7.0/9.0.

- `pfc_browse_reference` gains a `version` parameter (6.0/7.0/9.0, default
  7.0) mirroring `pfc_browse_commands`: the model list is filtered by
  version availability, requesting a model absent in the target version
  returns a friendly `item_unavailable_for_version` error (with
  `available_versions`), and not-found suggestions are version-filtered.
- New models: arrlinear, bilinear, burger, eepa, fish, flatjoint,
  hysteretic, jkr, lineardipole, null, smoothjoint, softbond,
  springnetwork, thermalnull, thermalpipe, plus 9.0-only `mohr` and
  `subspringnetwork`. The 5 legacy curated models keep their content.
- Content is shared across versions (measured: 7.0 == 9.0, and 6.0 == 7.0
  for shared properties), so no per-version data duplication. Differences
  are encoded as a per-model `availability` map and per-property `since`
  markers (flatjoint `fj_cohres`/`fj_resmode` since 7.0; softbond
  `rgap`/`sb_coh`/`sb_fa`/`sb_mcf` since 9.0). `range-elements` and
  `plot-items` have no `availability` and remain version-agnostic
  (backward compatible).
- Property extraction reworked to split on `<dt id="kwd:...">` markers
  instead of pairing `<dt>/<dd>`, so pages that nest base properties in a
  child `<dl class="keyword">` (e.g. eepa) no longer bleed text or drop
  the nested keywords; model-specific properties collapse into a single
  clean group.

## [0.3.14] - 2026-05-15

Second wave of command documentation expansion: 123 new commands across
8 new scopes, bringing totals to 21 categories / 362 commands (was 13 / 239).

- `geometry` (34): nodes, edges, polygons, import/export, refinement, tessellation
- `fracture` (32): DFN — create, generate, intersections, templates, joint-set
- `table`    (11): numerical x/y tables for boundary conditions and history data
- `group`     (4): named-group lifecycle (create / list / rename / slot)
- `trace`     (7): per-object trace recording (lifecycle / export / interval)
- `project`   (6): GUI project containers (new / save / restore / execute)
- `data`     (26): user data containers — label/scalar/vector/tensor sub-namespaces
- `domain`    (3): domain extent, boundary conditions, periodic-cell strain-rate

All entries populated for PFC 6.0/7.0/9.0 (7 commands marked unavailable in
6.0 as new in later versions; e.g. `fracture intersections` machinery).

Note: the "dfn" doc module is exposed under the scope name `fracture` to
match the actual command verb users type. Dotted HTML stems (e.g.
`cmd_geometry.edge.create.html`, `cmd_data.scalar.create.html`) are mapped
to dash-separated JSON keys (`edge-create`, `scalar-create`) following the
rblock convention. `parse_pfc{600,700,900}.py` `build_html_map` learned the
same dot→dash rule.

`range` was considered but not added — the HTML files under
`range_manual/range_commands/` are syntax reference (rangelogical,
rangenaming, rangephrase), not commands.

Fixes `pfc_browse_commands` to accept the natural space-separated form
of compound sub-commands (e.g. `geometry edge create`, `data scalar
create`, `fracture intersections compute`, `contact cmat add`).
Previously the lookup only matched the stored dash form (`edge-create`,
`cmat-add`), forcing users to type a non-PFC-syntax variant.

## [0.3.13] - 2026-05-15

Expands PFC command documentation coverage from 177 to 239 entries
across 13 categories (was 10). Three new scopes — `program` (28
commands: license, threads, log, system, lifecycle), `history` (8:
interval, export, label, results), and `fish` (11: callback, define,
list, debug, trace) — join filled gaps in `model` (+9: creep,
dynamic, energy, factor-of-safety, fluid, list, precision, step,
title), `contact` (+3: extra, history, list), and `fragment` (+3:
groupisolated, groupslot, map). All entries are populated for PFC
6.0/7.0/9.0. These commands were previously skipped because their
Python SDK equivalents return nothing; now that `itasca.command()`
stdout is captured via the bridge log, exposing them lets agents
read program/model/history/contact list output through normal
documentation lookup. A new `bootstrap_missing.py` script under
`command_docs/` walks the installed PFC HTML manuals and writes
complete versioned JSON.

Trims trailing float-precision noise from BM25 result scores in
`pfc_query_command` and `pfc_query_python_api` (e.g.
`2.4743000000000004` → `2.47`).

## [0.3.12] - 2026-05-14

Surfaces the structured cancellation outcomes from pfc-mcp-bridge >=
0.3.2 through `pfc_execute_code`: `terminated` (bridge aborted at the
deadline, partial output returned, PFC state may be partially
modified), `timeout` with `details.method="stuck_in_c"` (snippet stuck
in a C extension; bridge may recover when the C call returns),
`interrupted`, and the default `timeout` path. Local wait widens to
`timeout_ms / 1000 + 5.0s` so the bridge has room to deliver the
`terminated` response after its own grace window.

Drops `pfc_mcp.formatting.normalize_status()` (and its re-export from
`pfc_mcp.tools.task_formatting`); the shim only mapped legacy
`success`/`error` status from pre-0.3.0 bridges. Requires
pfc-mcp-bridge >= 0.3.0; pin `pfc-mcp<0.3.12` if you can't upgrade the
bridge.
