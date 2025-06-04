# chieta_lms/views.py

import json
import random
import time
import re
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from google import genai
from .question_bank import QUESTION_BANK
from .utils import extract_text
from .models import Assessment, GeneratedQuestion, QuestionBankEntry, CaseStudy


# -------------------------------------------
# 1) Add a new question to the Question Bank
# -------------------------------------------
@csrf_exempt
def add_question(request):
    if request.method == 'POST':
        qualification = request.POST.get('q_qualification')
        cs_selected_id = request.POST.get('q_case_study_select', '').strip()
        pasted_cs = request.POST.get('q_case_study', '').strip()
        text = request.POST.get('q_text', '').strip()
        marks = request.POST.get('q_marks', '').strip()

        # Determine which case study to use
        if cs_selected_id:
            cs_obj = CaseStudy.objects.filter(id=cs_selected_id).first()
            case_study_to_store = cs_obj.content if cs_obj else pasted_cs
        else:
            case_study_to_store = pasted_cs

        # Validation
        if not qualification or not text or not marks or not case_study_to_store:
            messages.error(request, "All fields (qualification, question text, marks, and a case study) are required.")
            return redirect('generate_tool_page')

        QuestionBankEntry.objects.create(
            qualification=qualification,
            text=text,
            marks=int(marks),
            case_study=case_study_to_store
        )

        messages.success(request, "Question added to the databank.")
        return redirect('generate_tool_page')


# ----------------------------
# 2) Add a new Case Study
# ----------------------------

@csrf_exempt
def add_case_study(request):
    if request.method == "POST":
        title = request.POST.get("cs_title")
        content = request.POST.get("cs_content")
        if title and content:
            CaseStudy.objects.create(title=title, content=content)
            messages.success(request, "Case study added successfully.")
    return redirect("generate_tool_page")


# ----------------------------------------
# 3) “Regular” view: render HTML + handle
#    Generate (via Gemini or fallback) and Save
# ----------------------------------------
# Initialize Gemini client once
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
def generate_tool_page(request):
    """
    Renders the 'generate_tool.html' template.
    - If request.method == POST and action == "generate": call Gemini (or fallback),
      collect questions up to mark_target, and show them in the template.
    - If request.method == POST and action == "save": parse question_block lines,
      create Assessment + GeneratedQuestion entries, and show a success message.
    """
    # Fetch all CaseStudy objects so dropdowns can populate
    case_studies = CaseStudy.objects.all()
    context = {"case_study_list": case_studies}

    if request.method == 'POST':
        action = request.POST.get("action")

        # --- HANDLE "Save Paper" ---
        if action == "save":
            try:
                qual = request.POST.get("qualification")
                question_block = request.POST.get("question_block", "").strip()

                # Only attempt to parse case_study_id if it's digits
                raw_cs_id = request.POST.get("case_study_id", "").strip()
                case_study_obj = None
                if raw_cs_id.isdigit():
                    case_study_obj = CaseStudy.objects.filter(id=int(raw_cs_id)).first()

                # Create a new Assessment record
                assessment = Assessment.objects.create(
                    eisa_id=f"EISA-{str(int(time.time()))[-4:]}",
                    qualification=qual,
                    paper="AutoGen",
                    comment="Generated and saved via tool",
                )

                # For each non-empty line in question_block, extract text + marks
                for line in question_block.split("\n"):
                    text_line = line.strip()
                    if not text_line:
                        continue

                    match = re.search(r"\((\d+)\s*marks?\)", text_line)
                    if match:
                        marks = int(match.group(1))
                        q_text = text_line[:match.start()].strip()
                    else:
                        marks = 0
                        q_text = text_line

                    GeneratedQuestion.objects.create(
                        assessment=assessment,
                        text=q_text,
                        marks=marks,
                        case_study=case_study_obj
                    )

                context["success"] = "Assessment and questions saved successfully."
                return render(request, "core/assessor-developer/generate_tool.html", context)

            except Exception as e:
                context["error"] = str(e)
                return render(request, "core/assessor-developer/generate_tool.html", context)

        # --- HANDLE "Generate Paper" ---
        if action == "generate":
            try:
                qual = request.POST.get("qualification")
                target = int(request.POST.get("mark_target", 0))
                demo_file = request.FILES.get("file", None)

                if not qual:
                    raise ValueError("Qualification is required.")

                if demo_file:
                    # Extract text from uploaded PDF/DOCX
                    text = extract_text(demo_file, demo_file.content_type)

                    # Grab a few sample questions from QUESTION_BANK to prime the prompt
                    samples = QUESTION_BANK.get(qual, [])[:3]
                    examples = "\n".join(f"- {q['text']}" for q in samples)

                    prompt = (
                        f"You’re an assessment generator for **{qual}**.\n"
                        f"Here are some example questions:\n{examples}\n\n"
                        "Now, given the following past‐paper text, generate JSON under the key 'questions',\n"
                        "where each item has 'text', 'marks' and 'case_study'.\n\n"
                        f"Past‐Papers Text:\n{text}"
                    )

                    resp = genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[prompt]
                    )

                    raw = resp.text.strip()
                    if not raw:
                        raise ValueError("Gemini API returned an empty response.")

                    # Clean the triple-backtick markers and smart quotes
                    cleaned = re.sub(r"^```json", "", raw)
                    cleaned = re.sub(r"```$", "", cleaned)
                    cleaned = cleaned.replace("“", '"').replace("”", '"')

                    data = json.loads(cleaned)
                    if "questions" not in data:
                        raise ValueError("Missing 'questions' key in Gemini output.")

                    all_qs = data["questions"]

                else:
                    # No file: fall back to QUESTION_BANK for this qualification
                    all_qs = QUESTION_BANK.get(qual, [])

                # Shuffle and pick questions until reaching mark_target
                random.shuffle(all_qs)
                selected, total = [], 0
                for q in all_qs:
                    try:
                        marks = int(float(q.get("marks", 0)))
                    except:
                        marks = 0

                    if total + marks <= target:
                        selected.append(q)
                        total += marks

                # Pass the selected questions and the full text block into context
                context.update({
                    "questions": selected,
                    "total": total,
                    "question_block": "\n\n".join(f"{q['text']} ({q['marks']} marks)" for q in selected)
                })

            except Exception as e:
                context["error"] = str(e)

    return render(request, "core/assessor-developer/generate_tool.html", context)

# ---------------------------------------
# 4) DRF endpoint: returns JSON (for AJAX)
# ---------------------------------------
@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_tool(request):
    """
    Accepts POST (qualification, mark_target, file) and returns:
    {
      "questions": [ { "text": "...", "marks": 5, "case_study": "..." }, … ],
      "total": <sum of marks>
    }
    This is the JSON‐returning endpoint (e.g. for AJAX / fetch calls).
    """
    try:
        qual = request.data.get("qualification")
        target = int(request.data.get("mark_target", 0))
        demo_file = request.FILES.get("file", None)

        if demo_file:
            text = extract_text(demo_file, demo_file.content_type)
            samples = QUESTION_BANK.get(qual, [])[:3]
            examples = "\n".join(f"- {q['text']}" for q in samples)

            prompt = (
                f"You’re an assessment generator for **{qual}**.\n"
                f"Here are some example questions:\n{examples}\n\n"
                "Now, given the following past‐paper text, generate JSON under the key 'questions',\n"
                "where each item has 'text', 'marks' and 'case_study'.\n\n"
                f"Past‐Papers Text:\n{text}"
            )

            resp = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )

            raw = resp.text.strip()
            if not raw:
                return JsonResponse({"error": "Gemini returned an empty response."}, status=500)

            cleaned = re.sub(r"^```json", "", raw)
            cleaned = re.sub(r"```$", "", cleaned)
            cleaned = cleaned.replace("“", '"').replace("”", '"')

            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as err:
                return JsonResponse({
                    "error": "Invalid JSON received from Gemini.",
                    "details": str(err),
                    "raw": cleaned[:300]
                }, status=500)

            if "questions" not in data:
                return JsonResponse({
                    "error": "Missing 'questions' key in Gemini output.",
                    "raw": cleaned
                }, status=500)

            all_qs = data["questions"]
        else:
            all_qs = QUESTION_BANK.get(qual, [])

        random.shuffle(all_qs)
        selected, total = [], 0

        for q in all_qs:
            try:
                marks = int(float(q.get("marks", 0)))
            except:
                marks = 0

            if total + marks <= target:
                selected.append(q)
                total += marks

        return JsonResponse({
            "questions": selected,
            "total": total
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)


# -----------------------------------------
# 5) Upload an existing assessment (PDF/Memo)
# -----------------------------------------
def upload_assessment(request):
    if request.method == "POST":
        eisa_id = f"EISA-{str(int(time.time()))[-4:]}"
        qual = request.POST["qualification"]
        paper = request.POST["paper_number"]
        saqa = request.POST["saqa_id"]
        file = request.FILES.get("file_input")
        memo = request.FILES.get("memo_file")
        comment = request.POST.get("comment_box", "")
        forward = request.POST.get("forward_to_moderator") == "on"

        Assessment.objects.create(
            eisa_id=eisa_id,
            qualification=qual,
            paper=paper,
            saqa_id=saqa,
            file=file,
            memo=memo,
            comment=comment,
            forward_to_moderator=forward,
        )

        messages.success(request, "Assessment uploaded successfully.")

        submissions = Assessment.objects.all().order_by("-created_at")
        return render(request, "core/assessor-developer/upload_assessment.html", {
            "submissions": submissions
        })

    submissions = Assessment.objects.all().order_by("-created_at")
    return render(request, "core/assessor-developer/upload_assessment.html", {
        "submissions": submissions
    })


# ---------------------------
# 6) Assessor Reports (chart)
# ---------------------------
def assessor_reports(request):
    data = [
        {
            "qualification": "Maintenance Planner",
            "toolsGenerated": 10,
            "toolsSubmitted": 8,
            "questionsAdded": 5,
        },
        {
            "qualification": "Quality Controller",
            "toolsGenerated": 15,
            "toolsSubmitted": 12,
            "questionsAdded": 9,
        },
    ]
    return render(request, "core/assessor-developer/assessor_reports.html", {
        "report_data": json.dumps(data)
    })


# -------------------------------------------
# 7) Assessment Archive / Filtering Page
# -------------------------------------------
def assessment_archive(request):
    qs = Assessment.objects.all()
    qual = request.GET.get("qualification", "")
    paper = request.GET.get("paper", "").strip()
    status = request.GET.get("status", "")

    if qual:
        qs = qs.filter(qualification=qual)
    if paper:
        qs = qs.filter(paper__icontains=paper)
    if status:
        qs = qs.filter(status=status)

    return render(request, "core/assessor-developer/assessment_archive.html", {
        "assessments": qs,
        "filter_qualification": qual,
        "filter_paper": paper,
        "filter_status": status,
    })


# -----------------------------
# 8) Assessor Dashboard (list)
# -----------------------------
def assessor_dashboard(request):
    assessments = Assessment.objects.all()
    return render(request, 'core/assessor-developer/assessor_dashboard.html', {
        'assessments': assessments
    })


# -------------------------------------------------
# 9) Submit a generated paper directly to Moderator
# -------------------------------------------------
@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def submit_generated_paper(request):
    try:
        qualification = request.POST.get("qualification")
        content = request.POST.get("paper_content")

        if not qualification or not content:
            return JsonResponse({"error": "Missing qualification or paper content."}, status=400)

        Assessment.objects.create(
            qualification=qualification,
            paper="AutoGen",
            comment="Forwarded from AI-generated tool",
            file=None,
            memo=None,
            forward_to_moderator=True,
            moderator_notes=content
        )

        return JsonResponse({"status": "success", "message": "Paper submitted to moderator."})

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)


# -------------------------------------------------
# 10) View a single Assessment + its Generated Questions
# -------------------------------------------------
def view_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    questions = assessment.generated_questions.all()

    if request.method == 'POST':
        notes = request.POST.get('moderator_notes', '').strip()
        assessment.moderator_notes = notes
        assessment.status = 'Submitted to ETQA'
        assessment.save()
        return redirect('assessor_dashboard')

    return render(request, 'core/assessor-developer/view_assessment.html', {
        'assessment': assessment,
        'questions': questions
    })
