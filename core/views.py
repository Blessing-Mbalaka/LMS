# chieta_lms/views.py
import json, random, time
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from google import genai
from .question_bank import QUESTION_BANK
from .utils import extract_text
from .models import Assessment, GeneratedQuestion

# Gemini client setup
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# --- GET: Render Generate Tool Page ---
def generate_tool_page(request):
    return render(request, "core/assessor-developer/generate_tool.html")

# --- POST: Generate Questions via Gemini or Question Bank ---
@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_tool(request):
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
            all_qs = json.loads(resp.text)["questions"]
        else:
            all_qs = QUESTION_BANK.get(qual, [])

        random.shuffle(all_qs)
        selected, total = [], 0
        for q in all_qs:
            if total + q.get("marks", 0) <= target:
                selected.append(q)
                total += q.get("marks", 0)

        return JsonResponse({"questions": selected, "total": total})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def view_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)
    questions = assessment.questions.all()

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

        return redirect('assessor_dashboard')


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
