# LaTeX to PreTeXt Worksheet Conversion Instructions

## Overview
This document describes how to convert a LaTeX worksheet document into a PreTeXt worksheet (`*.ptx`) file. These instructions are designed to be followed by a coding agent (like GitHub Copilot) to automate the conversion process across similar PreTeXt course projects.

## Task Summary
Convert a LaTeX document (typically with a `.tex` extension) into a PreTeXt XML worksheet. The LaTeX document should contain:
- A title (typically in bold at the beginning)
- Optional introductory text before the main content
- An `enumerate` environment containing exercise items
- `\vs{X}` commands indicating vertical workspace spacing

## Conversion Rules

### 1. Root Element
Wrap all converted content in a `<worksheet>` element.

### 2. Title
- The first bold text in the LaTeX document becomes the `<title>` of the worksheet
- Extract the text from `{\bf ...}` or `\textbf{...}` patterns

### 3. Structure
- Each item in the LaTeX `enumerate` environment becomes an `<exercise>` element
- If an exercise contains multiple sub-questions, organize them using `<task>` elements within the exercise
- If an exercise has introductory text before the questions, place it in an `<introduction>` element inside the exercise

### 4. Workspace Spacing
- When you encounter `\vs{X}` or `\vspace{X in}` in the LaTeX document, add a `workspace="Xin"` attribute to the preceding XML element (task or exercise)
- The workspace attribute specifies how much blank space should appear in the rendered worksheet
- Examples:
  - `\vs{1}` → `workspace="1in"`
  - `\vs{1.5}` → `workspace="1.5in"`
  - `\vs{0.75}` → `workspace="0.75in"`

### 5. Math Content
- Inline math (LaTeX `$...$` or `\(...\)`) becomes `<m>...</m>` in PreTeXt
- Display math (LaTeX `$$...$$` or `\[...\]` or `align*`, etc.) becomes `<md>...</md>` in PreTeXt
- Preserve all LaTeX commands (like `\threevec`, `\twovec`, `\col`, `\rank`, etc.) as-is
- Replace `&` with `&amp;` in math environments

### 6. Text Formatting
- `{\em ...}` or `\emph{...}` → `<em>...</em>`
- `{\bf ...}` or `\textbf{...}` → `<b>...</b>`
- Regular text → `<p>...</p>` inside appropriate elements

### 7. Ignore LaTeX Preamble
Do not include any content from the LaTeX preamble. Start conversion from:
- `\begin{document}` or
- The first content after the preamble (like the title)

Ignore:
- `\documentclass` declarations
- `\usepackage` commands
- `\newcommand` definitions
- Page setup commands (`\pagestyle`, `\setlength`, etc.)

## Output File Location
- Place the converted file in `source/activities/` directory
- Use the same filename as the original LaTeX file, but with `.ptx` extension
- Example: `source/latex/26-review.tex` → `source/activities/26-review.ptx`

## Input Specification
When performing this conversion, you will need:
- **Input file**: The path to the LaTeX file to be converted (e.g., `source/latex/26-review.tex`)
- The conversion target directory is always `source/activities/`

## Example

### Input LaTeX (excerpt)
```latex
\noindent
{\bf Mathematics 204} \\ 
{\bf Review}

\bigskip
\begin{enumerate}
\item Suppose that $A = \begin{bmatrix} ... \end{bmatrix}$
  
  Write the solution set of the equation $A\xvec = \bvec$.
  
  \vs{1.5}
  Find a basis for $\col(A)$.
  
  \vs{1}
\item For what values of $k$ is the matrix ... invertible?
  
  \vs{1.5}
\end{enumerate}
```

### Output PreTeXt
```xml
<?xml version="1.0" encoding="UTF-8"?>

<worksheet>
  <title>Mathematics 204 Review</title>

  <exercise>
    <introduction>
      <p>Suppose that <m>A = \begin{bmatrix} ... \end{bmatrix}</m></p>
    </introduction>
    <task workspace="1.5in">
      <p>Write the solution set of the equation <m>A\xvec = \bvec</m>.</p>
    </task>
    <task workspace="1in">
      <p>Find a basis for <m>\col(A)</m>.</p>
    </task>
  </exercise>

  <exercise workspace="1.5in">
    <statement>
      <p>For what values of <m>k</m> is the matrix ... invertible?</p>
    </statement>
  </exercise>

</worksheet>
```

## Instructions for the Coding Agent

When asked to convert a LaTeX worksheet to PreTeXt:

1. **Read the LaTeX file** referenced in the user's request
2. **Skip the preamble** - ignore everything before `\begin{document}` or the first content
3. **Extract the title** - find the first bold text and use it for the `<title>` element
4. **Identify the enumerate environment** - find the `\begin{enumerate}...\end{enumerate}` block
5. **For each enumerate item**:
   - Check if it contains multiple logical questions (indicated by multiple `\vs{}` commands)
   - If multiple questions: create an `<exercise>` containing `<task>` elements for each question
   - If single question: create an `<exercise>` with `<statement>` element
   - Extract any introductory content (before the first question) into an `<introduction>` element
6. **Handle workspace spacing** - when you encounter `\vs{X}`, add `workspace="Xin"` to the preceding element
7. **Convert math** - change inline math to `<m>` and display math to `<md>`; preserve LaTeX commands
8. **Fix XML special characters** - replace `&` with `&amp;` in math content
9. **Create the output file** in `source/activities/` with the same base filename but `.ptx` extension

## Example Usage Request

A colleague could request this conversion with:
> "I want you to convert the latex file `source/latex/my-worksheet.tex` into a pretext worksheet, following the same process as was done for 26-review.tex. You can read the instructions in LATEX_TO_PRETEXT_CONVERSION.md for guidance."

Or more simply:
> "Convert `source/latex/my-worksheet.tex` to a PreTeXt worksheet using the conversion instructions in LATEX_TO_PRETEXT_CONVERSION.md"
