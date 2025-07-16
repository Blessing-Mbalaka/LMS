import io
import re
from PyPDF2 import PdfReader
import docx
from docx import Document

print("✅ [CONFIRM] LOADED utils.py FROM:", __file__)

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
    #qn_rx = re.compile(
    #r'^\s*(\d+(?:\.\d+)+)\s+(.*?)(?:\s*\((\d+)\s*marks?\))?\s*$', 
    #re.IGNORECASE
#)
    qn_rx = re.compile(r'''
    ^\s*
    (?:Question(?:\s+Header)?\s*[:\-–]?\s*)?   # optional “Question” or “Question Header:” prefix
    (?P<number>\d+(?:\.\d+)+)\.?                # the numbering: 1.1 or 1.1.1 etc
    (?:\s*[-\.)]\s*)?                           # optional separator (., ), or – 
    (?P<text>.*?)                               # any following text (can be empty)
    (?:\s*\(\s*(?P<marks>\d+)\s*marks?\s*\))?   # optional “(10 Marks)”
    \s*$
    ''',
    re.IGNORECASE | re.VERBOSE
)


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

# Table extraction regex logic-This will be used to extract tables and questions,
# So what is happening? The code uses a regex delimination approach to identify the 
# XML file components of the word document and use the table fields deliminator to 
# Identify the fields on the table, and populate the data. 

# *In very simple*  terms: The question and its table should get extracted with this table---
# This is going to be an option, called the advanced extraction approach to help 
# structure the data. 

# _____________________________________________________________________________________
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


# These close imports matter please leave them here...
from docx import Document
from zipfile import BadZipFile
import io
import re
from docx import Document
from zipfile import BadZipFile

# 1. Match Column A with Column B Extractor
def extract_match_column_tables(docx_file):
    try:
        doc = Document(io.BytesIO(docx_file.read()))
    except BadZipFile:
        return {"error": "Uploaded file is not a valid .docx document."}
    except Exception as e:
        return {"error": str(e)}

    match_tables = []
    for tbl in doc.tables:
        rows = []
        for row in tbl.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                rows.append(cells)

        if rows and any("Column A" in cell or "Column B" in cell for cell in rows[0]):
            match_tables.append({
                "header": rows[0],
                "rows": rows[1:]
            })

    return match_tables


# 2. Multiple Choice Table Extractor
def extract_multiple_choice_tables(docx_file):
    try:
        doc = Document(io.BytesIO(docx_file.read()))
    except BadZipFile:
        return {"error": "Uploaded file is not a valid .docx document."}
    except Exception as e:
        return {"error": str(e)}

    mcq_tables = []
    for tbl in doc.tables:
        rows = []
        for row in tbl.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                rows.append(cells)

        if rows and "Correct Answer" in rows[0]:
            mcq_tables.append({
                "header": rows[0],
                "rows": rows[1:]
            })

    return mcq_tables


# 3. Combined Extractor 
def extract_all_tables(docx_file):
    docx_file.seek(0)
    match_tables = extract_match_column_tables(docx_file)

    docx_file.seek(0)
    mcq_tables = extract_multiple_choice_tables(docx_file)

    docx_file.seek(0)
    generic_tables = extract_generic_tables(docx_file)

    return {
        "match_tables": match_tables,
        "mcq_tables": mcq_tables,
        "generic_tables": generic_tables,
    }


from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from zipfile import BadZipFile
import io
import re

def extract_questions_with_metadata(docx_file):
    docx_file.seek(0)
    try:
        doc = Document(io.BytesIO(docx_file.read()))
    except BadZipFile:
        return {"error": "Uploaded file is not a valid .docx document."}

    # Regex to detect question numbers and marks
    #qn_rx = re.compile(
    #r'^\s*(\d+(?:\.\d+)+)\s+(.*?)(?:\s*\((\d+)\s*marks?\))?\s*$', 
    #re.IGNORECASE
#)

    qn_rx = re.compile(
        r'^\s*(\d+(?:\.\d+)+)\s+(.*?)\s*(?:\(\s*(\d+)\s*marks?\s*\))?\s*$',
        re.IGNORECASE | re.DOTALL
    )


    marks_rx = re.compile(r'\((\d+)\s*Marks?\)', re.IGNORECASE)

    results   = {}
    current_q = None
    in_cs     = False   # are we currently inside a case-study?

    for block in doc.element.body:

        # —— Paragraphs ——
        if block.tag.endswith('}p'):
            para = Paragraph(block, doc)
            text = para.text.strip()
            if not text:
                continue

            # 1️⃣ New question header?
            if m := qn_rx.match(text):
                current_q = m.group(1)
                in_cs     = False
                results[current_q] = {
                    "instruction": text,
                    "question_text": "",
                    "case_study": "",
                    "table": [],
                    "marks": marks_rx.search(text).group(1) if marks_rx.search(text) else ""
                }
                continue

            # 2️⃣ Case Study start?
            if current_q and text.lower().startswith("case study"):
                in_cs = True
                # strip off “Case Study:” label
                cs_body = re.sub(r'(?i)^case study\s*:?', '', text).strip()
                results[current_q]["case_study"] += cs_body + "\n"
                continue



            # 3️⃣ Any other paragraph
            if current_q:
                if in_cs:
                    results[current_q]["case_study"] += text + "\n"
                else:
                    results[current_q]["question_text"] += text + "\n"

        # —— Tables ——
        elif block.tag.endswith('}tbl') and current_q:
            tbl = Table(block, doc)
            rows = [
                [cell.text.strip() for cell in row.cells]
                for row in tbl.rows
                if any(cell.text.strip() for cell in row.cells)
            ]
            if rows:
                results[current_q]["table"].append(rows)

    # Final trim
    for qdata in results.values():
        qdata["question_text"] = qdata["question_text"].strip()
        qdata["case_study"]    = qdata["case_study"].strip()

    return results

def extract_generic_tables(docx_file):
    try:
        doc = Document(io.BytesIO(docx_file.read()))
    except BadZipFile:
        return {"error": "Uploaded file is not a valid .docx document."}
    except Exception as e:
        return {"error": str(e)}

    generic_tables = []
    for tbl in doc.tables:
        rows = []
        for row in tbl.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                rows.append(cells)

        # Skip if it's already handled
        if rows and not ("Column A" in rows[0] or "Correct Answer" in rows[0]):
            generic_tables.append({
                "header": rows[0],
                "rows": rows[1:]
            })

    return generic_tables


#This is the latest function which is meant to extract the full paper as is since we have proved we can extract each component individually.
import io
import re
import json
import base64
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from zipfile import BadZipFile
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

# XML namespaces for images
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
V_NS = "urn:schemas-microsoft-com:vml"


def extract_full_docx_structure(docx_file):
    docx_file.seek(0)
    try:
        doc = Document(io.BytesIO(docx_file.read()))
    except Exception:
        return {'error': 'Invalid .docx'}

    qn_rx = re.compile(r'''
        ^\s*
        (?:Question(?:\s+Header)?\s*[:\-\u2013]?\s*)?     # Optional "Question" prefix
        (?P<number>\d+(?:\.\d+)*)                          # Match 1 or 1.1 or 1.1.1 etc.
        (?:\s*[-\.)]\s*)?                                 # Optional trailing - or ) after number
        (?P<text>.*?)                                        # Capture text after number
        (?:\s*\(\s*(?P<marks>\d+)\s*marks?\s*\))?     # Optional (10 Marks)
        \s*$
    ''', re.IGNORECASE | re.VERBOSE | re.DOTALL)

    cr_rx = re.compile(r'(?i)^Constructive Response\s*:?.*')
    mcq_rx = re.compile(r'(?i)^Multiple Choice Questions?\s*:?.*')
    cs_rx = re.compile(r'(?i)^Case Study\s*:?.*')
    marks_only_rx = re.compile(r'^\(?\s*(\d+)\s*marks?\)?$', re.IGNORECASE)

    def is_subquestion(child, parent):
        return child.startswith(parent + '.') and child.count('.') == parent.count('.') + 1

    structured = []
    stack = []
    current_cs = None
    last_question_map = {}
    seen_questions = set()

    def create_question_block(num, rest, mark, subtype):
        return {
            'type': 'question',
            'subtype': subtype,
            'number': num,
            'text': rest,
            'marks': mark,
            'content': [],
            'children': []
        }

    for el in doc.element.body:
        if el.tag.endswith('}p'):
            # --- Handle embedded images (figures) ---
            found_figure = False
            try:
                for drawing in el.iter(f'{{{W_NS}}}drawing'):
                    for blip in drawing.iter(f'{{{A_NS}}}blip'):
                        rid = blip.get(f'{{{R_NS}}}embed')
                        part = doc.part.related_parts.get(rid)
                        if part and hasattr(part, 'blob'):
                            uri = "data:{};base64,{}".format(part.content_type, base64.b64encode(part.blob).decode())
                            fig_block = {'type': 'figure', 'data_uri': uri}
                            (stack[-1]['content'] if stack else structured).append(fig_block)
                            found_figure = True
                for shape in el.iter(f'{{{V_NS}}}imagedata'):
                    rid = shape.get(f'{{{R_NS}}}id')
                    part = doc.part.related_parts.get(rid)
                    if part and hasattr(part, 'blob'):
                        uri = "data:{};base64,{}".format(part.content_type, base64.b64encode(part.blob).decode())
                        fig_block = {'type': 'figure', 'data_uri': uri}
                        (stack[-1]['content'] if stack else structured).append(fig_block)
                        found_figure = True
            except Exception as e:
                print(f"⚠️ Figure extraction failed: {e}")
            if found_figure:
                continue

            para = Paragraph(el, doc)
            text = para.text.strip()
            if not text:
                continue

            m_mark = marks_only_rx.match(text)
            if m_mark:
                for q in reversed(stack):
                    if not q.get('marks'):
                        q['marks'] = m_mark.group(1)
                        break
                continue

            m_q = qn_rx.match(text)
            if m_q:
                num = m_q.group('number')
                rest = m_q.group('text').strip()
                mark = m_q.group('marks') or ''
                subtype = 'other'
                if cr_rx.match(rest):
                    subtype = 'constructive_response'
                elif mcq_rx.match(rest):
                    subtype = 'multiple_choice'
                elif cs_rx.match(rest):
                    subtype = 'case_study'

                if num in seen_questions:
                    continue

                new_q = create_question_block(num, rest, mark, subtype)
                while stack and not is_subquestion(num, stack[-1]['number']):
                    stack.pop()
                if stack:
                    stack[-1]['children'].append(new_q)
                else:
                    structured.append(new_q)
                stack.append(new_q)
                last_question_map[num] = new_q
                seen_questions.add(num)
                continue

            if cr_rx.match(text) or text.lower().startswith('constructive respond'):
                if stack:
                    block = {'type': 'question_text', 'text': text}
                    stack[-1]['content'].append(block)
                continue

            block = {'type': 'question_text', 'text': text}
            if stack:
                stack[-1]['content'].append(block)
            else:
                structured.append(block)

        elif el.tag.endswith('}tbl'):
            tbl = Table(el, doc)
            rows = [[cell.text.strip() for cell in row.cells] for row in tbl.rows]
            rows = [r for r in rows if any(r)]

            if rows:
                m0 = qn_rx.match(rows[0][0])
                if m0:
                    num = m0.group('number')
                    rest = m0.group('text').strip()
                    mark = m0.group('marks') or ''
                    subtype = 'other'
                    if mcq_rx.match(rest):
                        subtype = 'multiple_choice'
                    elif cr_rx.match(rest):
                        subtype = 'constructive_response'
                    elif cs_rx.match(rest):
                        subtype = 'case_study'

                    if num in seen_questions:
                        continue

                    new_q = create_question_block(num, rest, mark, subtype)
                    while stack and not is_subquestion(num, stack[-1]['number']):
                        stack.pop()
                    if stack:
                        stack[-1]['children'].append(new_q)
                    else:
                        structured.append(new_q)
                    stack.append(new_q)
                    last_question_map[num] = new_q
                    if len(rows) > 1:
                        new_q['content'].append({'type': 'table', 'rows': rows[1:]})
                    seen_questions.add(num)
                    continue

            table_block = {'type': 'table', 'rows': rows}
            if stack:
                stack[-1]['content'].append(table_block)
            else:
                structured.append(table_block)

    debug_preview = json.dumps(structured[:5], indent=2) + ("\n... [truncated]" if len(structured) > 5 else "")
    print("\n📦 [STRUCTURED PREVIEW]:\n" + debug_preview)
    return structured



def _flatten_structure(structure, parent=None):
    """
    Flatten the nested structure extracted from DOCX into a list.
    Preserves parent-child relationship using 'parent' field.
    """
    flat = []

    for block in structure:
        base = {
            "type": block.get("type"),
            "subtype": block.get("subtype", ""),
            "number": block.get("number", ""),
            "text": block.get("text", ""),
            "marks": block.get("marks", ""),
            "parent": parent,
            "children": []  # Only used temporarily for visual rebuilds
        }

        # Attach embedded content (figures, tables, paragraphs)
        if "content" in block:
            base["content"] = []
            for c in block["content"]:
                base["content"].append({
                    "type": c.get("type"),
                    "text": c.get("text", ""),
                    "rows": c.get("rows", []),
                    "data_uri": c.get("data_uri", "")
                })

        flat.append(base)

        # Recurse through children
        for child in block.get("children", []):
            flat += _flatten_structure([child], parent=block.get("number"))

    return flat




#We need to add a filtering layer that utilises AI to classify the final Structure to guaratee the final output,
#The intent is to give a better structured output so we can see a better paper extraction.
#***********************************END OF *****************************************************************************************************
#----------------------------------------------

#<---------------Serializer Node-----[used to preserve paper structure]----------------------->
def serialize_node(obj):
    """
    Converts either an extracted dict OR an ExamNode instance into a unified format.
    """
    if isinstance(obj, dict):
        return {
            "id":       obj.get("id"),
            "type":     obj.get("type", ""),
            "number":   obj.get("number", ""),
            "marks":    obj.get("marks", ""),
            "text":     obj.get("text", ""),
            "content":  obj.get("content", []),
            "children": [serialize_node(c) for c in obj.get("children", [])],
            **({"data_uri": obj.get("data_uri", "")} if obj.get("type") == "figure" else {})
        }

    if isinstance(obj, ExamNode):
        payload = obj.payload or {}
        return {
            "id":       str(obj.id),
            "type":     obj.node_type,
            "number":   obj.number,
            "marks":    obj.marks,
            "text":     payload.get("text", ""),
            "content":  payload.get("content", []),
            "children": [serialize_node(child) for child in obj.children.all().order_by("number")],
            **({"data_uri": payload.get("data_uri", "")} if obj.node_type == "figure" else {})
        }

    raise TypeError("Unsupported object type")
#<---------------Critical for paper reconstruction and preserving formating------------------->




#--------Start of saving Serialized nodes to DB----------------------------------------------->
from core.models import ExamNode
import uuid

def save_nodes_to_db(nodes, paper):
    """
    nodes: a flat list of dicts each with at least 'number', 'text', 'type', etc.
    paper: the Paper instance to attach them to
    """
    # 1. sort by how many dots in the number (parents first)
    nodes_sorted = sorted(nodes, key=lambda n: n['number'].count('.'))
    # 2. map from number -> saved ExamNode
    number_map = {}

    for node in nodes_sorted:
        num = node['number']
        # find parent by stripping last segment (e.g. '1.1.2' -> '1.1')
        parent = None
        if '.' in num:
            parent_num = num.rsplit('.', 1)[0]
            parent = number_map.get(parent_num)

        # create the node
        db_node = ExamNode.objects.create(
            id=(node.get("id") or uuid.uuid4().hex)[:32],
            paper=paper,
            parent=parent,
            node_type=node.get("type", ""),
            number=num,
            marks=node.get("marks", ""),
            text=node.get("text", ""),
            content=node.get("content", []),
            data_uri=node.get("data_uri", ""),
            payload={
                "text":    node.get("text", ""),
                "content": node.get("content", []),
                "data_uri": node.get("data_uri", "")
            },
        )

        # remember it for its children
        number_map[num] = db_node











import json
import re
import google.generativeai as genai

def auto_classify_blocks_with_gemini(blocks):
    print("🔥 [DEBUG] Using UPDATED Gemini classification function")
        #  Defensive type check to prevent calling .get() on strings
    if not isinstance(blocks, list) or not all(isinstance(b, dict) for b in blocks):
        raise TypeError("❌ Expected list of dicts, but got invalid structure.")

    # Step 1: Basic pre-labeling
    types = []
    for b in blocks:
        text = (b.get('text') or '').strip()
        if re.match(r'^\d+(?:\.\d+)+', text):
            types.append('question_header')
        elif text.lower().startswith('case study'):
            types.append('case_study')
        elif b.get('data_uri'):
            types.append('figure')
        elif b.get('rows') is not None:
            types.append('table')
        elif re.fullmatch(r'-{5,}', text):
            types.append('instruction')
        else:
            types.append(None)

    print("🧠 [LOG] Pre-assigned types:", types)

    # Step 2: System prompt
    system_prompt = """
You are a classification assistant. You will be given a list of blocks extracted from a question paper.

Some blocks have already been pre-classified as one of: question_header, case_study, table, or figure — leave those untouched.

Your job is to classify the remaining untyped blocks using ONLY one of the following labels:
- "paragraph": General text that doesn’t give specific instructions, often background or descriptive.
- "instruction": Any directive to the student (e.g. "Answer all questions", "Use only the booklet", "Show all working").
- "rubric": General rules or formatting notes that apply to the exam, typically near the top of the paper.
- "diagram": Describes a visual element without being a full figure block.

🛑 DO NOT classify any non-question text as "question_header".

---
**Examples of proper classification:**
- "1.1 Define the term ‘quality assurance’. (5 Marks)" → question_header
- "Use only the supplied EISA booklets." → instruction
- "All questions are compulsory." → instruction
- "The purpose of quality assurance is to ensure..." → paragraph
- "Diagrams must be labelled clearly." → rubric

---
Your output should ONLY be this JSON format:

{
  "types": ["paragraph", "instruction", "rubric", ...]
}
""".strip()

    try:

        for i in range(4):
            print(f"🔁 [LOOP] Running classification pass {i+1}/4")
        # Step 3: Gemini request
            model = genai.GenerativeModel('gemini-1.5-flash')  # or 'gemini-1.5-pro' if preferred
            response = model.generate_content([
            system_prompt,
            json.dumps({'blocks': blocks, 'partial_types': types})
        ])

        # Step 4: Log and clean response
        raw_text = (response.text or '').strip()
        print("📨 [LOG] Gemini raw response:", raw_text[:300], "..." if len(raw_text) > 300 else "")

        # Remove Markdown-style triple backticks if they exist
        cleaned_text = re.sub(r'^```(?:json)?|```$', '', raw_text, flags=re.IGNORECASE | re.MULTILINE).strip()

        parsed = json.loads(cleaned_text)
        ai_types = parsed.get('types', [])

        if not isinstance(ai_types, list):
            raise ValueError("Gemini response does not contain a valid 'types' list")

        # Step 5: Final merge
        final = [pre or ai for pre, ai in zip(types, ai_types)]
        print("✅ [LOG] Final merged types:", final)
        return final

    except Exception as e:
        print("❌ [ERROR] Gemini classification failed:", str(e))
        #add print payload so we can see th tree...
        return ['paragraph'] * len(blocks)
    
    



#----------------------------------------------end----------------------------------------------------------------
#responsible for AI filtering not classification only.
import os
import json
import re
import logging


# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Gemini Classification Logic ---

def is_structural_noise(text):
    text = text.strip().lower()
    noise_patterns = [
        r'^students are only allowed',
        r'^question paper',
        r'^instructions',
        r'^section [a-z]',
        r'^answer all questions',
        r'^eisa rules',
        r'^quality controller',
        r'^page \d+',
        r'^external integrated summative assessment',
        r'^this question paper consists of',
    ]
    return any(re.match(pattern, text) for pattern in noise_patterns)

def classify_block_type(text_blocks):
    """
    Accepts a list of text strings and returns a list of predicted block types:
    e.g., ['question', 'rubric', 'case_study', 'table', ...]
    """
    if not GEMINI_API_KEY:
        return ["other"] * len(text_blocks)

    prompt = f"""
You are a document examiner for exam papers.

Classify each of the following blocks into one of the following types:

- 'question': a numbered question (e.g. '1.1 Define...')
- 'case_study': if it contains context or scenario
- 'instruction': if it tells the learner what to do
- 'rubric': if it describes how marks are allocated
- 'table': if the block is a table or looks like one
- 'heading': if it is a heading like 'SECTION A'
- 'noise': if it is unrelated or structural like 'Page 1', or 'EISA Rules'
- 'other': if unsure

Return a JSON list in the same order as input.

INPUT:
{json.dumps(text_blocks[:40], indent=2)}

Respond with only the JSON list.
    """.strip()

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        raw = response.text.strip()

        logging.info("📨 Gemini raw response: \n%s", raw)

        parsed = json.loads(raw)
        return parsed

    except Exception as e:
        logging.error("❌ Gemini classification failed: %s", e)
        return ["other"] * len(text_blocks)


#Rebuild a tree structure  for ensuring the tree instead of flattened is stored in DB
def rebuild_tree(flat_nodes):
    """
    Given a flat list of blocks with `number` and `parent_id`,
    reconstruct a nested tree.
    """
    id_map = {n['id']: {**n, 'children': []} for n in flat_nodes}

    root_nodes = []
    for node in id_map.values():
        parent_id = node.get('parent_id')
        if parent_id and parent_id in id_map:
            id_map[parent_id]['children'].append(node)
        else:
            root_nodes.append(node)

    return root_nodes

#<----------------------------------------------------------------------------------------------------------------------------->


#<----------------------------------------------------------------------------------------------------------------------------->

def rebuild_nested_structure(flat_nodes):
    """
    Rebuilds a nested structure: parents like '1.1' will include their children like '1.1.1', '1.1.2' in a `children` list.
    Assumes each node has: id, number, parent_id (optional), and content fields.
    """
    id_to_node = {}
    root_nodes = []

    # Step 1: Prepare nodes and mapping
    for node in flat_nodes:
        node_copy = {**node, "children": []}
        id_to_node[node["id"]] = node_copy

    # Step 2: Assign children to parents
    for node in flat_nodes:
        parent_id = node.get("parent_id")
        if parent_id and parent_id in id_to_node:
            id_to_node[parent_id]["children"].append(id_to_node[node["id"]])
        else:
            root_nodes.append(id_to_node[node["id"]])  # no parent → top-level

    # Step 3: Optional — sort top-level by number (1.1, 1.2, ...)
    root_nodes.sort(key=lambda n: n.get("number", ""))
    return root_nodes
