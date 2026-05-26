# Version Support Matrix

`flac-mcp` separates documentation support from execution support.

Execution support depends on the FLAC GUI and embedded Python runtime available on the user's machine. Documentation support depends on the bundled command, Python API, and reference resources.

## Product and Version Support

| Product | Version | Command docs | Python API docs | Execution |
| --- | --- | --- | --- | --- |
| FLAC2D | 6.0 | Not applicable | Not applicable | Not applicable in bundled matrix |
| FLAC2D | 7.0 | Not applicable | Not applicable | Not applicable in bundled matrix |
| FLAC2D | 9.0-9.7 | Supported | Product-scoped 9.x baseline | Supported when FLAC2D GUI bridge is running |
| FLAC3D | 6.0 | Supported | Bundled 6.0 snapshot | Supported when FLAC3D GUI bridge is running |
| FLAC3D | 7.0 | Supported | Bundled 7.0 snapshot | Supported when FLAC3D GUI bridge is running |
| FLAC3D | 9.0-9.7 | Supported | 9.x baseline | Supported when FLAC3D GUI bridge is running |

## FLAC 9.x Command Resolution

FLAC 9.x command docs use nearest available bundled baselines.

General rule:

```text
9.7 -> 9.3 -> 9.2 -> 9.1 -> 9.0
9.6 -> 9.3 -> 9.2 -> 9.1 -> 9.0
9.5 -> 9.3 -> 9.2 -> 9.1 -> 9.0
9.4 -> 9.3 -> 9.2 -> 9.1 -> 9.0
9.3 -> 9.3 -> 9.2 -> 9.1 -> 9.0
9.2 -> 9.2 -> 9.1 -> 9.0
9.1 -> 9.1 -> 9.0
```

When a command returns an aliased document, the response includes `version_alias` metadata:

```json
{
  "requested_version": "9.7",
  "source_version": "9.3",
  "content_version": "9.1"
}
```

This means the caller requested 9.7, the nearest 9.3-era documentation was selected, and that page reuses a 9.1 command block.

## Python API 9.x Policy

Python API 9.x coverage currently uses the bundled ITASCA 9.0 FLAC Python API snapshot as the documented 9.x baseline. Runtime validation is recommended for version-specific embedded Python behavior.

## Coverage Tools

Use:

```text
flac_command_coverage
flac_python_api_coverage
```

These tools report product/version coverage and should be used before relying on version-specific command or API lookup results.
