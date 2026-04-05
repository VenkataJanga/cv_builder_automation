def extract_pdf(file_path: str) -> str:
    """Extract text from PDF (MVP1)"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    except Exception as e:
        raise RuntimeError("Install PyPDF2") from e
