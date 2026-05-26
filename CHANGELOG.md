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

## [Unreleased]

- Remove inherited non-FLAC documentation, examples, aliases, and resource
  scripts so the package is FLAC-only.
- Keep only FLAC command, Python API, and reference resources, centered on
  zone, gridpoint, structure, model, and constitutive-model workflows.
- Standardize bridge runtime configuration on `FLAC_MCP_*` environment
  variables and the `ItascaBridgeClient` name.
- Add product/version-scoped command coverage auditing and mark FLAC2D 6.0/7.0
  as not applicable in the bundled documentation matrix.
- Add FLAC plot-item reference docs for zone, gridpoint, and structural-element
  visualization workflows.
- Add FLAC reference docs for boundary conditions, initial conditions,
  structural-element properties, histories, zone field data, and results export.
- Add FLAC reference docs for FISH intrinsic workflows, interfaces/joints,
  geometry/data/table workflows, and sketch/building-block model generation.
- Resolve FLAC3D 6.0/7.0 command coverage against official legacy command
  indexes and mark version-absent commands as unavailable instead of missing.
- Tighten FLAC2D Python API filtering with explicit out-of-plane API rules.
- Add agentic setup and runtime validation documentation for FLAC2D/FLAC3D
  verification.
- Add `flac_validate_runtime` for non-destructive bridge/runtime/command/file
  smoke validation, with an opt-in destructive `model new` check.

## [0.1.0] - 2026-05-20

Initial release of `flac-mcp`: an MCP server for ITASCA FLAC workflows using
`flac_*` tools, the `src/flac_mcp` package, and the standalone
`itasca-mcp-bridge` runtime bridge.
