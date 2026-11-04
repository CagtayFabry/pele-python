# Changelog

## Unreleased

## 1.13.0 — 2026-11-04

- Update bundled Pele from 1.12.0 to 1.13.0.
- Revalidate the example notebook and record successful Linux, Windows x64, and
  macOS ARM64 validation for the updated bundle.

## 1.12.0 — 2026-11-04

- Add Pixi check/bump commands and a daily GitHub workflow opening Pele update PRs.
- Derive package versions from Git tags, preserving versions in source archives
  and using a development fallback for source trees without Git metadata.
- Add a shared Pixi test feature and Python 3.10–3.15 environments.
- Prepare GitHub CI for six Linux Python versions and Python 3.14 on Windows x64
  and macOS ARM64, with required quality, package, and browser checks.
- Validate distribution metadata and licenses, derive artifact names from package
  metadata, and produce SHA-256 checksums.
- Add project URLs and contribution, security, and release documentation.

- Render Mermaid diagrams through vendored Pele 1.12.0 and quickjs-ng 0.17.0.2.
- Provide `render_svg`, notebook SVG display through `render`, and structured `PeleError` diagnostics.
- Validate JSON options, generate unique default SVG ID prefixes, and isolate each runtime context.
- Include offline rendering, threading, vendored-asset, packaging, and browser checks.
- Include an example notebook with flowchart, sequence, and a 63-node binary tree.
