# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PreTeXt math course project (linear algebra / MTH 205). Source content lives as PreTeXt XML (`.ptx`) files, and LaTeX worksheets (`.tex` in `source/latex/`) are converted to PreTeXt for inclusion in the course.

## Build and Preview Commands

```bash
pretext build course        # Build HTML output
pretext view course         # Serve and open in browser
pretext build print         # Build PDF
pretext build --deploys     # Build all targets for deployment
pretext deploy              # Push to GitHub Pages
pretext deploy --stage-only # Stage without pushing (preview with `pretext view -d`)
```

For standalone files (slides, pdfs, SCORM):
```bash
pretext build pdf -i source/latex/filename.ptx
pretext build slides -i source/slides/chapter.ptx
```

## Converting LaTeX Worksheets to PreTeXt

The primary ongoing task in this repo is converting `.tex` worksheets to `.ptx` format.

### Automated conversion
```bash
python convert.py source/latex/filename.tex
# Outputs: source/latex/filename.ptx
```

### Manual/agent conversion
Follow `LATEX_TO_PRETEXT_CONVERSION.md` (or `lora_convert.md` for the more detailed version). Key rules:
- Skip LaTeX preamble (everything before `\begin{document}`)
- First `{\bf ...}` / `\textbf{...}` → `<title>`
- `\begin{tcolorbox}...\begin{itemize}` → `<objectives><introduction>` + `<ul>`
- Text before outer `\begin{enumerate}` → `<introduction>`
- Each outer `\item` → `<exercise>`; nested `\item` → `<task>`
- `\vs{X}` or `\vfill` → `workspace="Xin"` attribute on the element
- `$...$` → `<m>...</m>`; `$$...$$` or `\[...\]` → `<md>...</md>`
- `&` in math → `&amp;`
- Converted files go in `source/activities/` (not `source/latex/`)

### PreTeXt worksheet structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<worksheet>
  <title>...</title>
  <objectives>...</objectives>      <!-- from tcolorbox -->
  <introduction>...</introduction>  <!-- text before enumerate -->
  <exercise workspace="1in">
    <statement><p>...</p></statement>
    <task workspace="1.5in"><statement><p>...</p></statement></task>
  </exercise>
</worksheet>
```

## Project Structure

- `project.ptx` — build targets manifest (targets: `course`, `print`, `pdf`, `slides`, `scorm`)
- `source/main.ptx` — assembles the full course via `xi:include`; add new files here
- `source/docinfo.ptx` — shared macros (e.g., `\mattwo`, `\xvec`, `\col`)
- `source/latex/` — original `.tex` files and their converted `.ptx` counterparts
- `source/activities/` — canonical location for converted worksheet `.ptx` files
- `publication/` — publication config files controlling output format options
- `output/` — generated HTML (do not edit)

## Adding Content to the Course

After converting a `.tex` file to `.ptx`, register it in `source/main.ptx` with an `xi:include`:
```xml
<xi:include href="./activities/my-worksheet.ptx"/>
```
or if placed in `source/latex/`:
```xml
<xi:include href="./latex/my-worksheet.ptx"/>
```

## Dependencies

- `pretext==2.37.1` (see `requirements.txt`)
- Python with `lxml` (used by `convert.py`)
- LaTeX distribution (for PDF output and `<latex-image>` elements)
