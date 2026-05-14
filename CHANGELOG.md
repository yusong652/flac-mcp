# Changelog

All notable changes to `pfc-mcp` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Add a new section per release before tagging. The publish workflow extracts
the section matching the tag version and uses it as the GitHub release body.
The release will fail to publish if no matching entry is found.

## [x.y.z] - YYYY-MM-DD

Description of the release.
-->

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
