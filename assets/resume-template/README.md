# resume-template

Generic single-page sidebar resume in two flavors. The `nightly` skill auto-detects which renderer the user has installed and picks accordingly.

## Files

- `resume.cls` — LaTeX class with the sidebar layout.
- `resume.tex` — LaTeX template the user fills in. Requires `pdflatex` + `paracol`, `titlesec`, `enumitem`, `xcolor`, `geometry`, `hyperref` (all in TeX Live and MiKTeX by default).
- `resume.typ` — Typst alternative. Requires the `typst` binary (single ~30MB executable, no toolchain).
- `Makefile` — `make pdf` or `make typst`.

## Compile

```bash
make pdf      # pdflatex path
make typst    # typst path
```

If neither is installed, the `nightly` skill falls back to a clean markdown resume and notes in `apply-notes.md` that PDF rendering needs `pdflatex` (recommended) or `typst` installed locally.

## Customization hooks (LaTeX)

The class exposes three variables for restyling without touching `resume.cls`:

```latex
\renewcommand{\mysidestyle}{}                  % runs at top of sidebar column — add a banner, photo, etc.
\renewcommand{\mysidewidth}{0.30}              % sidebar width as fraction of page (0.25 – 0.40 typical)
\renewcommand{\mysidecolor}{blue!50!black}     % accent color for section headers
```

## Customization hooks (Typst)

`sidebar-width` and `sidebar-color` are declared at the top of `resume.typ`. Edit and recompile.

## ATS note

Single-column resumes parse more reliably in some ATS systems than multi-column layouts. This sidebar template is ATS-acceptable for most modern parsers (Greenhouse, Lever, Ashby, Workable handle it cleanly), but older Workday installs occasionally scramble multi-column. If targeting a Workday-heavy company and a screen surfaces parsing weirdness, switch to a single-column layout for that application.
