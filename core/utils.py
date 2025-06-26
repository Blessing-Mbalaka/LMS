import io
from PyPDF2 import PdfReader
import docx

def extract_text_from_pdf(f):
    reader = PdfReader(f)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(f):
    f.seek(0)
    doc = docx.Document(io.BytesIO(f.read()))
    return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

def extract_text(file_obj, content_type):
    file_obj.seek(0)
    if content_type == "application/pdf":
        return extract_text_from_pdf(file_obj)
    elif content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_text_from_docx(file_obj)
    else:
        return file_obj.read().decode("utf-8", errors="ignore")
