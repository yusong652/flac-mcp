# Command Documentation Maintenance

FLAC command documentation is stored as JSON resources under
`src/flac_mcp/knowledge/resources/command_docs`.

Use this workflow when adding or refreshing command documentation:

1. Refresh generated FLAC3D 6.0/7.0 command docs when the cached official pages
   change:

   ```powershell
   uv run python scripts/update_flac3d_legacy_command_docs.py --parse-pages --write
   ```

   FLAC 9.1-9.7 command requests use the nearest bundled 9.x command block.
   FLAC 9.4 and later should resolve against the 9.3-era baseline first, then
   older 9.x blocks. Add an explicit 9.1+ version block only when official
   syntax differs from the 9.0 baseline, such as `model configure fluid-flow`
   and `zone fluid` unsaturated-flow controls.

2. Regenerate the command index after adding, deleting, or renaming command JSON
   files:

   ```powershell
   uv run python scripts/generate_flac_command_index.py --write
   ```

   The generator preserves existing index metadata by default. Use
   `--refresh-metadata` only when you intentionally want to refresh index
   descriptions, syntax, and Python availability flags from the command files.

3. Validate the bundled command docs before opening a PR:

   ```powershell
   uv run python scripts/generate_flac_command_index.py --check
   uv run python scripts/validate_flac_command_docs.py
   ```

The validator checks that every command file is indexed, every indexed file
exists, unavailable version entries explain why they are unavailable, available
version entries include command and syntax text, and keyword entries include
user-facing names and syntax.
