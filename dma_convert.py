#!/usr/bin/env python3
"""
LaTeX worksheet to PreTeXt worksheet converter for DMA-style worksheets.
Usage: python dma_convert.py filename.tex
Output: filename.ptx (same directory as input)

Source conventions:
  - Two bold lines at top: first is a course label (ignored); second is the title.
  - If there is an outer enumerate, each \\item is an exercise.
    \\vs{N} / \\vspace{N} within an item separates tasks; each chunk gets
    workspace="Nin" (or workspace="N" when N already includes units).
  - If there is no enumerate, the body is split by \\vs / \\vspace into
    individual exercises, each with a <statement>.
"""

import sys
import re
from pathlib import Path
import xml.etree.ElementTree as ET


# ── Low-level helpers ─────────────────────────────────────────────────────────

def strip_preamble(tex):
    """Return document body: from \\begin{document} to first \\end{document}."""
    m_start = re.search(r'\\begin\{document\}', tex)
    if not m_start:
        return tex
    after_start = tex[m_start.end():]
    m_end = re.search(r'\\end\{document\}', after_start)
    if m_end:
        return after_start[:m_end.start()]
    return after_start


def find_env(text, env, start=0):
    """
    Find first \\begin{env}...\\end{env} at or after `start`, tracking nesting.
    Returns (begin_pos, end_pos, inner_text) or None.
    """
    begin_tag = f'\\begin{{{env}}}'
    end_tag   = f'\\end{{{env}}}'
    pos = text.find(begin_tag, start)
    if pos == -1:
        return None
    depth = 1
    i = pos + len(begin_tag)
    while i < len(text) and depth > 0:
        if text[i:].startswith(begin_tag):
            depth += 1
            i += len(begin_tag)
        elif text[i:].startswith(end_tag):
            depth -= 1
            if depth == 0:
                return (pos, i + len(end_tag), text[pos + len(begin_tag):i])
            i += len(end_tag)
        else:
            i += 1
    return None


def split_items(text):
    """
    Split enumerate/itemize inner content into top-level \\item chunks.
    Returns a list of strings (content after \\item, without the \\item itself).
    """
    items = []
    current = []
    depth = 0
    i = 0
    while i < len(text):
        if text[i:].startswith(r'\begin{enumerate}'):
            depth += 1
            current.append(r'\begin{enumerate}')
            i += len(r'\begin{enumerate}')
        elif text[i:].startswith(r'\begin{itemize}'):
            depth += 1
            current.append(r'\begin{itemize}')
            i += len(r'\begin{itemize}')
        elif text[i:].startswith(r'\end{enumerate}'):
            depth -= 1
            current.append(r'\end{enumerate}')
            i += len(r'\end{enumerate}')
        elif text[i:].startswith(r'\end{itemize}'):
            depth -= 1
            current.append(r'\end{itemize}')
            i += len(r'\end{itemize}')
        elif text[i:].startswith(r'\item') and depth == 0:
            chunk = ''.join(current).strip()
            if chunk:
                items.append(chunk)
            current = []
            i += len(r'\item')
            j = i
            while j < len(text) and text[j] in ' \t':
                j += 1
            if j < len(text) and text[j] == '[':
                end = text.find(']', j)
                if end != -1:
                    i = end + 1
        else:
            current.append(text[i])
            i += 1
    chunk = ''.join(current).strip()
    if chunk:
        items.append(chunk)
    return items


# ── Title extraction ──────────────────────────────────────────────────────────

_BF_RE = re.compile(
    r'\{\\bf\s*\{?([^{}]+?)\}?\}'  # {\bf text} or {\bf{text}}
    r'|\\textbf\{([^}]+)\}'        # \textbf{text}
)


def extract_second_bf(text):
    """
    Skip first {\\bf ...} / \\textbf{...}; use second as the worksheet title.
    Both occurrences are removed from the returned body text.
    Returns (title_or_None, cleaned_text).
    """
    matches = list(_BF_RE.finditer(text))
    if not matches:
        return None, text
    if len(matches) == 1:
        m = matches[0]
        title = (m.group(1) or m.group(2)).strip()
        return title, text[:m.start()] + text[m.end():]
    m1, m2 = matches[0], matches[1]
    title = (m2.group(1) or m2.group(2)).strip()
    result = text[:m1.start()] + text[m1.end():m2.start()] + text[m2.end():]
    return title, result


# ── Workspace splitting ───────────────────────────────────────────────────────

# Matches workspace-producing commands in priority order:
#   \vs{N}      → workspace="Nin"   (N is a bare number)
#   \vss{N}     → workspace="Nin"   (N is a bare number)
#   \vspace{N} / \vspace*{N}  → workspace="N"  (N may include units)
_WS_RE = re.compile(
    r'\\vs\{([0-9.]+)\}'        # group 1: \vs
    r'|\\vss\{([0-9.]+)\}'      # group 2: \vss
    r'|\\vspace\*?\{([^}]+)\}'  # group 3: \vspace / \vspace*
)


def split_by_workspace(text):
    """
    Split text at \\vs / \\vss / \\vspace commands.
    Returns [(chunk, workspace_or_None), ...].
    Each chunk is the text BEFORE the workspace command; the final
    element covers trailing text and always has workspace=None.
    """
    result = []
    last_end = 0
    for m in _WS_RE.finditer(text):
        chunk = text[last_end:m.start()]
        if m.group(1) is not None:
            ws = m.group(1).strip() + 'in'
        elif m.group(2) is not None:
            ws = m.group(2).strip() + 'in'
        else:
            ws = m.group(3).strip()
        result.append((chunk, ws))
        last_end = m.end()
    result.append((text[last_end:], None))
    return result


def _is_noise(text):
    """Return True if text is empty/whitespace after stripping LaTeX layout commands."""
    t = text
    for cmd in [r'\noindent', r'\bigskip', r'\medskip', r'\smallskip',
                r'\newpage', r'\vfill', r'\hfill', r'\\']:
        t = t.replace(cmd, '')
    t = re.sub(r'\\hspace\*?\{[^}]+\}', '', t)
    t = re.sub(r'\\input\s+\S+', '', t)
    return not t.strip()


# ── Text → XML conversion ─────────────────────────────────────────────────────

def _escape_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _escape_math(math):
    # PreTeXt uses \amp for alignment ampersands inside math
    return math.replace('&', r'\amp').replace('<', '&lt;').replace('>', '&gt;')


def convert_text(text):
    """
    Convert a LaTeX text fragment to an XML fragment string.
    Handles math, bold/italic formatting, images, URLs, and layout noise.
    """
    # Strip center environment markers (contents processed inline)
    text = re.sub(r'\\begin\{center\}', '', text)
    text = re.sub(r'\\end\{center\}', '', text)

    # 1. Protect display math $$ ... $$
    dmath = {}
    def save_dmath(m):
        k = f'\x00D{len(dmath)}\x00'
        dmath[k] = _escape_math(m.group(1))
        return k
    text = re.sub(r'\$\$(.+?)\$\$', save_dmath, text, flags=re.DOTALL)

    # 2. Protect inline math $ ... $
    imath = {}
    def save_imath(m):
        k = f'\x00I{len(imath)}\x00'
        imath[k] = _escape_math(m.group(1))
        return k
    text = re.sub(r'\$(.+?)\$', save_imath, text, flags=re.DOTALL)

    # 3. Escape XML specials in remaining plain text
    text = _escape_xml(text)

    # 4. \includegraphics[opts]{path} → <image source="path"/>
    text = re.sub(
        r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',
        r'<image source="\1"/>',
        text,
    )

    # 5. \url{...} → <url href="https://...">...</url>
    text = re.sub(r'\\url\{([^}]+)\}', r'<url href="https://\1">\1</url>', text)

    # 6. {\bf text} / \textbf{text} → <term>text</term>
    text = re.sub(
        r'\{\\bf\s*\{?([^{}]+?)\}?\}|\\textbf\{([^}]+)\}',
        lambda m: f'<term>{(m.group(1) or m.group(2)).strip()}</term>',
        text,
    )

    # 7. \emph{text} / {\em text} → <em>text</em>
    text = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', text)
    text = re.sub(r'\{\\em\s+([^}]+)\}', r'<em>\1</em>', text)

    # 8. Remove LaTeX layout / noise commands
    for cmd in [r'\noindent', r'\bigskip', r'\medskip', r'\smallskip',
                r'\newpage', r'\vfill', r'\hfill', r'\\']:
        text = text.replace(cmd, '')
    text = re.sub(r'\\hspace\*?\{[^}]+\}', '', text)
    text = re.sub(r'\\input\s+\S+', '', text)
    # Remove any residual workspace commands not caught by split_by_workspace
    text = re.sub(r'\\vspace\*?\{[^}]+\}', '', text)
    text = re.sub(r'\\vss\{[^}]+\}', '', text)
    text = re.sub(r'\\vs\{[^}]+\}', '', text)

    # 9. Restore math placeholders
    for k, v in dmath.items():
        text = text.replace(k, f'<md>{v}</md>')
    for k, v in imath.items():
        text = text.replace(k, f'<m>{v}</m>')

    return text


def _make_paras(text, indent):
    """Split converted XML text into <p> elements on blank lines."""
    xml = convert_text(text)
    chunks = [c.strip() for c in re.split(r'\n\s*\n', xml)]
    return [f'{indent}<p>{c}</p>' for c in chunks if c]


def text_to_xml(text, indent):
    """
    Convert raw LaTeX text (possibly containing \\begin{itemize}) to XML lines.
    Produces <p> for prose and <ul> for itemize blocks.
    """
    result = []
    remaining = text
    while remaining.strip():
        env = find_env(remaining, 'itemize')
        if env is None:
            result.extend(_make_paras(remaining, indent))
            break
        begin_pos, end_pos, inner = env
        before = remaining[:begin_pos]
        if before.strip():
            result.extend(_make_paras(before, indent))
        ul_lines = [f'{indent}<ul>']
        for item in split_items(inner):
            content = convert_text(item.strip())
            ul_lines.append(f'{indent}  <li><p>{content.strip()}</p></li>')
        ul_lines.append(f'{indent}</ul>')
        result.append('\n'.join(ul_lines))
        remaining = remaining[end_pos:]
    return '\n'.join(result)


# ── PreTeXt element builders ──────────────────────────────────────────────────

def build_exercise_from_item(item_text):
    """
    Build an <exercise> from one outer enumerate item.

    Split the item by \\vs / \\vspace commands to get workspace-delimited chunks.
    - Single chunk (one or zero separators, no significant trailing text):
        <exercise workspace="..."><statement>...</statement></exercise>
    - Multiple chunks:
        <exercise><task workspace="..."><statement>...</statement></task>...</exercise>

    The workspace attribute is derived from the separator that FOLLOWS each chunk.
    """
    chunks = split_by_workspace(item_text)

    # "Simple" if there is at most one workspace separator and the trailing
    # text (after it) is pure noise/whitespace.
    is_simple = (
        len(chunks) == 1  # no separators at all
        or (len(chunks) == 2 and _is_noise(chunks[1][0]))
    )

    if is_simple:
        text, workspace = chunks[0]
        workspace = workspace or '1in'
        ws_attr = f' workspace="{workspace}"'
        content = text_to_xml(text.strip(), indent='      ')
        return '\n'.join([
            f'  <exercise{ws_attr}>',
            '    <statement>',
            content,
            '    </statement>',
            '  </exercise>',
        ])

    # Multi-task exercise
    lines = ['  <exercise>']
    for text, workspace in chunks:
        if _is_noise(text) and workspace is None:
            continue  # skip empty trailing segment
        workspace = workspace or '1in'
        ws_attr = f' workspace="{workspace}"'
        task_content = text_to_xml(text.strip(), indent='        ')
        lines += [
            f'    <task{ws_attr}>',
            '      <statement>',
            task_content,
            '      </statement>',
            '    </task>',
        ]
    lines.append('  </exercise>')
    return '\n'.join(lines)


def build_exercise_simple(chunk_text, workspace):
    """Build a standalone <exercise> (no-enumerate mode) with <statement>."""
    workspace = workspace or '1in'
    ws_attr = f' workspace="{workspace}"'
    content = text_to_xml(chunk_text.strip(), indent='      ')
    return '\n'.join([
        f'  <exercise{ws_attr}>',
        '    <statement>',
        content,
        '    </statement>',
        '  </exercise>',
    ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        print('Usage: python dma_convert.py filename.tex')
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f'Error: {input_path} not found')
        sys.exit(1)

    tex = input_path.read_text(encoding='utf-8')
    body = strip_preamble(tex)

    # Title comes from the SECOND {\bf ...} (first is the course label)
    title, body = extract_second_bf(body)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<worksheet>']

    if title:
        title_xml = convert_text(title)
        parts.append(f'  <title>{title_xml.strip()}</title>')

    outer = find_env(body, 'enumerate')

    if outer is None:
        # No enumerate: each \vs / \vspace-separated chunk is one exercise
        chunks = split_by_workspace(body)
        for chunk_text, workspace in chunks:
            if _is_noise(chunk_text):
                continue  # skip noise-only chunks (with or without workspace)
            parts.append('')
            parts.append(build_exercise_simple(chunk_text, workspace))
    else:
        # Enumerate: each \item is an exercise; \vs within items makes tasks
        outer_start, outer_end, outer_inner = outer

        intro_raw = body[:outer_start].strip()
        if intro_raw and not _is_noise(intro_raw):
            parts.append('  <introduction>')
            parts.append(text_to_xml(intro_raw, indent='    '))
            parts.append('  </introduction>')

        for item in split_items(outer_inner):
            parts.append('')
            parts.append(build_exercise_from_item(item))

    parts += ['', '</worksheet>', '']
    output = '\n'.join(parts)

    try:
        ET.fromstring(output)
    except ET.ParseError as e:
        print(f'Warning: generated XML failed validation: {e}')

    output_path = input_path.with_suffix('.ptx')
    output_path.write_text(output, encoding='utf-8')
    print(f'Written: {output_path}')


if __name__ == '__main__':
    main()
