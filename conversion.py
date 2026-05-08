#!/usr/bin/env python3
"""
LaTeX to PreTeXt Worksheet Conversion Script

Converts LaTeX worksheet documents to PreTeXt (*.ptx) format.
Usage: python conversion.py filename.tex
"""

import sys
import re
from pathlib import Path
from lxml import etree


def read_latex_file(filename):
    """Read and return the contents of a LaTeX file."""
    with open(filename, 'r') as f:
        return f.read()


def extract_document_content(latex_content):
    """Extract content after \begin{document}."""
    match = re.search(r'\\begin\{document\}(.*)', latex_content, re.DOTALL)
    if match:
        content = match.group(1)
        # Remove everything after \end{document}
        content = re.sub(r'\\end\{document\}.*', '', content, flags=re.DOTALL)
        return content
    return latex_content


def extract_title(content):
    """Extract title from bold text at the beginning."""
    # Match {\bf ...} or \textbf{...}
    match = re.search(r'\\begin\{document\}.*?(?:\{\\bf(.+?)\}|\\textbf\{(.+?)\})', content, re.DOTALL)
    if match:
        title_text = match.group(1) or match.group(2)
        # Clean up the title - remove newlines and extra spaces
        title_text = re.sub(r'\s+', ' ', title_text).strip()
        # Continue looking for additional bold text (like "Review")
        remaining = content[match.end():]
        additional_match = re.search(r'\\\\\s*\{\\bf(.+?)\}', remaining)
        if additional_match:
            additional = additional_match.group(1).strip()
            title_text += ' ' + additional
        return title_text
    return "Worksheet"


def convert_math(text):
    """Convert LaTeX math notation to PreTeXt format and return with markers."""
    # Replace & with \amp in math contexts
    # We'll handle this during math extraction
    
    # Find inline math and wrap in <m> tags
    def replace_inline_math(match):
        math_content = match.group(1)
        math_content = math_content.replace('&', '\\amp')
        return f'<m>{math_content}</m>'
    
    # Handle $...$ math
    text = re.sub(r'\$([^$]+)\$', replace_inline_math, text)
    # Handle \(...\) math  
    text = re.sub(r'\\\(([^\)]+)\\\)', replace_inline_math, text)
    
    return text


def extract_enumerate_items(content):
    """Extract items from the enumerate environment."""
    # Find the enumerate block
    match = re.search(r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}', content, re.DOTALL)
    if not match:
        return [], content
    
    enum_content = match.group(1)
    # Split by \item
    items = re.split(r'\n\s*\\item\s+', enum_content)
    # Remove the first empty element
    if items and not items[0].strip():
        items = items[1:]
    
    return items, content[match.end():]  # Return items and remaining content


def split_item_into_tasks(item_text):
    """Split an item into introduction, questions (tasks), and workspace info."""
    # Clean comments first
    lines = item_text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove everything after % (but not \% which is escaped)
        line = re.sub(r'(?<!\\)%.*', '', line)
        cleaned_lines.append(line)
    item_text = '\n'.join(cleaned_lines)
    
    # Split by \vs{} commands to identify separate questions
    parts = re.split(r'(\\\s*vs\{[0-9.]+\})', item_text)
    
    questions = []
    current_q = ""
    
    for i, part in enumerate(parts):
        if part.strip().startswith(r'\vs'):
            # Extract workspace value
            ws_match = re.search(r'\\vs\{([0-9.]+)\}', part)
            if ws_match:
                ws_value = ws_match.group(1)
                if current_q.strip():
                    questions.append((current_q.strip(), f"{ws_value}in"))
                    current_q = ""
        else:
            current_q += part
    
    # Add final question if exists and not empty
    if current_q.strip():
        questions.append((current_q.strip(), None))
    
    # First part before any \vs is the introduction
    intro = None
    if questions:
        first_q, first_ws = questions[0]
        # Check if this looks like introductory text (no question mark usually)
        if not re.search(r'[?!]', first_q) and len(questions) > 1:
            intro = first_q
            questions = questions[1:]
    
    # Filter out empty questions
    questions = [(q, ws) for q, ws in questions if q.strip()]
    
    return intro, questions


def process_text_formatting(text):
    """Convert LaTeX text formatting to PreTeXt."""
    # Convert {\em ...} to <em>...</em>
    text = re.sub(r'\{\\em\s+([^}]+)\}', r'<em>\1</em>', text)
    # Convert \emph{...} to <em>...</em>
    text = re.sub(r'\\emph\{([^}]+)\}', r'<em>\1</em>', text)
    # Convert {\bf ...} to <b>...</b>
    text = re.sub(r'\{\\bf\s+([^}]+)\}', r'<b>\1</b>', text)
    # Convert \textbf{...} to <b>...</b>
    text = re.sub(r'\\textbf\{([^}]+)\}', r'<b>\1</b>', text)
    
    # Remove \includegraphics commands for now (just note them)
    text = re.sub(r'\\includegraphics\[.*?\]\{([^}]+)\}', r'[IMAGE: \1]', text)
    
    return text


def extract_display_math(text):
    """Extract display math blocks and replace with placeholders."""
    display_math = []
    
    # Handle $$...$$ math
    def replace_display(match):
        math_content = match.group(1)
        math_content = math_content.replace('&', '\\amp')
        placeholder = f"__DISPLAY_MATH_{len(display_math)}__"
        display_math.append(math_content)
        return placeholder
    
    text = re.sub(r'\$\$(.+?)\$\$', replace_display, text, flags=re.DOTALL)
    # Handle \[...\] math
    text = re.sub(r'\\\[(.+?)\\\]', replace_display, text, flags=re.DOTALL)
    # Handle align*, equation*, etc.
    text = re.sub(r'\\begin\{(align\*|equation\*|multline\*|gather\*)\}(.+?)\\end\{\1\}', 
                  replace_display, text, flags=re.DOTALL)
    # Handle simple \begin{bmatrix}...\end{bmatrix}
    text = re.sub(r'(\s)\\\[(.+?)\\\]', replace_display, text, flags=re.DOTALL)
    
    return text, display_math


def restore_display_math(text, display_math):
    """Restore display math from placeholders."""
    for i, math_content in enumerate(display_math):
        placeholder = f"__DISPLAY_MATH_{i}__"
        text = text.replace(placeholder, f"<md>{math_content}</md>")
    return text


def clean_text(text):
    """Clean up LaTeX text."""
    # Remove LaTeX comments (everything after % on each line)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove everything after % (but not \% which is escaped)
        line = re.sub(r'(?<!\\)%.*', '', line)
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    
    # Remove \vs{} commands
    text = re.sub(r'\\\s*vs\{[0-9.]+\}', '', text)
    # Replace \hspace with ~~~
    text = re.sub(r'\\hspace\*?\{[^}]*\}', '~~~', text)
    # Remove \newpage
    text = re.sub(r'\\newpage', '', text)
    # Remove \bigskip, \smallskip, etc.
    text = re.sub(r'\\(big|small|medium)?skip', '', text)
    # Remove \noindent
    text = re.sub(r'\\noindent', '', text)
    # Remove blank lines
    text = re.sub(r'\n\s*\n+', '\n', text)
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    return text.strip()


def text_to_xml_content(text):
    """Convert text to XML content, wrapping in paragraph tags if needed."""
    text = text.strip()
    if not text:
        return None
    
    text = clean_text(text)
    
    # Extract display math and replace with placeholders
    display_math = []
    
    # Handle $$...$$ math
    def replace_display(match):
        math_content = match.group(1)
        math_content = math_content.replace('&', '\\amp')
        placeholder = f"__DISPLAY_MATH_{len(display_math)}__"
        display_math.append(math_content)
        return placeholder
    
    text = re.sub(r'\$\$(.+?)\$\$', replace_display, text, flags=re.DOTALL)
    
    text = process_text_formatting(text)
    text = convert_math(text)
    
    # Restore display math
    for i, math_content in enumerate(display_math):
        placeholder = f"__DISPLAY_MATH_{i}__"
        text = text.replace(placeholder, f"<md>{math_content}</md>")
    
    # If text doesn't start with a tag, wrap in <p>
    if text and not text.startswith('<'):
        text = f'<p>{text}</p>'
    
    return text


def create_exercise_element(intro, questions):
    """Create an exercise element with introduction and tasks/statement."""
    exercise = etree.Element('exercise')
    
    # Determine if we should use task or statement
    use_statement = len(questions) == 1
    
    # Set workspace on exercise if using statement
    if use_statement and questions[0][1]:
        exercise.set('workspace', questions[0][1])
    
    # Add introduction
    if intro:
        intro_elem = etree.SubElement(exercise, 'introduction')
        intro_text = text_to_xml_content(intro)
        if intro_text:
            # Parse XML content
            intro_elem.append(etree.fromstring(f'<root>{intro_text}</root>')[0])
    
    # Add tasks or statement
    for i, (question, workspace) in enumerate(questions):
        if use_statement:
            elem = etree.SubElement(exercise, 'statement')
            # Workspace is already set on exercise
        else:
            elem = etree.SubElement(exercise, 'task')
            if workspace:
                elem.set('workspace', workspace)
        
        question_text = text_to_xml_content(question)
        if question_text:
            # Parse and add XML content
            parsed = etree.fromstring(f'<root>{question_text}</root>')
            for child in parsed:
                elem.append(child)
        elif not use_statement:
            # Remove empty task elements for multi-task exercises
            exercise.remove(elem)
    
    return exercise


def extract_text_before_tcolorbox(content):
    """Extract text before tcolorbox and the tcolorbox content."""
    match = re.search(r'\\begin\{tcolorbox\}(.*?)\\end\{tcolorbox\}', content, re.DOTALL)
    if not match:
        return content, None
    
    before = content[:match.start()]
    tcolorbox_content = match.group(1)
    
    return before, tcolorbox_content


def parse_tcolorbox(tcolorbox_content):
    """Parse tcolorbox content into introduction and list items."""
    # Extract initial text (intro)
    intro_match = re.match(r'\s*(.+?)(?=\\begin\{itemize\}|\\begin\{enumerate\})', 
                           tcolorbox_content, re.DOTALL)
    intro_text = intro_match.group(1).strip() if intro_match else ""
    
    # Extract list items
    itemize_match = re.search(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', tcolorbox_content, re.DOTALL)
    items = []
    if itemize_match:
        items_content = itemize_match.group(1)
        items = re.findall(r'\\item\s+(.+?)(?=\\item|\Z)', items_content, re.DOTALL)
    
    return intro_text, items


def create_objectives_element(tcolorbox_content):
    """Create an objectives element from tcolorbox content."""
    objectives = etree.Element('objectives')
    
    intro_text, items = parse_tcolorbox(tcolorbox_content)
    
    # Add introduction
    if intro_text:
        intro_elem = etree.SubElement(objectives, 'introduction')
        intro_content = text_to_xml_content(intro_text)
        if intro_content:
            parsed = etree.fromstring(f'<root>{intro_content}</root>')
            for child in parsed:
                intro_elem.append(child)
    
    # Add ul with li items
    if items:
        ul = etree.SubElement(objectives, 'ul')
        for item in items:
            li = etree.SubElement(ul, 'li')
            item_text = text_to_xml_content(item)
            if item_text:
                parsed = etree.fromstring(f'<root>{item_text}</root>')
                for child in parsed:
                    li.append(child)
    
    return objectives


def convert_latex_to_pretext(latex_filename):
    """Main conversion function."""
    # Read LaTeX file
    latex_content = read_latex_file(latex_filename)
    
    # Extract document content
    doc_content = extract_document_content(latex_content)
    
    # Extract title
    title_text = extract_title(latex_content)
    
    # Extract tcolorbox first (if it exists anywhere), and remove it from content
    tcolorbox_content = None
    match = re.search(r'\\begin\{tcolorbox\}(.*?)\\end\{tcolorbox\}', doc_content, re.DOTALL)
    if match:
        tcolorbox_content = match.group(1)
        # Remove tcolorbox from document content
        doc_content = doc_content[:match.start()] + doc_content[match.end():]
    
    # Extract enumerate items from cleaned content
    items, remaining = extract_enumerate_items(doc_content)
    
    # Create root element
    root = etree.Element('worksheet')
    
    # Add title
    title_elem = etree.SubElement(root, 'title')
    title_elem.text = title_text
    
    # Add objectives if tcolorbox exists
    if tcolorbox_content:
        objectives_elem = create_objectives_element(tcolorbox_content)
        root.append(objectives_elem)
    
    # Add exercises
    for item in items:
        intro, questions = split_item_into_tasks(item)
        if questions:
            exercise = create_exercise_element(intro, questions)
            root.append(exercise)
    
    return root


def format_xml(element):
    """Format XML with proper indentation."""
    def indent(elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    indent(element)


def main():
    if len(sys.argv) != 2:
        print("Usage: python conversion.py filename.tex")
        sys.exit(1)
    
    latex_file = sys.argv[1]
    
    if not Path(latex_file).exists():
        print(f"Error: File '{latex_file}' not found")
        sys.exit(1)
    
    # Convert filename
    ptx_file = Path(latex_file).with_suffix('.ptx')
    
    try:
        # Perform conversion
        root = convert_latex_to_pretext(latex_file)
        
        # Format and write
        format_xml(root)
        tree = etree.ElementTree(root)
        tree.write(str(ptx_file), encoding='UTF-8', xml_declaration=True, pretty_print=True)
        
        print(f"Successfully converted '{latex_file}' to '{ptx_file}'")
    
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
