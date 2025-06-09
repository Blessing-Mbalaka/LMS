# chieta_lms/views.py

import json
import random
import time
import re
import csv
from django.conf import settings
from django.http import JsonResponse,  HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from google import genai
from .question_bank import QUESTION_BANK
from .utils import extract_text
from .models import Assessment, GeneratedQuestion, QuestionBankEntry, CaseStudy 
from django.views.decorators.http import require_http_methods


# -------------------------------------------
# 1) Add a new question to the Question Bank
# -------------------------------------------
@csrf_exempt
def add_question(request):
    if request.method == 'POST':
        qualification = request.POST.get('q_qualification', '').strip()
        cs_selected_id = request.POST.get('q_case_study_select', '').strip()
        pasted_cs = request.POST.get('q_case_study', '').strip()
        text = request.POST.get('q_text', '').strip()
        marks = request.POST.get('q_marks', '').strip()

        # Determine which case study to use:
        if cs_selected_id:
            # If it's a digit, treat it as an existing CaseStudy ID.
            if cs_selected_id.isdigit():
                cs_obj = CaseStudy.objects.filter(id=int(cs_selected_id)).first()
                case_study_to_store = cs_obj.content if cs_obj else pasted_cs
            else:
                # Otherwise, the dropdown value was non‐numeric, so use it as pasted content.
                case_study_to_store = cs_selected_id
        else:
            case_study_to_store = pasted_cs

        # Validation: all four fields must be non‐empty
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

# chieta_lms/views.py

import random
import time
import re
import json
import traceback

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from django.http import JsonResponse

from .models import QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion
from .utils import extract_text
from google import genai

# Initialize Gemini once
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
def generate_tool_page(request):
    from .models import QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion

    # ─── Fetch dropdown data (case studies) ─────────────────────
    case_studies = CaseStudy.objects.all()

    # ─── Fetch ALL assessments; later we split by status ─────────
    all_assessments = Assessment.objects.all().order_by("-created_at")

    # ─── Build context with both “awaiting” and “approved” lists ──
    context = {
        "case_study_list": case_studies,
        # Papers whose status is still "Pending" (newly saved)
        "awaiting_assessments": Assessment.objects.filter(status="Pending").order_by("-created_at"),
        # Papers whose status indicates final approval
        "approved_assessments": Assessment.objects.filter(
            status__in=["Approved by Moderator", "Approved by ETQA"]
        ).order_by("-created_at"),
        # For the Question Bank tab
        "question_bank_entries": QuestionBankEntry.objects.all().order_by("-created_at"),
        # We still keep the full list around if you need it elsewhere
        "assessments": all_assessments,
    }

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        # ─── 1) “Compile from Question Bank” ────────────────────
        if action == "compile_from_bank":
            qual = request.POST.get("qualification", "").strip()
            raw_target = request.POST.get("mark_target", "").strip()
            raw_num = request.POST.get("num_questions", "").strip()

            # Basic validation
            if not qual or not raw_target.isdigit() or not raw_num.isdigit():
                messages.error(request, "Select qualification, numeric mark target, and numeric # of questions.")
                return redirect("generate_tool_page")

            target = int(raw_target)
            num_qs = int(raw_num)

            # Fetch matching entries
            entries = list(QuestionBankEntry.objects.filter(qualification=qual))
            if not entries:
                messages.error(request, f"No questions found for '{qual}'.")
                return redirect("generate_tool_page")

            random.shuffle(entries)
            compiled = []
            total_marks = 0

            # Pick until we hit either the mark‐target OR the requested number of questions
            for entry in entries:
                if len(compiled) >= num_qs:
                    break
                m = entry.marks or 0
                if total_marks + m <= target:
                    compiled.append(entry)
                    total_marks += m
                if total_marks >= target:
                    break

            context["compiled_questions"] = compiled
            return render(request, "core/assessor-developer/generate_tool.html", context)

        # ─── 2) “Generate (Gemini or fallback)” ───────────────────
        elif action == "generate":
            try:
                qual = request.POST.get("qualification", "").strip()
                target = int(request.POST.get("mark_target", "0").strip() or 0)
                demo_file = request.FILES.get("file", None)

                if not qual:
                    raise ValueError("Qualification is required.")

                if demo_file:
                    # Gemini path
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
                        raise ValueError("Gemini returned an empty response.")

                    cleaned = re.sub(r"^```json", "", raw)
                    cleaned = re.sub(r"```$", "", cleaned)
                    cleaned = cleaned.replace("“", '"').replace("”", '"')
                    data = json.loads(cleaned)
                    if "questions" not in data:
                        raise ValueError("Missing 'questions' key in Gemini output.")

                    all_qs = data["questions"]
                else:
                    # Fallback to in‐memory QUESTION_BANK
                    all_qs = QUESTION_BANK.get(qual, [])

                random.shuffle(all_qs)
                selected = []
                total_marks = 0
                for q in all_qs:
                    try:
                        m = int(float(q.get("marks", 0)))
                    except:
                        m = 0
                    if total_marks + m <= target:
                        selected.append(q)
                        total_marks += m
                    if total_marks >= target:
                        break

                context.update({
                    "questions": selected,
                    "total": total_marks,
                    "question_block": "\n\n".join(f"{q['text']} ({q['marks']} marks)" for q in selected)
                })
            except Exception as e:
                context["error"] = str(e)

            return render(request, "core/assessor-developer/generate_tool.html", context)

        # ─── 3) “Save Generated Paper” ───────────────────────────
        elif action == "save":
            try:
                qual = request.POST.get("qualification", "").strip()
                question_block = request.POST.get("question_block", "").strip()

                raw_cs_id = request.POST.get("case_study_id", "").strip()
                case_study_obj = None
                if raw_cs_id.isdigit():
                    case_study_obj = CaseStudy.objects.filter(id=int(raw_cs_id)).first()

                # Create a new Assessment with status="Pending" (default)
                assessment = Assessment.objects.create(
                    eisa_id=f"EISA-{str(int(time.time()))[-4:]}",
                    qualification=qual,
                    paper="AutoGen",
                    comment="Generated and saved via tool",
                    # default status is “Pending,” so it will show up under awaiting_…
                )

                # Parse each line of question_block, save as GeneratedQuestion
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

                context["success"] = "Paper saved and is now awaiting approval."
            except Exception as e:
                context["error"] = str(e)

            # Re‐fetch “awaiting” and “approved” lists in case they’ve changed
            context["awaiting_assessments"] = Assessment.objects.filter(status="Pending").order_by("-created_at")
            context["approved_assessments"] = Assessment.objects.filter(
                status__in=["Approved by Moderator", "Approved by ETQA"]
            ).order_by("-created_at")
            return render(request, "core/assessor-developer/generate_tool.html", context)

    # ─── GET (or no action) ──────────────────────────────────────
    return render(request, "core/assessor-developer/generate_tool.html", context)


# ---------------------------------------
# 4) DRF endpoint: returns JSON (for AJAX)
# ---------------------------------------
from django.db import transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from django.http import JsonResponse
import random
import re
import json
import traceback

from .utils import extract_text
from .models import QuestionBankEntry, CaseStudy
from google import genai

# Initialize Gemini client once
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_tool(request):
    """
    Accepts POST with:
      - qualification (string)
      - mark_target (int or numeric string)
      - optional file (PDF/DOCX)

    Returns JSON:
      {
        "questions": [
           { "text": "...", "marks": 5, "case_study": "..." }, …
        ],
        "total": <sum of marks>
      }
    """
    try:
        qual = request.data.get("qualification", "").strip()
        raw_target = request.data.get("mark_target", "").strip()
        demo_file = request.FILES.get("file", None)

        # Validate mark_target
        if not raw_target.isdigit():
            return JsonResponse(
                {"error": "mark_target must be a number."},
                status=400
            )
        target = int(raw_target)

        # If a file was uploaded, use Gemini path
        if demo_file:
            text = extract_text(demo_file, demo_file.content_type)

            # Optional: provide a few example questions from your in‐memory bank
            samples = QUESTION_BANK.get(qual, [])[:3]
            examples = "\n".join(f"- {q['text']}" for q in samples)

            prompt = (
                f"You’re an assessment generator for **{qual}**.\n"
                f"Here are some example questions:\n{examples}\n\n"
                "Now, given the following past‐paper text, generate JSON under the key 'questions',\n"
                "where each item has 'text', 'marks', and 'case_study'.\n\n"
                f"Past‐Papers Text:\n{text}"
            )

            resp = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
            raw = resp.text.strip()
            if not raw:
                return JsonResponse({"error": "Gemini returned an empty response."}, status=500)

            # Clean up JSON fences, smart quotes, etc.
            cleaned = re.sub(r"^```json", "", raw)
            cleaned = re.sub(r"```$", "", cleaned)
            cleaned = cleaned.replace("“", '"').replace("”", '"')

            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as err:
                return JsonResponse({
                    "error": "Invalid JSON received from Gemini.",
                    "details": str(err),
                    "raw_snippet": cleaned[:200]
                }, status=500)

            if "questions" not in data:
                return JsonResponse({
                    "error": "Missing 'questions' key in Gemini output.",
                    "raw": cleaned
                }, status=500)

            all_qs = data["questions"]

        # Otherwise, pull from QuestionBankEntry (database)
        else:
            # 1) Fetch all QuestionBankEntry matching this qualification
            entries = list(QuestionBankEntry.objects.filter(qualification=qual))
            if not entries:
                return JsonResponse(
                    {"error": f"No questions found in the bank for qualification '{qual}'."},
                    status=404
                )

            # 2) Shuffle and pick until mark_target is reached (or just under)
            random.shuffle(entries)
            selected = []
            total = 0

            for entry in entries:
                entry_marks = entry.marks or 0
                if total + entry_marks <= target:
                    selected.append({
                        "text": entry.text,
                        "marks": entry_marks,
                        "case_study": entry.case_study or ""
                    })
                    total += entry_marks
                if total >= target:
                    break

            all_qs = selected

        # If we got here, all_qs is a list of dicts with keys "text", "marks", and "case_study"
        # Now ensure we don't exceed mark target again (in case Gemini returned too many)
        random.shuffle(all_qs)
        final_selection = []
        running_sum = 0

        for q in all_qs:
            try:
                m = int(q.get("marks", 0))
            except (ValueError, TypeError):
                m = 0
            if running_sum + m <= target:
                final_selection.append(q)
                running_sum += m
            if running_sum >= target:
                break

        return JsonResponse({
            "questions": final_selection,
            "total": running_sum
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc().splitlines()[:5]  # send first few lines
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
        { "qualification": "Maintenance Planner", "toolsGenerated": 10, "toolsSubmitted": 8,  "questionsAdded": 5 },
        { "qualification": "Quality Controller",    "toolsGenerated": 15, "toolsSubmitted": 12, "questionsAdded": 9 },
    ]

    # pass both the JSON (for JS) and the Python list (for the template loop)
    return render(request, "core/assessor-developer/assessor_reports.html", {
        "report_data": json.dumps(data),
        "report_list": data,  
    })

# -------------------------------------------
# 7) Assessment Archive / Filtering Page
# -------------------------------------------
def assessment_archive(request):
    qs = Assessment.objects.all()

    # 1) grab the raw filter values
    qual   = request.GET.get("qualification", "").strip()
    paper  = request.GET.get("paper", "").strip()
    status = request.GET.get("status", "").strip()

    # 2) apply them if present
    if qual:
        qs = qs.filter(qualification=qual)
    if paper:
        qs = qs.filter(paper__icontains=paper)
    if status:
        qs = qs.filter(status=status)

    # 3) for the dropdowns, fetch the distinct set of qualifications & statuses
    all_quals    = (
        Assessment.objects
        .order_by("qualification")
        .values_list("qualification", flat=True)
        .distinct()
    )
    all_statuses = [c[0] for c in Assessment.STATUS_CHOICES]

    # 4) CSV export
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="assessment_archive.csv"'
        writer = csv.writer(response)
        writer.writerow(["EISA ID", "Qualification", "Paper", "Status", "Date"])

        for a in qs:
            writer.writerow([
                a.eisa_id,
                a.qualification,
                a.paper,
                a.status,
                a.created_at.date().isoformat()
            ])

        return response

    # 5) render HTML
    return render(request, "core/assessor-developer/assessment_archive.html", {
        "assessments":          qs,
        "filter_qualification": qual,
        "filter_paper":         paper,
        "filter_status":        status,
        "all_qualifications":   all_quals,
        "all_statuses":         all_statuses,
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
#---------------------------------------------------------------------------------------
 

def moderator_developer_dashboard(request):
    from .models import Assessment, Feedback
    pending   = Assessment.objects.filter(status="Submitted to Moderator")\
                                  .order_by("-created_at")
    recent_fb = Feedback.objects.select_related("assessment")\
                                .order_by("-created_at")[:10]

    return render(request, "core/assessor-developer/moderator_developer.html", {
        "pending_assessments": pending,
        "recent_feedback": recent_fb,
    })


@require_http_methods(["GET", "POST"])
def moderate_assessment(request, eisa_id):
    a = get_object_or_404(Assessment, eisa_id=eisa_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        notes      = request.POST.get("moderator_notes", "").strip()

        # Validate choice
        valid = dict(Assessment.STATUS_CHOICES)
        if new_status not in valid:
            messages.error(request, "Invalid status.")
        else:
            a.status          = new_status
            a.moderator_notes = notes
            a.save()
            messages.success(request, f"{a.eisa_id} updated to “{new_status}.”")
        return redirect("moderator_developer")

    return render(request, "core/assessor-developer/moderate_assessment.html", {
        "assessment": a,
        "status_choices": Assessment.STATUS_CHOICES,
    })

@require_http_methods(["POST"])
def add_feedback(request, eisa_id):
    a      = get_object_or_404(Assessment, eisa_id=eisa_id)
    to     = request.POST.get("to_user", "").strip()
    msg    = request.POST.get("message", "").strip()
    status = request.POST.get("status", "Pending")

    if not to or not msg:
        messages.error(request, "Both recipient and message are required.")
    else:
        Feedback.objects.create(
            assessment=a,
            to_user=to,
            message=msg,
            status=status
        )
        messages.success(request, "Feedback added.")
    return redirect("moderator_developer")
# checklist
from django.http import JsonResponse, Http404
from .models import ChecklistItem  # wherever you keep your checklist model

def toggle_checklist_item(request, item_id):
    try:
        item = ChecklistItem.objects.get(pk=item_id)
        item.completed = not item.completed
        item.save()
        return JsonResponse({"status": "ok", "completed": item.completed})
    except ChecklistItem.DoesNotExist:
        raise Http404()

def checklist_stats(request):
    total   = ChecklistItem.objects.count()
    done    = ChecklistItem.objects.filter(completed=True).count()
    pending = total - done
    return JsonResponse({
        "total": total,
        "completed": done,
        "pending": pending
    })

# QCTO Dashboard: list assessments submitted to ETQA
@require_http_methods(["GET"])
def qcto_dashboard(request):
    pending = Assessment.objects.filter(status="Submitted to ETQA").order_by("-created_at")
    return render(request, "core/qcto/qcto_dashboard.html", {
        "pending_assessments": pending,
    })

# QCTO Moderate Assessment: view + update status and notes
@require_http_methods(["GET", "POST"])
def qcto_moderate_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    if request.method == "POST":
        notes = request.POST.get("qcto_notes", "").strip()
        new_status = request.POST.get("status")
        valid_statuses = [choice[0] for choice in Assessment.STATUS_CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selection.")
        else:
            assessment.qcto_notes = notes
            assessment.status = new_status
            assessment.save()
            messages.success(request, f"{assessment.eisa_id} updated to {new_status}.")
        return redirect("qcto_dashboard")
    # On GET: render with current assessment and choices
    return render(request, "core/qcto/qcto_moderate_assessment.html", {
        "assessment": assessment,
        "status_choices": [
            ("Approved by ETQA", "Approve"),
            ("Rejected", "Reject"),
        ],
    })
    # 1) QCTO Dashboard: list assessments submitted to ETQA
@require_http_methods(["GET"])
def qcto_dashboard(request):
    pending = Assessment.objects.filter(status="Submitted to ETQA").order_by("-created_at")
    return render(request, "core/qcto/qcto_dashboard.html", {"pending_assessments": pending})

# 2) QCTO Moderate Assessment: view + update status and notes
@require_http_methods(["GET", "POST"])
def qcto_moderate_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    if request.method == "POST":
        notes = request.POST.get("qcto_notes", "").strip()
        new_status = request.POST.get("status")
        valid_statuses = [choice[0] for choice in Assessment.STATUS_CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status selection.")
        else:
            assessment.qcto_notes = notes
            assessment.status = new_status
            assessment.save()
            messages.success(request, f"{assessment.eisa_id} updated to {new_status}.")
        return redirect("qcto_dashboard")
    return render(request, "core/qcto/qcto_moderate_assessment.html", {
        "assessment": assessment,
        "status_choices": [("Approved by ETQA", "Approve"), ("Rejected", "Reject")],
    })

# 3) QCTO Reports: summary of QCTO-approved assessments
@require_http_methods(["GET"])
def qcto_reports(request):
    from django.db.models import Count
    stats = Assessment.objects.filter(status="Approved by ETQA").values('qualification').annotate(validated_count=Count('id')).order_by('qualification')
    return render(request, "core/qcto/qcto_reports.html", {"stats": stats})

# 4) QCTO Compliance & Reports: overview all assessments
@require_http_methods(["GET"])
def qcto_compliance(request):
    assessments = Assessment.objects.all().order_by('-created_at')
    return render(request, "core/qcto/qcto_compliance.html", {"assessments": assessments})

# 5) QCTO Final Assessment Review: list for QCTO decision
@require_http_methods(["GET"])
def qcto_assessment_review(request):
    reviews = Assessment.objects.filter(status="Submitted to ETQA").order_by('-created_at')
    return render(request, "core/qcto/qcto_assessment_review.html", {"reviews": reviews})

# 6) QCTO Archive: list archived QCTO decisions
@require_http_methods(["GET"])
def qcto_archive(request):
    archives = Assessment.objects.filter(status__in=["Approved by ETQA", "Rejected"]).order_by('-created_at')
    return render(request, "core/qcto/qcto_archive.html", {"archives": archives})

# 7) QCTO View Single Assessment Details
def qcto_view_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    generated_questions = GeneratedQuestion.objects.filter(assessment=assessment)
    return render(request, 'core/qcto/qcto_view_assessment.html', {
        'assessment': assessment,
        'generated_questions': generated_questions
    })

#8) QCTO Assessment view logic
@require_http_methods(["GET"])
def qcto_latest_assessment_detail(request):
    latest = Assessment.objects.filter(status="Approved by ETQA").order_by("-created_at").first()
    questions = GeneratedQuestion.objects.filter(assessment=latest)

    return render(request, "core/qcto/qcto_view_assessment.html", {
        "assessment": latest,
        "generated_questions": questions,
    })
