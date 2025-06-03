# chieta_lms/views.py
import json, random, time, re
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from google import genai
from .question_bank import QUESTION_BANK
from .utils import extract_text
from .models import Assessment, GeneratedQuestion
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

# Gemini client setup
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Renders the HTML page
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def generate_tool_page(request):
    if request.method == 'POST':
        try:
            qual = request.POST.get("qualification")
            target = int(request.POST.get("mark_target", 0))
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
                all_qs = json.loads(resp.text)["questions"]
            else:
                all_qs = QUESTION_BANK.get(qual, [])

            random.shuffle(all_qs)
            selected, total = [], 0
            for q in all_qs:
                if total + q.get("marks", 0) <= target:
                    selected.append(q)
                    total += q.get("marks", 0)

            return render(request, "core/assessor-developer/generate_tool.html", {
                "questions": selected,
                "total": total,
            })

        except Exception as e:
            return render(request, "core/assessor-developer/generate_tool.html", {
                "error": str(e)
            })

    return render(request, "core/assessor-developer/generate_tool.html")

@csrf_exempt
def generate_tool_page(request):
    if request.method == 'POST':
        try:
            qual = request.POST.get("qualification")
            target = int(request.POST.get("mark_target", 0))
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
                all_qs = json.loads(resp.text)["questions"]
            else:
                all_qs = QUESTION_BANK.get(qual, [])

            random.shuffle(all_qs)
            selected, total = [], 0
            for q in all_qs:
                if total + q.get("marks", 0) <= target:
                    selected.append(q)
                    total += q.get("marks", 0)

            return render(request, "core/assessor-developer/generate_tool.html", {
                "questions": selected,
                "total": total,
            })

        except Exception as e:
            return render(request, "core/assessor-developer/generate_tool.html", {
                "error": str(e)
            })

    return render(request, "core/assessor-developer/generate_tool.html")

@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_tool(request):
    if request.method == "GET":
        return JsonResponse({"error": "You must use POST for this endpoint."}, status=405)

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

            print("RAW Gemini Output:")
            print(resp.text)

            cleaned_text = resp.text.strip()
            cleaned_text = re.sub(r"^```json", "", cleaned_text)
            cleaned_text = re.sub(r"```$", "", cleaned_text)
            cleaned_text = cleaned_text.replace("“", '"').replace("”", '"')

            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as json_err:
                return JsonResponse({
                    "error": "JSON decoding failed.",
                    "details": str(json_err),
                    "raw_response": cleaned_text
                }, status=500)

            if "questions" not in data:
                return JsonResponse({
                    "error": "Missing 'questions' key in Gemini output.",
                    "raw_response": cleaned_text
                }, status=500)

            all_qs = data["questions"]

        else:
            all_qs = QUESTION_BANK.get(qual, [])

        random.shuffle(all_qs)
        selected, total = [], 0

        for q in all_qs:
            try:
                raw_marks = q.get("marks", 0)
                marks = int(float(raw_marks))
            except Exception as m_err:
                print(f"Error parsing marks for question: {q} — {m_err}")
                marks = 0

            if total + marks <= target:
                selected.append(q)
                total += marks

        return JsonResponse({
            "questions": selected,
            "total": total
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)

def view_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    questions = assessment.generated_questions.all()

    if request.method == 'POST':
        notes = request.POST.get('moderator_notes', '').strip()
        assessment.moderator_notes = notes
        assessment.internal = 'Submitted to Moderator'
        assessment.forward_to_moderator = True
        assessment.save()
        return redirect('core/assessor-developer/assessor_dashboard')

    return render(
        request,
        'core/assessor-developer/view_assessment.html',
        {'assessment': assessment, 'questions': questions}
    )

from django.contrib import messages  # import at the top if not already

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

        # Reload the page instead of redirecting
        submissions = Assessment.objects.all().order_by("-created_at")
        return render(request, "core/assessor-developer/upload_assessment.html", {
            "submissions": submissions
        })

    submissions = Assessment.objects.all().order_by("-created_at")
    return render(request, "core/assessor-developer/upload_assessment.html", {
        "submissions": submissions
    })


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


def assessor_dashboard(request):
    assessments = Assessment.objects.all()
    return render(
        request,
        'core/assessor-developer/assessor_dashboard.html',
        {'assessments': assessments}
    )
@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def submit_generated_paper(request):
    try:
        qualification = request.POST.get("qualification")
        content = request.POST.get("paper_content")

        if not qualification or not content:
            return JsonResponse({"error": "Missing qualification or paper content."}, status=400)

        # Save it as a simplified assessment record (customize as needed)
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
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)
