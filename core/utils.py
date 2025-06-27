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


import re

def extract_case_studies(raw_text):
    """
    Scan raw_text for every `Case Study:` block, capturing
    everything until the next question-number marker.
    Returns a dict: { question_number: case_study_text }
    """
    # question numbers look like 1.1 or 1.1.2 etc.
    qn_rx = re.compile(r"^(\d+(?:\.\d+)+)\b", re.MULTILINE)
    cs_rx = re.compile(r"Case Study\s*:\s*", re.IGNORECASE)

    lines = raw_text.splitlines()
    cs_map = {}
    current_q = None
    buffer = []

    for line in lines:
        # new question
        m_q = qn_rx.match(line.strip())
        if m_q:
            # if we were buffering a case‐study, attach it to the *previous* qn
            if current_q and buffer:
                cs_map[current_q] = "\n".join(buffer).strip()
            buffer = []
            current_q = m_q.group(1)
            continue

        # case‐study start
        if cs_rx.search(line):
            # begin buffering
            buffer.append(cs_rx.sub("", line).strip())
            continue

        # if buffering, keep adding until next question
        if buffer is not None and buffer != []:
            buffer.append(line.strip())

    # final flush
    if current_q and buffer:
        cs_map[current_q] = "\n".join(buffer).strip()

    return cs_map
