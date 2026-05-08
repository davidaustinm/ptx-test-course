# LaTeX to PreText Worksheet Conversion Process

This document describes the systematic process used to convert LaTeX worksheet source files to PreText worksheet format.

## Overview

Convert a LaTeX document (`.tex` file) containing exercises and activities into a PreText worksheet (`.ptx` file) with proper semantic markup.

## File Organization

- **Source**: LaTeX file located in `source/latex/` (e.g., `21-SVD.tex`)
- **Output**: PreText file placed in `source/activities/` with `.ptx` extension (e.g., `21-SVD.ptx`)

## Conversion Steps

### Step 1: Ignore LaTeX Preamble
Skip everything before the actual content begins. Do not attempt to convert:
- `\documentclass` declarations
- `\usepackage` commands
- Custom command definitions (`\newcommand`, `\renewcommand`)
- Document setup commands (`\pagestyle`, `\setlength`, etc.)

Start converting from the actual content (after `\begin{document}`).

### Step 2: Extract and Process Objectives (tcolorbox)

**LaTeX Structure:**
```latex
\begin{tcolorbox}
Introductory text
\begin{itemize}
    \item First point
    \item Second point
\end{itemize}
\end{tcolorbox}
```

**PreText Structure:**
```xml
<objectives>
  <introduction>
    <p>Introductory text</p>
  </introduction>
  <ul>
    <li>First point</li>
    <li>Second point</li>
  </ul>
</objectives>
```

**Rules:**
- Convert the introductory text before the list into `<introduction><p>` ... `</p></introduction>`
- Convert itemize lists to `<ul>` with `<li>` elements for each item
- Place this as the first major section of the worksheet

### Step 3: Create Worksheet with Title

**Structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<worksheet>
  <title>Title from the first bold text in document</title>
  <objectives>
    ... (from Step 2)
  </objectives>
  <introduction>
    ... (from Step 4)
  </introduction>
  ... (exercises from Step 5)
</worksheet>
```

**Rules:**
- Use the first `{\bf text}` or `<strong>` markup in the document as the `<title>`
- This is typically the document header

### Step 4: Extract Introductory Content

**LaTeX Structure:**
```latex
\noindent
{\bf Title} -- Course info
Introductory paragraphs...

\begin{enumerate}
```

**PreText Structure:**
```xml
<introduction>
  <p>Course info and related notes (with course code marked as <term>)</p>
  <p>Introductory paragraphs...</p>
</introduction>
```

**Rules:**
- Create an `<introduction>` element after the `<objectives>`
- Extract all text that appears before the outer `<enumerate>`
- Place this text in `<p>` elements within the introduction
- Include course code references, URLs, and explanatory text

### Step 5: Convert Enumerate Items to Exercises

**LaTeX Structure:**
```latex
\begin{enumerate}
    \item Exercise 1 content
        \begin{enumerate}
            \item Sub-task 1
            \item Sub-task 2 \vfill
        \end{enumerate}
    \item Exercise 2 content
    \item Exercise 3 content \vfill
\end{enumerate}
```

**PreText Structure:**
```xml
<exercise workspace="...">
  <statement>
    <p>Exercise 1 content</p>
  </statement>
  <task workspace="...">
    <statement><p>Sub-task 1</p></statement>
  </task>
  <task workspace="...">
    <statement><p>Sub-task 2</p></statement>
  </task>
</exercise>

<exercise workspace="...">
  <statement>
    <p>Exercise 2 content</p>
  </statement>
</exercise>

<exercise workspace="...">
  <statement>
    <p>Exercise 3 content</p>
  </statement>
</exercise>
```

**Rules:**
- Each outer `\item` becomes an `<exercise>` element (at the worksheet level)
- The exercise content goes in `<statement><p>` ... `</p></statement>`
- **If the exercise has a nested `\begin{enumerate}`**: Convert each nested `\item` to a `<task>` with `<statement><p>` structure
- **If the exercise has NO nested enumerate**: Just use a single `<exercise><statement><p>` structure

### Step 6: Handle Workspace Attributes

**\vfill:**
- Appears at the end of enumerate items to provide blank space for student answers
- Convert to: `workspace="1in"` attribute on the `<exercise>` or `<task>` element
- Default workspace space: `1in`

**\vspace:**
- Appears as `\vspace{2cm}` or similar to specify custom spacing
- Convert to: `workspace="2cm"` attribute (use the exact dimension)

**Placement:**
```xml
<exercise workspace="1in">
  <statement><p>Exercise text</p></statement>
</exercise>

<task workspace="2cm">
  <statement><p>Task text</p></statement>
</task>
```

### Step 7: Math Mode Conversion

**Display Math ($$...$$):**
- LaTeX: `$$(f(\xvec))^2 = |A\xvec|^2$$`
- PreText: `<md>(f(\xvec))^2 = |A\xvec|^2</md>`
- Use `<md>` for display/block-level math

**Inline Math ($...$):**
- LaTeX: `$A\xvec$`
- PreText: `<m>A\xvec</m>`
- Use `<m>` for inline math

**Rules:**
- Copy the LaTeX math notation exactly as-is inside the tags
- Do NOT convert LaTeX macros (e.g., `\mattwo`, `\vvec`, `\sigma` are preserved)
- Math macros can be defined in docinfo or handled by the PreText system

### Step 8: Text Formatting Conversion

| LaTeX | PreText | Usage |
|-------|---------|-------|
| `{\bf text}` or `\textbf{text}` | `<strong>text</strong>` OR `<term>text</term>` | Key terminology → `<term>` |
| `` `text' `` (quotes) | `<q>text</q>` | Quoted/special terms |
| `\url{link}` | `<url href="link">link</url>` | Hyperlinks |
| `\hspace`, `\quad`, etc. | Remove or use context | Whitespace usually not needed |

**Special Cases:**
- The first `{\bf text}` in the document → becomes the `<title>` (Step 3)
- Other `{\bf text}` for key terminology → convert to `<term>`
- Emphasized course codes or abbreviations → use `<term>`

### Step 9: Inline Lists (itemize)

**LaTeX Structure:**
```latex
\begin{itemize}
    \item First point
    \item Second point
\end{itemize}
```

**PreText Structure:**
```xml
<ul>
  <li>First point</li>
  <li>Second point</li>
</ul>
```

**Rules:**
- LaTeX `itemize` → PreText `<ul>` (unordered list)
- Each `\item` → `<li>` element
- Preserve text content, converting math and formatting as needed

### Step 10: Handling Newlines and Page Breaks

- `\newpage` and `\vfill` at the end of content → Remove (use workspace attributes instead)
- Standard paragraph breaks → Separate `<p>` elements
- Multiple blank lines → Single separation between paragraphs in XML

## Example Conversion

### Before (LaTeX):

```latex
\item The first {\bf{singular value}} $\sigma_1$ is the maximum value of $f(\xvec)$
 over all unit vectors and an associated {\bf{right singular vector}} $\vvec_1$
 is a unit vector describing a direction in which this maximum occurs.
Use the diagram to find the first singular value $\sigma_1$ and an associated right singular vector $\vvec_1$.
    \vfill
```

### After (PreText):

```xml
<task workspace="1in">
  <statement>
    <p>The first <term>singular value</term> <m>\sigma_1</m> is the maximum value of <m>f(\xvec)</m>
 over all unit vectors and an associated <term>right singular vector</term> <m>\vvec_1</m>
 is a unit vector describing a direction in which this maximum occurs.
Use the diagram to find the first singular value <m>\sigma_1</m> and an associated right singular vector <m>\vvec_1</m>.</p>
  </statement>
</task>
```

## XML Declaration and Root Element

Every PreText worksheet must start with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<worksheet>
  ... content ...
</worksheet>
```

## Summary of Mapping

| LaTeX Element | PreText Element | Notes |
|---------------|-----------------|-------|
| tcolorbox intro + itemize | `<objectives>` | Goes at top of worksheet |
| Intro text before enumerate | `<introduction>` | Contains introductory content |
| Top-level enumerate items | `<exercise>` | Each becomes one exercise |
| Nested enumerate items | `<task>` | Inside an exercise with nested enums |
| `{\bf text}` (first) | `<title>` | Document title |
| `{\bf text}` (other) | `<term>` | Terminology/key concepts |
| `$...$` | `<m>...</m>` | Inline math |
| `$$...$$` | `<md>...</md>` | Display math |
| `\vfill` | `workspace="1in"` | On exercise/task element |
| `\vspace{Xcm}` | `workspace="Xcm"` | On exercise/task element |
| `\url{link}` | `<url href="link">link</url>` | Hyperlinks |
| `\item` in itemize | `<li>` in `<ul>` | Bullet lists |

## Verification

After conversion:
1. Ensure the `.ptx` file is well-formed XML
2. Check that all math is properly wrapped in `<m>` or `<md>`
3. Verify that all exercises and tasks have proper `<statement>` wrappers
4. Confirm workspace attributes are present for questions requiring space
5. Test with `pretext build course` to ensure no parsing errors
