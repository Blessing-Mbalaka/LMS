import io
import re
from PyPDF2 import PdfReader
import docx

def extract_text_from_pdf(f):
    reader = PdfReader(f)
    texts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texts.append(t)
    return "\n\n".join(texts)

def extract_text_from_docx(f):
    doc = docx.Document(io.BytesIO(f.read()))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_text(file_obj, content_type):
    """
    f: InMemoryUploadedFile or file-like
    content_type: e.g. 'application/pdf' or docx mime
    """
    file_obj.seek(0)
    if content_type == "application/pdf":
        return extract_text_from_pdf(file_obj)
    elif content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_text_from_docx(file_obj)
    else:
        # fallback: try decoding
        return file_obj.read().decode("utf-8", errors="ignore")
