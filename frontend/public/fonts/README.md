# Self-hosted fonts — attribution

Both families are licensed under the SIL Open Font License 1.1 and are
self-hosted here (no CDN requests at runtime). License texts are committed
alongside the binaries in this directory.

## Fraunces (display serif — headings)

- Designers: Phaedra Charles and Flavia Zimbardi (Undercase Type)
- Copyright 2018 The Fraunces Project Authors
- License: SIL OFL 1.1 — see `OFL-Fraunces.txt`
- Source: https://github.com/undercasetype/Fraunces, release `1.000`
  (asset `UnderCaseType_Fraunces_1.000.zip`)
- File: `Fraunces-VF.woff2` — the upright variable font
  (`Fonts - Web/Fraunces[SOFT,WONK,opsz,wght].woff2`, renamed; binary
  unmodified). Axes: wght 100–900, opsz 9–144, SOFT, WONK.

## Source Sans 3 (text family — UI/body)

- Designer: Paul D. Hunt (Adobe)
- Copyright 2010–2022 Adobe, with Reserved Font Name 'Source'
- License: SIL OFL 1.1 — see `LICENSE-SourceSans3.md`
- Source: https://github.com/adobe-fonts/source-sans, release `3.052R`
  (asset `WOFF2-source-sans-3.052R.zip`, `WOFF2/TTF/` static instances;
  `.ttf.woff2` suffix simplified to `.woff2`; binaries unmodified)
- Files: `SourceSans3-Regular.woff2` (400), `SourceSans3-Italic.woff2`
  (400 italic), `SourceSans3-Semibold.woff2` (600), `SourceSans3-Bold.woff2` (700)

Monospace (numeric/data) intentionally uses the system stack via
`--font-mono` in `src/styles/tokens.css` — no third self-hosted family.
