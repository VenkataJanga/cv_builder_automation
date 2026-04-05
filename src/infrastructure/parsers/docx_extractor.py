from typing import Optional

def extract_docx(file_path: str) -> str:
    """Extract text from a DOCX file including tables. Requires python-docx"""
    try:
        from docx import Document
    except Exception as e:
        raise RuntimeError("Install python-docx") from e

    doc = Document(file_path)
    
    # Extract all content in document order
    full_text = []
    
    # Get all paragraphs and tables in order
    for element in doc.element.body:
        # Check if it's a paragraph
        if element.tag.endswith('p'):
            # Find the corresponding paragraph object
            for para in doc.paragraphs:
                if para._element == element:
                    if para.text.strip():
                        full_text.append(para.text)
                    break
        # Check if it's a table
        elif element.tag.endswith('tbl'):
            # Find the corresponding table object
            for table in doc.tables:
                if table._element == element:
                    # Extract text from table cells
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                row_text.append(cell_text)
                        if row_text:
                            full_text.append(" | ".join(row_text))
                    break
    
    return "\n".join(full_text)
