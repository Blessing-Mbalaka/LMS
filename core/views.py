import os
import traceback
from django.contrib import messages
from rest_framework.parsers import MultiPartParser, JSONParser
from .forms import QualificationForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion, Batch, AssessmentCentre
import json
import random
from django.db import models
from django.urls import reverse
import time
import re
from .models import MCQOption
from .forms import EmailRegistrationForm
import uuid
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

from .models import Assessment, GeneratedQuestion, QuestionBankEntry, CaseStudy, Feedback, AssessmentCentre, ExamAnswer
from django.views.decorators.http import require_http_methods
from collections import defaultdict
from django.contrib import messages
#Imports for Login logic 
from django.core.mail  import send_mail
from django.utils.timezone  import now
from django.contrib.admin.views.decorators import staff_member_required
import random, string
from django.contrib.auth.decorators import login_required
from .models import Qualification, CustomUser


from .forms import CustomUserForm
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.admin import UserAdmin
from .models import AssessmentCentre
from .forms import AssessmentCentreForm, QualificationForm
from .models import (
    QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion,
    Qualification, CustomUser, AssessmentCentre, Feedback
)
from .forms import QualificationForm, AssessmentCentreForm, CustomUserForm
from .question_bank import QUESTION_BANK
from utils import extract_text
from google import genai
from django.conf import settings
from django.contrib.auth import get_user_model


# Initialize AI client
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)



# core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import EmailRegistrationForm
from .models import CustomUser
from django.utils.timezone import now
def redirect_user_by_role(user ):
    role = user.role
    if role == 'default':
        return redirect ('default')
    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'moderator':
        return redirect('moderator_developer')
    elif role == 'internal_mod':
        return redirect('internal_moderator_dashboard')
    elif role in 'assessor_dev':
        return redirect('assessor_dashboard')
    elif role in 'qcto':
        return redirect('qcto_dashboard')
    elif role in 'etqa':
        return redirect('etqa_dashboard')
    elif role == 'learner':
        return redirect('student_dashboard')
    else:
        return redirect('home')

def register(request):
    if request.method == "POST":
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.is_staff  = (user.role != 'learner')
            user.save()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = EmailRegistrationForm()

    return render(request, "core/login/login.html", {"form": form})

def custom_login(request):
    # we reuse the registration form so the template can render both sides
    list(messages.get_messages(request))   
    reg_form = EmailRegistrationForm()
       
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        try:
            u = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            u = None

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect_user_by_role(user)
        else:
            return render(request, "core/login/login.html", {
                "form":  reg_form,
                "error": "Invalid credentials",
            })

    return render(request, "core/login/login.html", {"form": reg_form})
#_______________________________________________________________________________________________________
#******************************************************************************************************
#LOGIN LOGIC AND USER ACCESS CONTROL STARTS HERE********************************************************
#*******************************************************************************************************
#*******************************************************************************************************

from django.contrib.auth import get_user_model

from django.contrib.auth.decorators import login_required

from .models import Qualification

CustomUser = get_user_model()  

@login_required
# @staff_member_required
def user_management(request):
    if request.method == 'POST':
        name  = request.POST['name']
        email = request.POST['email']
        role  = request.POST['role']
        qual_id = request.POST['qualification']
        qualification = Qualification.objects.filter(pk=qual_id).first()

        if not (name and email and role and qualification):
            messages.error(request, "Please fill in all required fields.")
            return redirect('user_management')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect('user_management')

        # Split name
        parts = name.split()
        first = parts[0]
        last  = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Generate random password
        pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # Create user with is_staff True for all except learners
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            first_name=first,
            last_name=last,
            role=role,
            qualification=qualification,
            is_active=True,
            is_staff=(role != 'learner'),
            activated_at=now()
        )
        user.set_password(pwd)
        user.save()

        # Send email
        send_mail(
            'Your CHIETA LMS Password',
            f'Hello {first}, your new password is: {pwd}',
            'noreply@chieta.co.za',
            [email],
            fail_silently=False,
        )
        messages.success(request, f"User {email} created and password emailed.")
        return redirect('user_management')

    users = CustomUser.objects.select_related('qualification').exclude(is_superuser=True)
    quals = Qualification.objects.all()
    return render(request, 'core/administrator/user_management.html', {
        'users': users,
        'qualifications': quals,
        'role_choices': CustomUser.ROLE_CHOICES,
    })

#*******************************************************************************************************
#*******************************************************************************************************
#Role Management is done here
#______________________________________________________________________________________________________
    
@login_required
# @staff_member_required
def update_user_role(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    if request.method=='POST':
        user.role = request.POST['role']
        user.save()
        messages.success(request, f"Role updated for {user.get_full_name()}.")
    return redirect('user_management')
#_______________________________________________________________________________________________________
#_______________________________________________________________________________________________________
# User qualification
@login_required
# @staff_member_required
def update_user_qualification(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    if request.method=='POST':
        qual = get_object_or_404(Qualification, pk=request.POST['qualification'])
        user.qualification = qual
        user.save()
        messages.success(request, f"Qualification updated for {user.get_full_name()}.")
    return redirect('user_management')

#User Status
@login_required
# @staff_member_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    user.is_active = not user.is_active
    if user.is_active:
        user.activated_at   = now()
        user.deactivated_at = None
    else:
        user.deactivated_at = now()
    user.save()
    state = "activated" if user.is_active else "deactivated"
    messages.success(request, f"{user.get_full_name()} {state}.")
    return redirect('user_management')
#********************************************************************************************************
#********************************************************************************************************
# ASSESSMENT CENTRE VIEWS FOR ADDING ETC________________________________________________________________
def assessment_centres_view(request):
    centres = AssessmentCentre.objects.all()
    form = AssessmentCentreForm()

    # Handle form submission
    if request.method == 'POST':
        form = AssessmentCentreForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Assessment centre added successfully.")
            return redirect('assessment_centres')
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'core/administrator/centre.html', {
        'centres': centres,
        'form': form,
    })


def edit_assessment_centre(request, centre_id):
    centre = get_object_or_404(AssessmentCentre, id=centre_id)

    if request.method == 'POST':
        form = AssessmentCentreForm(request.POST, instance=centre)
        if form.is_valid():
            form.save()
            messages.success(request, 'Assessment centre updated successfully!')
            return redirect('assessment_centres')
    else:
        form = AssessmentCentreForm(instance=centre)

    return render(request, 'core/edit_centre.html', {
        'form': form,
        'centre': centre,
    })


def delete_assessment_centre(request, centre_id):
    centre = get_object_or_404(AssessmentCentre, id=centre_id)
    centre.delete()
    messages.success(request, 'Assessment centre removed successfully!')
    return redirect('assessment_centres')

@login_required
# @staff_member_required
def admin_dashboard(request):
    
    if request.method == "POST":
        q_id      = request.POST.get("qualification")
        paper     = request.POST.get("paper_number", "").strip()
        saqa      = request.POST.get("saqa_id", "").strip()
        file_obj  = request.FILES.get("file_input")
        memo_obj  = request.FILES.get("memo_file")

        qual = get_object_or_404(Qualification, pk=q_id)
        Assessment.objects.create(
            eisa_id=f"EISA-{uuid.uuid4().hex[:8].upper()}",
            qualification=qual,
            paper=paper,
            saqa_id=saqa,
            file=file_obj,
            memo=memo_obj,
            created_by=request.user,     
        )
        messages.success(request, "Assessment uploaded successfully.")
        return redirect("admin_dashboard")

    # GET: show the dashboard
    tools       = Assessment.objects.select_related("qualification","created_by")\
                                     .order_by("-created_at")
    total_users = CustomUser.objects.filter(is_superuser=False).count()
    quals       = Qualification.objects.all()

    return render(request, "core/administrator/admin_dashboard.html", {
        "tools":           tools,
        "total_users":     total_users,
        "qualifications":  quals,
    })

#_____________________________________________________________________________________________________


#_____________________________________________________________________________________________________
def qualification_management_view(request):
    qualifications = Qualification.objects.all()
    form = QualificationForm()

    if request.method == 'POST':
        form = QualificationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Qualification added successfully.")
            return redirect('manage_qualifications')
        else:
            print("Form errors:", form.errors)  # ✅ This helps you see why it failed
            messages.error(request, "Please correct the errors below.")

    return render(request, 'core/administrator/qualifications.html', {
        'qualifications': qualifications,
        'form': form,
    })

#0) Databank View 2025/06/10 made to handle logic for the databank for the question generation.

def databank_view(request):
    if request.method == "POST":
        qt = request.POST["question_type"]
        qualification_code = request.POST["qualification"]
        qualification = Qualification.objects.get(code=qualification_code)

        q = QuestionBankEntry.objects.create(
            qualification=qualification,
            question_type=qt,
            text=request.POST["text"],
            marks=request.POST["marks"],
            case_study=(
                CaseStudy.objects.get(pk=request.POST["case_study"])
                if qt == "case_study" else None
            )
        )

        if qt == "mcq":
            for i in range(1, 5):
                txt = request.POST.get(f"opt_text_{i}")
                corr = request.POST.get(f"opt_correct_{i}") == "on"
                if txt:
                    q.options.create(text=txt, is_correct=corr)

        return redirect("databank")

    # GET request
    entries = QuestionBankEntry.objects.select_related("case_study", "qualification").prefetch_related("options").all()
    databank = defaultdict(list)
    for e in entries:
        databank[e.qualification].append(e)

    qualification_codes = Qualification.objects.values_list("code", flat=True)

    return render(request, "core/administrator/databank.html", {
        "databank": dict(databank),
        "qualifications": sorted(Qualification.objects.all(), key=lambda q: q.name),
        "qualification_codes": qualification_codes,
        "case_studies": CaseStudy.objects.all(),
        "question_bank_entries": entries,
    })

# -------------------------------------------
# 1) Add a new question to the Question Bank
# -------------------------------------------


@csrf_exempt
def add_question(request):
    if request.method == 'POST':
        q_type = request.POST.get('question_type')
        qualification_id   = request.POST.get('qualification')
        marks = request.POST.get('marks')
        text = request.POST.get('text')

        # Fetch qualification object
        try:
             qualification = get_object_or_404(Qualification, pk=qualification_id)
        except ValueError:
            messages.error(request, "Invalid qualification selected.")
            return redirect('databank')

        # Prepare case study if needed
        case_study_id = request.POST.get('case_study')
        case_study = None
        if q_type == 'case_study' and case_study_id:
            try:
                case_study = CaseStudy.objects.get(id=case_study_id)
            except CaseStudy.DoesNotExist:
                messages.error(request, "Selected case study not found.")
                return redirect('generate_tool_page')

        # Basic validation
        if not text or not marks:
            messages.error(request, "Please fill in all required fields.")
            return redirect('generate_tool_page')

        # Create the question
        question = QuestionBankEntry.objects.create(
            qualification=qualification,
            question_type=q_type,
            text=text,
            marks=int(marks),
            case_study=case_study
        )

        # Handle MCQ options
        if q_type == 'mcq':
            has_correct = False
            for i in range(1, 5):
                opt_text = request.POST.get(f'opt_text_{i}')
                is_correct = request.POST.get(f'opt_correct_{i}') == 'on'
                if opt_text:
                    MCQOption.objects.create(
                        question=question,
                        text=opt_text,
                        is_correct=is_correct
                    )
                    if is_correct:
                        has_correct = True
            if not has_correct:
                question.delete()
                messages.error(request, "At least one MCQ option must be marked as correct.")
                return redirect('generate_tool_page')

        messages.success(request, "Question added to the databank.")
        return redirect('databank')

@csrf_exempt
def add_case_study(request):
    if request.method == 'POST':
        title = request.POST.get('cs_title')
        content = request.POST.get('cs_content')
        if title and content:
            CaseStudy.objects.create(title=title, content=content)
            messages.success(request, "Case study added successfully.")
    return redirect('databank')
############################################################################################
#Critical do not touch this danger!!! generate_tool is offlimits
###########################################################################################
############################################################################################
########################################################################################### 
@csrf_exempt
def generate_tool_page(request):
    case_studies = CaseStudy.objects.all()
    all_assessments = Assessment.objects.all().order_by("-created_at")

    # Group questions by qualification
    databank = defaultdict(list)
    for q in QuestionBankEntry.objects.select_related("qualification"):
        databank[q.qualification.name].append(q)

    qualifications = Qualification.objects.all()
    selected_qualification = None

    context = {
        "case_study_list": case_studies,
        "awaiting_assessments": Assessment.objects.filter(status="Pending").order_by("-created_at"),
        "approved_assessments": Assessment.objects.filter(status__in=["Approved by Moderator","Approved by ETQA"]).order_by("-created_at"),
        "assessments": all_assessments,
        "databank": databank,
        "qualifications": qualifications,
        "case_studies": case_studies,
        "selected_qualification": selected_qualification,
    }

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "compile_from_bank":
            qual = request.POST.get("qualification", "").strip()
            selected_qualification = qual
            raw_target = request.POST.get("mark_target", "").strip()
            raw_num = request.POST.get("num_questions", "").strip()

            if not qual or not raw_target.isdigit() or not raw_num.isdigit():
                context.update({
                    "error": "Select qualification, numeric mark target, and numeric # of questions.",
                    "selected_qualification": qual
                })
                return render(request, "core/assessor-developer/generate_tool.html", context)

            target, num_qs = int(raw_target), int(raw_num)
            entries = list(QuestionBankEntry.objects.filter(qualification__code=qual))
            if not entries:
                context.update({
                    "error": f"No questions found for '{qual}'.",
                    "selected_qualification": qual
                })
                return render(request, "core/assessor-developer/generate_tool.html", context)

            random.shuffle(entries)
            compiled, total = [], 0
            for e in entries:
                if len(compiled) >= num_qs:
                    break
                if total + (e.marks or 0) <= target:
                    compiled.append(e)
                    total += e.marks or 0
                if total >= target:
                    break

            context.update({
                "compiled_questions": compiled,
                "selected_qualification": qual
            })
            return render(request, "core/assessor-developer/generate_tool.html", context)

        elif action == "save":
            qual = request.POST.get("qualification", "").strip()
            question_block = request.POST.get("question_block", "").strip()
            raw_cs_id = request.POST.get("case_study_id", "").strip()
            cs_obj = CaseStudy.objects.filter(id=int(raw_cs_id)).first() if raw_cs_id.isdigit() else None

            qualification = Qualification.objects.filter(code=qual).first()
            if not qualification:
                context.update({
                    "error": f"Selected qualification '{qual}' does not exist.",
                    "selected_qualification": qual
                })
                return render(request, "core/assessor-developer/generate_tool.html", context)

            # Use UUID for eisa_id
            assessment = Assessment.objects.create(
                eisa_id=f"EISA-{uuid.uuid4().hex[:8].upper()}",
                qualification=qualification,
                paper="AutoGen",
                comment="Generated and saved via tool",
            )

            for line in question_block.split("\n"):
                text_line = line.strip()
                if not text_line:
                    continue
                match = re.search(r"\((\d+)\s*marks?\)", text_line)
                if match:
                    m = int(match.group(1))
                    q_text = text_line[:match.start()].strip()
                else:
                    m = 0
                    q_text = text_line
                GeneratedQuestion.objects.create(
                    assessment=assessment,
                    text=q_text,
                    marks=m,
                    case_study=cs_obj
                )

            context.update({
                "success": "Paper submitted to moderator and is now awaiting approval.",
                "selected_qualification": qual,
                "awaiting_assessments": Assessment.objects.filter(status="Pending").order_by("-created_at"),
            })
            return render(request, "core/assessor-developer/generate_tool.html", context)

    return render(request, "core/assessor-developer/generate_tool.html", context)


#**********************************************************************************************************
@require_http_methods(["GET", "POST"])
def upload_assessment(request):
    qualifications = Qualification.objects.all()
    submissions    = Assessment.objects.all().order_by("-created_at")

    if request.method == "POST":
        eisa_id = f"EISA-{uuid.uuid4().hex[:8].upper()}"
        qual_id  = request.POST.get("qualification")
        qualification_obj = get_object_or_404(Qualification, pk=qual_id)
        paper    = request.POST["paper_number"].strip()
        saqa     = request.POST["saqa_id"].strip()
        file     = request.FILES.get("file_input")
        memo     = request.FILES.get("memo_file")
        comment  = request.POST.get("comment_box","").strip()
        forward  = request.POST.get("forward_to_moderator") == "on"

        Assessment.objects.create(
            eisa_id=eisa_id,
            qualification=qualification_obj,
            paper=paper,
            saqa_id=saqa,
            file=file,
            memo=memo,
            comment=comment,
            forward_to_moderator=forward,
            created_by=request.user, 
        )

        messages.success(request, "Assessment uploaded successfully.")
        return redirect("upload_assessment")

    return render(request, "core/assessor-developer/upload_assessment.html", {
        "submissions":    submissions,
        "qualifications": qualifications,
    })


# ---------------------------------------
# 4) DRF endpoint: returns JSON (for AJAX)
# ---------------------------------------
from django.db import transaction


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
#This one is for the Assessor Developer Don't assume its a duplicate view_assessment!
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
 

# core/views.py


@login_required
# @staff_member_required
def moderator_developer_dashboard(request):
    pending = Assessment.objects.filter(
        status__in=["Pending", "Submitted to Moderator"]
    ).order_by("-created_at")

    forwarded = Assessment.objects.filter(
        status="Submitted to ETQA"
    ).order_by("-created_at")

    recent_fb = Feedback.objects.select_related("assessment") \
                                .order_by("-created_at")[:10]

    return render(request, "core/moderator/moderator_developer.html", {
        "pending_assessments":   pending,
        "forwarded_assessments": forwarded,
        "recent_feedback":       recent_fb,
    })


def moderate_assessment(request, eisa_id):
    # Fetch the assessment (raises 404 if not found)
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)

    if request.method == 'POST':
        # Read form inputs
        decision = request.POST.get('decision')
        notes    = request.POST.get('moderator_notes', '')

        # Save the moderator’s notes
        assessment.moderator_notes = notes

        # Toggle status for the QCTO flow
        if decision == 'approve':
            assessment.status = 'Submitted to QCTO'
        else:
            assessment.status = 'Returned for Changes'
        assessment.save()

        # Redirect back to your moderator-developer dashboard
        return redirect('moderator_developer')

    # GET: render the moderation form
    return render(
        request,
        'core/moderator/moderate_assessment.html',  # make sure this path matches your file location
        {'assessment': assessment}
    )

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
#not neccessary---not main
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
    """
    QCTO dashboard: list assessments submitted by the moderator for QCTO review.
    Only those with status 'Submitted to QCTO' appear here.
    """
    pending_assessments = Assessment.objects.filter(
        status="Submitted to QCTO"
    ).order_by("-created_at")
    return render(
        request,
        "core/qcto/qcto_dashboard.html",
        {"pending_assessments": pending_assessments}
    )

#@require_http_methods(["GET", "POST"])
def qcto_moderate_assessment(request, eisa_id):
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)

    # Ensure QCTO only handles "Submitted to QCTO"
    if assessment.status != "Submitted to QCTO":
        messages.error(request, "This assessment is not pending QCTO review.")
        return redirect("qcto_dashboard")

    if request.method == "POST":
        notes = request.POST.get("qcto_notes", "").strip()
        decision = request.POST.get("decision")  # 'approve' or 'reject'

        if decision == "approve":
            assessment.status = "Approved by QCTO"
            messages.success(request, f"{assessment.eisa_id} has been approved by QCTO.")
        elif decision == "reject":
            assessment.status = "Rejected"
            messages.success(request, f"{assessment.eisa_id} has been rejected.")
        else:
            messages.error(request, "Invalid decision.")
            return redirect("qcto_moderate_assessment", eisa_id=eisa_id)

        assessment.qcto_notes = notes
        assessment.save()
        return redirect("qcto_dashboard")

    # On GET, offer approve/reject choices
    return render(
        request,
        "core/qcto/qcto_moderate_assessment.html",
        {
            "assessment": assessment,
            "decision_choices": [
                ("approve", "Approve"),
                ("reject", "Reject"),
            ],
        }
    )

    # 1) QCTO Dashboard: list assessments submitted to ETQA
@require_http_methods(["GET"])
def qcto_dashboard(request):
    pending = Assessment.objects.filter(status="Submitted to ETQA").order_by("-created_at")
    return render(request, "core/qcto/qcto_dashboard.html", {"pending_assessments": pending})

# 2) QCTO Moderate Assessment: view + update status and notes
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def qcto_moderate_assessment(request, eisa_id):
    """
    QCTO review step: only handles assessments with status 'Submitted to QCTO'.
    On 'approve', status becomes 'Submitted to ETQA'; on 'reject', status becomes 'Rejected'.
    """
    assessment = get_object_or_404(Assessment, eisa_id=eisa_id)

    if assessment.status != "Submitted to QCTO":
        messages.error(request, "This assessment is not pending QCTO review.")
        return redirect("qcto_dashboard")

    if request.method == "POST":
        notes    = request.POST.get("qcto_notes", "").strip()
        decision = request.POST.get("decision")  # now 'approve' or 'reject'

        if decision == "approve":
            assessment.status = "Submitted to ETQA"
            messages.success(request, f"{assessment.eisa_id} approved and forwarded to ETQA.")
        elif decision == "reject":
            assessment.status = "Rejected"
            messages.success(request, f"{assessment.eisa_id} has been rejected.")
        else:
            messages.error(request, "Invalid decision.")
            return redirect("qcto_moderate_assessment", eisa_id=eisa_id)

        assessment.qcto_notes = notes
        assessment.save()
        return redirect("qcto_dashboard")

    # on GET, render the form
    return render(request, "core/qcto/qcto_moderate_assessment.html", {
        "assessment": assessment,
        "decision_choices": [
            ("approve", "Approve"),
            ("reject",  "Reject"),
        ],
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
@login_required
# @staff_member_required
def qcto_assessment_review(request):
    assessments = Assessment.objects.filter(status='Submitted to QCTO')
    return render(request,
                  'core/qcto/assessment_review.html',   # <-- properly quoted
                  {'assessments': assessments})




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

#______________________________________________________________________________________________________
#______________________________________________________________________________________________________
# Log-Out View_________________________________________________________________________________________
#______________________________________________________________________________________________________

 # LOGOUT VIEW
def custom_logout(request):
     logout(request)
     return redirect('custom_login')
#Creating Users

def register(request):
    if request.method == "POST":
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            # Build user but do not log in yet
            user = form.save(commit=False)
            user.role = 'default'               # Assign default role
            user.qualification = Qualification.objects.get(code='default')
            user.is_active = True
            user.is_staff = False               # Default users are not staff
            user.save()

            # Show success message and redirect to login
            messages.success(request, "Registered. Pending approval.")
            return redirect('custom_login')  # or 'login' if your URL is named that

    else:
        form = EmailRegistrationForm()

    return render(request, "core/login/login.html", {"form": form})

#****************************************************************************
#Default Page is added here...
def default_page(request):
    return render(request, 'core/login/awaiting_activation.html')
#****************************************************************************
#****************************************************************************
#####Approved assessments view for the paper to be easily pulled and used for other uses.
def approved_assessments_view(request):
    assessments = Assessment.objects.filter(status="Approved by ETQA").prefetch_related('generated_questions')
    return render(request, 'core/approved_assessments.html', {'assessments': assessments})
#########################################################################################################################
#ASSessment Progress tracker view
@login_required
def assessment_progress_tracker(request):
    archived_statuses = [
        "Approved by ETQA",
        "Rejected",
        "Submitted to ETQA",
        "Approved by Moderator",
        "Submitted to Moderator",
    ]

    assessments = Assessment.objects.filter(status__in=archived_statuses).order_by('-created_at')

    # Dynamically add the `currently_with` field to each assessment
    for a in assessments:
        a.currently_with = get_current_holder(a.status)

    return render(request, 'core/paper_tracking/assessment_progress_tracker.html', {
        'assessments': assessments,
    })

#View to get current holder of the paper 
def get_current_holder(status):
    mapping = {
        "Pending": "Assessor/Developer",
        "Submitted to Moderator": "Moderator",
        "Returned for Changes": "Assessor/Developer",
        "Approved by Moderator": "ETQA",
        "Submitted to ETQA": "ETQA",
        "Approved by ETQA": "Archived",
        "Rejected": "Archived",
    }
    return mapping.get(status, "Unknown")
#to summarise the tracker now tells us where the paper is and displays the approved papers so they can be pulled.

#Learner Assessment viewing view
#@login_required
def approved_assessments_for_learners (request):
    user_qualification = request.user.qualification
    assessments = Assessment.objects.filter(
        status="Approved by ETQA", #fetching from the 
        qualification=user_qualification
    ).prefetch_related('generated_questions', 'case_study')

    return render(request, 'learner/approved_assessments_by_qualification.html', {
        'assessments': assessments,
    })
#_____________________________________________________________________________________

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

@login_required
def etqa_dashboard(request):
    centers         = AssessmentCentre.objects.all()
    qualifications  = Qualification.objects.all()
    assessments_for_etqa = Assessment.objects.filter(status="Submitted to ETQA")

    # 1) Figure out which qualification we're working with
    selected_qualification = (
        request.GET.get('qualification_id')
        or request.POST.get('qualification')
        or ""
    )

    # 2) Always load the APPROVED assessments for that qualification
    approved_assessments = []
    if selected_qualification:
        approved_assessments = Assessment.objects.filter(
            qualification_id=selected_qualification,
            status="Approved by ETQA"
        )

    created_batch = None

    if request.method == 'POST':
        # 3) Simple presence check
        missing = [f for f in ('center','qualification','assessment','date','number_of_learners')
                   if f not in request.POST]
        if missing:
            return render(request, 'core/qcto/etqa_dashboard.html', {
                'centers': centers,
                'qualifications': qualifications,
                'selected_qualification': selected_qualification,
                'approved_assessments': approved_assessments,
                'assessments_for_etqa': assessments_for_etqa,
                'error': f'Missing: {missing[0]}'
            })

        # 4) Create the batch
        batch = Batch.objects.create(
            center_id           = request.POST['center'],
            qualification_id    = request.POST['qualification'],
            assessment_id       = request.POST['assessment'],
            assessment_date     = request.POST['date'],
            number_of_learners  = request.POST['number_of_learners'],
        )
        created_batch = batch
        # Note: no redirect here; we simply fall through and re-render

    return render(request, 'core/qcto/etqa_dashboard.html', {
        'centers': centers,
        'qualifications': qualifications,
        'selected_qualification': selected_qualification,
        'approved_assessments': approved_assessments,
        'assessments_for_etqa': assessments_for_etqa,
        'created_batch': created_batch,
    })


  

@login_required
def approve_by_etqa(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    assessment.status = "Approved by ETQA"
    assessment.save()
    return redirect('etqa_dashboard')

@login_required
def reject_by_etqa(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    assessment.status = "Rejected"
    assessment.save()
    return redirect('etqa_dashboard')


#_________________________________________________view for assessment centre_____________________________
def assessment_center_view(request):
    batches = Batch.objects.filter(submitted_to_center=True)
    return render(request, 'assessment_center.html', {'batches': batches})

def submit_to_center(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    batch.submitted_to_center = True
    batch.save()
    return redirect('etqa_dashboard')

#----------------------views students-------------------------------------------------------
# pull the assesment under a specific qualification that the studnet has enrolled
from django.db.models import Max
from .models import Assessment, ExamAnswer

@login_required
def student_dashboard(request):
    assessments = Assessment.objects.filter(
        status="Approved by ETQA"
    ).prefetch_related('generated_questions')

    assessment_data = []
    for assessment in assessments:
        attempt_count = ExamAnswer.objects.filter(
            question__assessment=assessment,
            user=request.user
        ).count()
        assessment_data.append({
            'assessment': assessment,
            'attempt': attempt_count
        })

    return render(request, 'core/student/dashboard.html', {
        'assessment_data': assessment_data,
    })






@login_required
def student_assessment(request, assessment_id):
    assessment = get_object_or_404(
        Assessment,
        id=assessment_id,
        status="Approved by ETQA"
    )

    # Count user's attempts on this assessment
    user_attempts = ExamAnswer.objects.filter(
        user=request.user,
        question__assessment=assessment
    ).values('attempt_number').distinct().count()

    if user_attempts >= 3:
        messages.error(request, "You've reached the maximum number of attempts (3).")
        return redirect('student_dashboard')

    generated_qs = assessment.generated_questions.all()

    if not generated_qs.exists():
        generated_qs = QuestionBankEntry.objects.filter(qualification=assessment.qualification)

    return render(request, "core/student/assessment.html", {
        "assessment": assessment,
        "generated_qs": generated_qs,
        "attempt_number": user_attempts + 1  # next attempt number
    })

from django.views.decorators.http import require_POST

#@require_POST
@login_required
def submit_exam(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Determine current attempt number
    current_attempt = ExamAnswer.objects.filter(
        user=request.user,
        question__assessment=assessment
    ).aggregate(max_attempt=models.Max('attempt_number'))['max_attempt'] or 0

    if current_attempt >= 3:
        messages.error(request, "You cannot submit again. You've reached the maximum attempts.")
        return redirect('student_dashboard')

    next_attempt = current_attempt + 1

    # Process answers for this attempt
    for question in assessment.generated_questions.all():
        answer_key = f'answer_{question.id}'
        answer_text = request.POST.get(answer_key, '').strip()
        if answer_text:
            ExamAnswer.objects.update_or_create(
                user=request.user,
                question=question,
                attempt_number=next_attempt,
                defaults={'answer_text': answer_text}
            )

    messages.success(request, f"Attempt {next_attempt} submitted successfully!")
    return redirect('student_dashboard')


@login_required
def student_results(request):
    return render(request, 'core/student/results.html')

login_required
def write_exam(request, assessment_id):
    # Fetch only if status is 'Approved by ETQA'
    assessment = get_object_or_404(Assessment, id=assessment_id, status="Approved by ETQA")

    # Get only the questions linked to this assessment
    generated_qs = GeneratedQuestion.objects.filter(assessment=assessment)

    return render(request, 'core/student/write_exam.html', {
        'assessment': assessment,
        'generated_qs': generated_qs,
        'attempt_number': 1  # or fetch from logic if attempts are tracked
    })



from utils import extract_text, extract_all_tables, extract_questions_with_metadata

def beta_paper_extractor(request):
    questions    = {}
    raw_text     = ""
    file_url     = None
    match_tables = []
    mcq_tables   = []

    if request.method == "POST":
        uploaded = request.FILES.get("paper")
        if uploaded and uploaded.name.lower().endswith(".docx"):
            # save file (if you still need file_url)
            fs   = FileSystemStorage()
            name = fs.save(uploaded.name, uploaded)
            file_url = fs.url(name)

            # plain text (you can keep this or drop it)
            raw_text = extract_text(uploaded, uploaded.content_type)

            # if you still want the separate match/MCQ tables:
            uploaded.seek(0)
            table_data   = extract_all_tables(uploaded)
            match_tables = table_data.get("match_tables", [])
            mcq_tables   = table_data.get("mcq_tables", [])

            # **NEW** structured extraction:
            uploaded.seek(0)
            questions = extract_questions_with_metadata(uploaded)

    return render(request, "core/administrator/beta_paper_extractor.html", {
        "raw_text":     raw_text,
        "file_url":     file_url,
        "match_tables": match_tables,
        "mcq_tables":   mcq_tables,
        "questions":    questions,      # now a dict keyed by question number
    })


# …make sure you’ve already got:
# from google import genai
# from django.conf import settings
# genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

@csrf_exempt
@require_POST
def clean_questions(request):
    """
    POST JSON: { "questions": [ "...", ... ] }
    Returns   JSON: { "cleaned": [ true, false, ... ] }
    """
    try:
        payload = json.loads(request.body)
        qs      = payload.get("questions", [])
        if not isinstance(qs, list):
            return JsonResponse({"error": "`questions` must be an array"}, status=400)

        system_prompt = (
            "You will receive a JSON list of question texts. "
            "Return ONLY a JSON object {\"cleaned\": [...]}, where each entry is "
            "`true` if that text is a real exam question or `false` otherwise."
        )

        resp = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[system_prompt, json.dumps(qs)]
        )
        raw = (resp.text or "").strip()

        if not raw:
            flags = [True] * len(qs)
        else:
            try:
                data = json.loads(raw)
                flags = data.get("cleaned") or data.get("valid")
                if not isinstance(flags, list) or len(flags) != len(qs):
                    raise ValueError(f"Bad format/length: {flags}")
            except Exception:
                flags = [True] * len(qs)

        return JsonResponse({"cleaned": flags})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc().splitlines()[:5]
        }, status=500)

#Imports close to functions to makesure import order does not impede the functions.
from django.shortcuts import redirect, render
from .models import QuestionBankEntry
from django.contrib import messages

def save_extracted_questions(request):
    if request.method == 'POST':
        counter = 1
        questions_to_save = []

        while f"question_{counter}" in request.POST:
            number = request.POST.get(f"number_{counter}")
            question = request.POST.get(f"question_{counter}")
            marks = request.POST.get(f"marks_{counter}")
            status = request.POST.get(f"status_{counter}")
            case_study = request.POST.get(f"case_study_{counter}")

            if question and number:
                entry = QuestionBankEntry(
                    number=number,
                    text=question,
                    marks=int(marks) if marks else 0,
                    status=status,
                    case_study=case_study or ''
                )
                questions_to_save.append(entry)
            counter += 1

        # Bulk save
        QuestionBankEntry.objects.bulk_create(questions_to_save)
        messages.success(request, f"{len(questions_to_save)} questions saved successfully.")
        return redirect('beta_paper')  # replace with your actual view name

    return redirect('beta_paper')



from django.shortcuts import render
from utils import extract_all_tables

def beta_paper_tables_view(request):
    tables = {}
    if request.method == "POST":
        uploaded = request.FILES.get("paper")
        if uploaded and uploaded.name.endswith(".docx"):
            tables = extract_all_tables(uploaded)
    return render(request, "core/administrator/extracted_tables.html", {"tables": tables})

# core/views.py









import json
from django.shortcuts  import get_object_or_404, render, redirect
from django.contrib    import messages
from django.db         import transaction
from django.views.decorators.http import require_POST
from .models           import Qualification, Paper, ExamNode
from utils             import extract_full_docx_structure
from add_ids           import ensure_ids
import uuid

def paper_as_is_view(request, paper_pk=None):
    """
    • GET  (no pk) → show upload form
    • POST (no pk) → save .docx, create a Paper, redirect to /…/<paper_pk>/
    • GET  (with pk) → show the pre-parsed blocks for manual editing
    """
    # — POST with file and no paper_pk → create & redirect
    if request.method == "POST" and request.FILES.get("paper") and paper_pk is None:
        # form inputs
        paper_number     = (request.POST.get("paper_number") or "").strip() or "1A"
        qualification_id = (request.POST.get("qualification_id") or "").strip()
        qualification = (
            Qualification.objects.filter(code=qualification_id).first()
            or Qualification.objects.filter(saqa_id=qualification_id).first()
        )

        # create the Paper row
        paper = Paper.objects.create(
            name          = paper_number,
            qualification = qualification,
            total_marks   = 0,
        )

        # parse the DOCX into a nested dict-list
        blocks    = extract_full_docx_structure(request.FILES["paper"])
        questions = _flatten_structure(blocks)
        ensure_ids(questions)

        # update total_marks
        paper.total_marks = sum(int(q.get("marks") or 0) for q in _walk(questions))
        paper.save(update_fields=["total_marks"])

        # stash the blocks in the session so that the GET can pick them up
        request.session[f"paper_{paper.pk}_questions"] = questions

        return redirect("review_paper", paper_pk=paper.pk)

    # — GET with paper_pk → pull questions from session (or re-parse from file if you saved it)
    questions = []
    paper     = None
    if paper_pk is not None:
        paper     = get_object_or_404(Paper, pk=paper_pk)
        questions = request.session.get(f"paper_{paper_pk}_questions", [])

    return render(request,
                  "core/administrator/review_paper.html",
                  {"questions": questions, "paper": paper})


def _flatten_structure(qs):
    flattened = []
    for q in qs:
        flattened.append({
            "id":       q.get("id"),              # make sure ensure_ids ran
            "type":     q.get("type", ""),
            "number":   q.get("number", ""),
            "marks":    q.get("marks", ""),
            "text":     q.get("text", ""),
            "content":  q.get("content", []),
            "children": _flatten_structure(q.get("children", [])),
            **({"data_uri": q["data_uri"]} if q.get("type") == "figure" else {}),
        })
    return flattened

def _walk(nodes):
    for n in nodes:
        yield n
        yield from _walk(n.get("children", []))


@require_POST
def save_blocks(request, paper_pk):
    print("SAVE BLOCKS TRIGGERED")
    print(request.POST.get("nodes_json", ""))

    raw = request.POST.get("nodes_json", "")
    if not raw:
        messages.error(request, "Nothing to save – no data received.")
        return redirect("review_paper", paper_pk=paper_pk)

    try:
        nodes = json.loads(raw)
    except json.JSONDecodeError:
        messages.error(request, "Malformed data – cannot decode JSON.")
        return redirect("review_paper", paper_pk=paper_pk)

    # Normalize and ensure all node IDs are valid strings
    for n in nodes:
        if not n.get("id") or n["id"] in ["None", "", None]:
            n["id"] = uuid.uuid4().hex
        else:
            n["id"] = str(n["id"]).replace("-", "")[:32]

        # Clean parent_id the same way
        if n.get("parent_id"):
            n["parent_id"] = str(n["parent_id"]).replace("-", "")[:32]

    paper = get_object_or_404(Paper, pk=paper_pk)

    with transaction.atomic():
        id_to_node = {}

        # First: create/update each node without parent
        for n in nodes:
            node, _ = ExamNode.objects.update_or_create(
                id=n["id"],
                defaults={
                    "number":    n.get("number", ""),
                    "marks":     n.get("marks", ""),
                    "node_type": n.get("type", ""),
                    "payload":   n,
                    
                },
            )
            id_to_node[n["id"]] = node

        # Second: assign parent-child relationships
        for n in nodes:
            parent_id = n.get("parent_id")
            if parent_id and parent_id in id_to_node:
                node = id_to_node[n["id"]]
                parent = id_to_node[parent_id]
                node.parent = parent
                node.save(update_fields=["parent"])

    messages.success(request, "Manual edits saved.")
    return redirect("review_paper", paper_pk=paper_pk)




import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from google import genai

# Initialize your gemini client (ensure you've set up api key)
# from google import genai_client
# genai_client = genai.GeminiClient()

@require_POST
@csrf_exempt
def auto_fix_blocks(request):
    """
    Accepts JSON {blocks: [...]}. Returns JSON {fixes: [...]} with suggested corrections
    for 'mark', 'type', 'text' or 'rows' fields in each block.
    """
    try:
        payload = json.loads(request.body)
        blocks = payload.get('blocks', [])
        system_prompt = (
            "You are an exam formatting assistant. Each block has fields 'type', 'text', 'mark', and optionally 'rows'.\n"
            "Analyze each block and correct any misplaced marks, refine the type if needed, adjust text formatting, and ensure tables ('rows') stay intact.\n"
            "Respond with JSON {'fixes': [...]} where each entry matches the input blocks and may include updated 'mark', 'type', 'text', and 'rows'."
        )
        # Call Gemini
        resp = genai_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[system_prompt, json.dumps(blocks)]
        )
        data = json.loads((resp.text or '').strip())
        fixes = data.get('fixes', [])
        if not isinstance(fixes, list) or len(fixes) != len(blocks):
            raise ValueError("Invalid fixes format")
    except Exception:
        # Fallback: echo original fields
        fixes = []
        for blk in blocks:
            fixes.append({
                'mark': blk.get('mark', ''),
                'type': blk.get('type', ''),
                'text': blk.get('text', ''),
                'rows': blk.get('rows', []),
            })
    return JsonResponse({'fixes': fixes})

@require_POST
@csrf_exempt
def auto_place_marks(request):
    """
    Accepts JSON {blocks: [...]}. Extracts marks from text if present
    and returns JSON {marks: [...]} aligned by index.
    """
    try:
        payload = json.loads(request.body)
        blocks = payload.get('blocks', [])
        system_prompt = (
            "You are an exam parsing assistant. Each block may contain a marks notation like '(5 marks)' or 'x 10'.\n"
            "Extract the correct mark value for each block and return JSON {'marks': [...]} aligned to input indices."
        )
        resp = genai_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[system_prompt, json.dumps(blocks)]
        )
        data = json.loads((resp.text or '').strip())
        marks = data.get('marks', [])
        if not isinstance(marks, list) or len(marks) != len(blocks):
            raise ValueError("Invalid marks format")
    except Exception:
        marks = [blk.get('mark', '') for blk in blocks]
    return JsonResponse({'marks': marks})




# core/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

@require_POST
def auto_classify_blocks(request, paper_pk):
    """
    AJAX helper – receives the current blocks as JSON, runs your AI classifier,
    returns the enriched blocks back to the browser.

    For now we just echo the payload so the route exists and Django can import it.
    """
    try:
        nodes = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid JSON")

    # ───── TODO: call your ML model here and mutate `nodes` as needed ─────
    # for n in nodes:
    #     n["marks"] = my_classifier.predict(n["text"])

    return JsonResponse(nodes, safe=False)
