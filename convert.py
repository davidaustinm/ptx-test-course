#!/usr/bin/env python3
"""
LaTeX to PreText Worksheet Converter

Converts LaTeX worksheet source files to PreText worksheet format.
Usage: python convert.py filename.tex
Output: filename.ptx
"""

import sys
import re
from pathlib import Path
from lxml import etree


class LatexToPretext:
    def __init__(self, tex_content):
        self.tex_content = tex_content
        self.root = None
        
    def extract_content_after_begin_document(self):
        """Skip preamble and extract content after \\begin{document}"""
        match = re.search(r'\\begin\{document\}(.*)', self.tex_content, re.DOTALL)
        if match:
            return match.group(1)
        return self.tex_content
    
    def extract_tcolorbox(self, content):
        """Extract tcolorbox content and return (objectives_intro, objectives_items, remaining_content)"""
        # Find tcolorbox block
        match = re.search(r'\\begin\{tcolorbox\}(.*?)\\end\{tcolorbox\}', content, re.DOTALL)
        if not match:
            return None, None, content
        
        tcolorbox_content = match.group(1)
        remaining = content[:match.start()] + content[match.end():]
        
        # Split intro text from itemize list
        itemize_match = re.search(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', tcolorbox_content, re.DOTALL)
        if itemize_match:
            intro_text = tcolorbox_content[:itemize_match.start()].strip()
            items_text = itemize_match.group(1)
            
            # Extract items
            items = re.findall(r'\\item\s+(.*?)(?=\\item|\Z)', items_text, re.DOTALL)
            items = [item.strip() for item in items]
            
            return intro_text, items, remaining
        
        return tcolorbox_content.strip(), [], remaining
    
    def extract_first_bold(self, content):
        """Extract first bold text (for title) and return (title, content_with_first_bold_removed)"""
        # Look for {\bf text} or \textbf{text}
        match = re.search(r'(?:\\textbf\{([^}]+)\}|\{\\bf\s*([^}]+)\})', content)
        if match:
            title = match.group(1) or match.group(2)
            # Replace the first bold occurrence with empty string to remove it from document
            content_after = content[:match.start()] + content[match.end():]
            return title, content_after
        return None, content
    
    def extract_intro_before_enumerate(self, content):
        """Extract introductory text before the outer enumerate"""
        match = re.search(r'^(.*?)\\begin\{enumerate\}', content, re.DOTALL)
        if match:
            intro = match.group(1).strip()
            return intro
        return ""
    
    def get_enumerate_content(self, content):
        """Extract the content of the outer enumerate"""
        # Find the outermost enumerate block by manual depth tracking
        start = content.find('\\begin{enumerate}')
        if start == -1:
            return ""
        
        # Count depth to find matching \end{enumerate}
        i = start + 18  # len('\\begin{enumerate}')
        depth = 1
        
        while i < len(content) and depth > 0:
            if content[i:].startswith('\\begin{enumerate}'):
                depth += 1
                i += 18
            elif content[i:].startswith('\\end{enumerate}'):
                depth -= 1
                if depth == 0:
                    return content[start + 18:i]
                i += 16
            else:
                i += 1
        
        return ""
    
    def extract_enumerate_items(self, enum_content):
        """Extract top-level items from enumerate, handling nested enumerates"""
        items = []
        i = 0
        current_item = ""
        depth = 0
        
        while i < len(enum_content):
            if enum_content[i:].startswith('\\item'):
                if current_item.strip() or not items:
                    if current_item.strip():
                        items.append(current_item)
                    current_item = ""
                i += 5  # skip \item
                # Skip whitespace after \item
                while i < len(enum_content) and enum_content[i] in ' \t\n':
                    i += 1
            elif enum_content[i:].startswith('\\begin{enumerate}'):
                depth += 1
                current_item += enum_content[i:i+18]
                i += 18
            elif enum_content[i:].startswith('\\end{enumerate}'):
                depth -= 1
                current_item += enum_content[i:i+16]
                i += 16
            else:
                current_item += enum_content[i]
                i += 1
        
        if current_item.strip():
            items.append(current_item)
        
        return items
    
    def has_nested_enumerate(self, item_content):
        """Check if item has nested enumerate"""
        return '\\begin{enumerate}' in item_content
    
    def extract_nested_items(self, item_content):
        """Extract nested enumerate items"""
        match = re.search(r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}', item_content, re.DOTALL)
        if match:
            nested_content = match.group(1)
            items = re.findall(r'\\item\s+(.*?)(?=\\item|\Z)', nested_content, re.DOTALL)
            return [item.strip() for item in items]
        return []
    
    def get_item_prefix(self, item_content):
        """Get content before any nested enumerate"""
        match = re.search(r'^(.*?)(?:\\begin\{enumerate\}|\Z)', item_content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return item_content.strip()
    
    def check_vfill(self, text):
        """Check if text ends with \\vfill"""
        return text.rstrip().endswith('\\vfill')
    
    def check_vspace(self, text):
        """Extract vspace dimension if present"""
        match = re.search(r'\\vspace\{([^}]+)\}', text)
        if match:
            return match.group(1)
        return None
    
    def clean_text(self, text):
        """Remove LaTeX formatting artifacts"""
        # Remove \vfill, \vspace, \newpage, \noindent, \bigskip
        text = re.sub(r'\\vfill', '', text)
        text = re.sub(r'\\vspace\{[^}]+\}', '', text)
        text = re.sub(r'\\newpage', '', text)
        text = re.sub(r'\\noindent', '', text)
        text = re.sub(r'\\bigskip', '', text)
        # Remove trailing whitespace
        text = text.strip()
        return text
    
    def convert_math_and_formatting(self, text):
        """Convert LaTeX math and formatting to PreText"""
        # Protect display math by replacing $$ with markers
        display_math_pattern = re.compile(r'\$\$([^$]+?)\$\$', re.DOTALL)
        display_matches = list(display_math_pattern.finditer(text))
        display_placeholders = {}
        for i, match in enumerate(display_matches):
            placeholder = f"__DISPLAY_MATH_{i}__"
            display_placeholders[placeholder] = match.group(1)
            text = text.replace(match.group(0), placeholder)
        
        # Protect inline math by replacing $ with markers
        inline_math_pattern = re.compile(r'\$([^$]+?)\$')
        inline_matches = list(inline_math_pattern.finditer(text))
        inline_placeholders = {}
        for i, match in enumerate(inline_matches):
            placeholder = f"__INLINE_MATH_{i}__"
            inline_placeholders[placeholder] = match.group(1)
            text = text.replace(match.group(0), placeholder)
        
        # Convert text formatting
        # {\bf text} or \textbf{text} to <term>text</term>
        text = re.sub(r'(?:\\textbf\{([^}]+)\}|\{\\bf\s*([^}]+)\})', 
                     lambda m: f'<term>{m.group(1) or m.group(2)}</term>', text)
        
        # \url{link} to <url href="link">link</url>
        text = re.sub(r'\\url\{([^}]+)\}', r'<url href="\1">\1</url>', text)
        
        # Replace placeholders with XML tags
        for placeholder, math_content in display_placeholders.items():
            text = text.replace(placeholder, f'<md>{math_content}</md>')
        
        for placeholder, math_content in inline_placeholders.items():
            text = text.replace(placeholder, f'<m>{math_content}</m>')
        
        return text
    
    def text_to_element(self, text, preserve_inline_xml=False):
        """Convert text to element content, potentially containing mixed text and XML"""
        if not text or not text.strip():
            return None
        
        text = self.convert_math_and_formatting(text)
        text = self.clean_text(text)
        
        # Try to parse as mixed content
        try:
            # Wrap in temp element if needed to parse mixed content
            wrapped = f"<temp>{text}</temp>"
            elem = etree.fromstring(wrapped)
            # Extract children and text
            result = []
            if elem.text:
                result.append(elem.text)
            for child in elem:
                result.append(child)
                if child.tail:
                    result.append(child.tail)
            return result if result else None
        except:
            # If parsing fails, return as plain text
            return text
    
    def build_objectives(self, intro_text, items):
        """Build objectives element"""
        objectives = etree.Element('objectives')
        
        if intro_text:
            introduction = etree.SubElement(objectives, 'introduction')
            text_content = self.text_to_element(intro_text)
            p = etree.SubElement(introduction, 'p')
            if isinstance(text_content, list):
                if text_content and isinstance(text_content[0], str):
                    p.text = text_content[0]
                for elem in text_content[1:]:
                    if isinstance(elem, str):
                        if len(p) > 0:
                            p[-1].tail = (p[-1].tail or "") + elem
                        else:
                            p.text = (p.text or "") + elem
                    else:
                        p.append(elem)
            else:
                p.text = str(text_content) if text_content else ""
        
        if items:
            ul = etree.SubElement(objectives, 'ul')
            for item_text in items:
                li = etree.SubElement(ul, 'li')
                text_content = self.text_to_element(item_text)
                if isinstance(text_content, list):
                    if text_content and isinstance(text_content[0], str):
                        li.text = text_content[0]
                    for elem in text_content[1:]:
                        if isinstance(elem, str):
                            if len(li) > 0:
                                li[-1].tail = (li[-1].tail or "") + elem
                            else:
                                li.text = (li.text or "") + elem
                        else:
                            li.append(elem)
                else:
                    li.text = str(text_content) if text_content else ""
        
        return objectives
    
    def build_introduction(self, intro_text):
        """Build introduction element"""
        if not intro_text or not intro_text.strip():
            return None
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', intro_text) if p.strip()]
        
        if not paragraphs:
            return None
        
        introduction = etree.Element('introduction')
        
        for para_text in paragraphs:
            p = etree.SubElement(introduction, 'p')
            text_content = self.text_to_element(para_text)
            if isinstance(text_content, list):
                if text_content and isinstance(text_content[0], str):
                    p.text = text_content[0]
                for elem in text_content[1:]:
                    if isinstance(elem, str):
                        if len(p) > 0:
                            p[-1].tail = (p[-1].tail or "") + elem
                        else:
                            p.text = (p.text or "") + elem
                    else:
                        p.append(elem)
            else:
                p.text = str(text_content) if text_content else ""
        
        return introduction
    
    def build_exercise_or_tasks(self, item_content):
        """Build exercise with optional tasks"""
        exercise = etree.Element('exercise')
        
        # Determine workspace
        workspace = None
        if self.check_vfill(item_content):
            workspace = "1in"
        else:
            vspace = self.check_vspace(item_content)
            if vspace:
                workspace = vspace
        
        if workspace:
            exercise.set('workspace', workspace)
        
        # Check if has nested enumerate
        if self.has_nested_enumerate(item_content):
            # Item prefix becomes the statement
            prefix = self.get_item_prefix(item_content)
            if prefix:
                statement = etree.SubElement(exercise, 'statement')
                p = etree.SubElement(statement, 'p')
                text_content = self.text_to_element(prefix)
                if isinstance(text_content, list):
                    if text_content and isinstance(text_content[0], str):
                        p.text = text_content[0]
                    for elem in text_content[1:]:
                        if isinstance(elem, str):
                            if len(p) > 0:
                                p[-1].tail = (p[-1].tail or "") + elem
                            else:
                                p.text = (p.text or "") + elem
                        else:
                            p.append(elem)
                else:
                    p.text = str(text_content) if text_content else ""
            
            # Create tasks for nested items
            nested_items = self.extract_nested_items(item_content)
            for nested_item in nested_items:
                task = etree.SubElement(exercise, 'task')
                
                # Check workspace for task
                task_workspace = None
                if self.check_vfill(nested_item):
                    task_workspace = "1in"
                else:
                    vspace = self.check_vspace(nested_item)
                    if vspace:
                        task_workspace = vspace
                
                if task_workspace:
                    task.set('workspace', task_workspace)
                
                statement = etree.SubElement(task, 'statement')
                p = etree.SubElement(statement, 'p')
                nested_item_clean = self.clean_text(nested_item)
                text_content = self.text_to_element(nested_item_clean)
                if isinstance(text_content, list):
                    if text_content and isinstance(text_content[0], str):
                        p.text = text_content[0]
                    for elem in text_content[1:]:
                        if isinstance(elem, str):
                            if len(p) > 0:
                                p[-1].tail = (p[-1].tail or "") + elem
                            else:
                                p.text = (p.text or "") + elem
                        else:
                            p.append(elem)
                else:
                    p.text = str(text_content) if text_content else ""
        else:
            # No nested enumerate - single statement
            item_clean = self.clean_text(item_content)
            statement = etree.SubElement(exercise, 'statement')
            p = etree.SubElement(statement, 'p')
            text_content = self.text_to_element(item_clean)
            if isinstance(text_content, list):
                if text_content and isinstance(text_content[0], str):
                    p.text = text_content[0]
                for elem in text_content[1:]:
                    if isinstance(elem, str):
                        if len(p) > 0:
                            p[-1].tail = (p[-1].tail or "") + elem
                        else:
                            p.text = (p.text or "") + elem
                    else:
                        p.append(elem)
            else:
                p.text = str(text_content) if text_content else ""
        
        return exercise
    
    def convert(self):
        """Main conversion process"""
        content = self.extract_content_after_begin_document()
        
        # Clean up formatting commands early
        content = re.sub(r'\\noindent\s*', '', content)
        content = re.sub(r'\\bigskip\s*', '', content)
        
        # Extract objectives
        obj_intro, obj_items, content = self.extract_tcolorbox(content)
        
        # Extract title (first bold text) and remove it from the content
        title, content = self.extract_first_bold(content)
        
        # Extract introduction text before enumerate
        intro_text = self.extract_intro_before_enumerate(content)
        
        # Extract and process enumerate items
        enum_content = self.get_enumerate_content(content)
        items = self.extract_enumerate_items(enum_content)
        
        # Build XML
        self.root = etree.Element('worksheet')
        
        # Add title
        if title:
            title_elem = etree.SubElement(self.root, 'title')
            title_elem.text = title
        
        # Add objectives
        if obj_intro or obj_items:
            objectives = self.build_objectives(obj_intro, obj_items)
            self.root.append(objectives)
        
        # Add introduction
        intro_elem = self.build_introduction(intro_text)
        if intro_elem is not None:
            self.root.append(intro_elem)
        
        # Add exercises
        for item in items:
            if item.strip():
                exercise = self.build_exercise_or_tasks(item)
                self.root.append(exercise)
        
        return self.root
    
    def to_string(self):
        """Convert to formatted XML string"""
        if self.root is None:
            return None
        
        tree = etree.ElementTree(self.root)
        xml_str = etree.tostring(self.root, pretty_print=True, 
                                xml_declaration=True, encoding='UTF-8')
        return xml_str.decode('utf-8')


def main():
    if len(sys.argv) != 2:
        print("Usage: python convert.py filename.tex")
        sys.exit(1)
    
    input_file = sys.argv[1]
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    
    if not input_path.suffix == '.tex':
        print("Warning: Input file should have .tex extension")
    
    # Read the LaTeX file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            tex_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Convert
    converter = LatexToPretext(tex_content)
    converter.convert()
    xml_output = converter.to_string()
    
    # Write output
    output_file = input_path.stem + '.ptx'
    output_path = input_path.parent / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_output)
        print(f"Successfully converted '{input_file}' to '{output_path}'")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
