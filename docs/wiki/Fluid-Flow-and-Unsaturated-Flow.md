# Fluid Flow and Unsaturated Flow

This page summarizes the FLAC 9.x fluid-flow command behavior captured in the bundled command knowledge base.

## Configuration Command

FLAC 9.1 and later use:

```text
model configure fluid-flow
```

FLAC 9.0 used:

```text
model configure fluid
```

For 9.x work, query the command docs with the target version:

```text
flac_browse_commands(command="model configure", product="flac3d", version="9.7")
```

## Zone Fluid Command

Browse:

```text
flac_browse_commands(command="zone fluid", product="flac3d", version="9.7")
```

Important 9.x command areas include:

- `zone fluid active`
- `zone fluid cmodel assign`
- `zone fluid property`
- `zone fluid density`
- `zone fluid unsaturated`
- `zone fluid permeability-saturation`
- `zone fluid steady-state`
- `zone fluid timestep`

## Runtime-Validated FLAC3D 9.x Commands

The following commands were accepted in a FLAC3D 9.x runtime smoke test:

```text
model configure fluid-flow
zone fluid property porosity 0.35
zone fluid property fluid-modulus 2e9
zone fluid property mobility-coefficient 1e-12
zone fluid density 1000
zone fluid unsaturated off
zone fluid unsaturated cutoff 0.0
zone fluid unsaturated brooks-corey 1.0 2.0
zone fluid unsaturated gardner 1.0 2.0 1.0
zone fluid unsaturated van-genuchten 2.0 0.5 1.0
zone fluid permeability-saturation constant
zone fluid permeability-saturation s-shape
zone fluid timestep fix 1e-3
```

The runtime also accepted these fluid model assignments:

```text
zone fluid cmodel assign isotropic
zone fluid cmodel assign anisotropic
zone fluid cmodel assign active
zone fluid cmodel assign inactive
```

## Runtime-Rejected Forms

The runtime smoke test rejected:

```text
zone fluid cmodel assign linear
zone fluid timestep fixed 1e-3
```

Use `fix`, not `fixed`, for the timestep command:

```text
zone fluid timestep fix 1e-3
```

## Table-Based Permeability Saturation

This form parses as a table reference:

```text
zone fluid permeability-saturation table "table-name"
```

If the named table does not exist, FLAC reports a semantic error. Create the table first before applying it.

## Practical Guidance

For unsaturated-flow workflows:

1. Query command docs for the target product/version.
2. Start with a minimal model.
3. Run a small command smoke test in FLAC.
4. Only then generate larger `.dat` or Python-driven simulations.
