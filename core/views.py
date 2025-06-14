import traceback
from django.contrib import messages
from rest_framework.parsers import MultiPartParser, JSONParser
from .forms import QualificationForm
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from .models import QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion
import json
import random
import time
import re
from .models import MCQOption
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
from .utils import extract_text
from .models import Assessment, GeneratedQuestion, QuestionBankEntry, CaseStudy, Feedback
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
from django.contrib.auth.admin import UserAdmin
from .models import AssessmentCentre
from .forms import AssessmentCentreForm, QualificationForm
from .models import (
    QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion,
    Qualification, CustomUser, AssessmentCentre, Feedback
)
from .forms import QualificationForm, AssessmentCentreForm, CustomUserForm
from .question_bank import QUESTION_BANK
from .utils import extract_text
from google import genai
from django.conf import settings

# Initialize AI client
genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)


#Custom User
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active']
    ordering = ['-created_at']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'qualification', 'activated_at', 'deactivated_at')}),
    )

admin.site.register(Qualification)


def custom_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)

            role = user.role
            if role == 'admin':
                return redirect('admin_dashboard')
            elif role == 'moderator':
                return redirect('moderator_developer')  # NOTE: corrected to match your URL name
            elif role == 'internal_mod':
                return redirect('internal_moderator_dashboard')
            elif role == 'assessor_dev':
                return redirect('assessor_dashboard')  # fallback to existing view
            elif role == 'assessor_marker':
                return redirect('assessor_dashboard')  # fallback
            elif role == 'etqa':
                return redirect('qcto_dashboard')  # assuming qcto serves as etqa too
            elif role == 'qcto':
                return redirect('qcto_dashboard')
            elif role == 'learner':
                # No learner_dashboard defined yet, fallback or comment
                return redirect('home')  # or comment this line out
                # pass  # optionally just do nothing or show 403

        return render(request, 'core/login/login.html', {'error': 'Invalid credentials'})

    return render(request, 'core/login/login.html')
#_______________________________________________________________________________________________________
#******************************************************************************************************
#LOGIN LOGIC AND USER ACCESS CONTROL STARTS HERE********************************************************
#*******************************************************************************************************
#*******************************************************************************************************
@login_required
@staff_member_required
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

        # split name
        parts = name.split()
        first = parts[0]
        last  = " ".join(parts[1:]) if len(parts)>1 else ""

        # random password
        pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # actual user creation
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            first_name=first,
            last_name=last,
            role=role,
            qualification=qualification,
            is_active=True,
            activated_at=now()
        )
        user.set_password(pwd)
        user.save()

        # email it
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
@staff_member_required
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
@staff_member_required
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
@staff_member_required
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
@staff_member_required
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
        qualification_code = request.POST.get('qualification')
        marks = request.POST.get('marks')
        text = request.POST.get('text')

        # Fetch qualification object
        try:
            qualification = Qualification.objects.get(code=qualification_code)
        except Qualification.DoesNotExist:
            messages.error(request, "Selected qualification does not exist.")
            return redirect('generate_tool_page')

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
        return redirect('generate_tool_page')

@csrf_exempt
def add_case_study(request):
    if request.method == 'POST':
        title = request.POST.get('cs_title')
        content = request.POST.get('cs_content')
        if title and content:
            CaseStudy.objects.create(title=title, content=content)
            messages.success(request, "Case study added successfully.")
    return redirect('generate_tool_page')



#Critical
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
@staff_member_required
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


@require_http_methods(["GET", "POST"])
@staff_member_required
def moderate_assessment(request, eisa_id):
    a = get_object_or_404(Assessment, eisa_id=eisa_id)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        notes  = request.POST.get("moderator_notes", "").strip()

        if action == "forward":
            # Forward to ETQA
            a.status = "Submitted to ETQA"
            a.moderator_notes = notes
            a.save()
            messages.success(request, f"{a.eisa_id} successfully forwarded to QCTO.")
            return redirect("moderator_developer")

        # Otherwise treat as status change
        new_status = action or request.POST.get("status")
        valid = dict(Assessment.STATUS_CHOICES)
        if new_status not in valid:
            messages.error(request, "Invalid status.")
        else:
            a.status = new_status
            a.moderator_notes = notes
            a.save()
            messages.success(request, f"{a.eisa_id} updated to “{new_status}.”")
        return redirect("moderator_developer")

    return render(request, "core/moderator/moderate_assessment.html", {
        "assessment":     a,
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

#______________________________________________________________________________________________________
#______________________________________________________________________________________________________
# Log-Out View_________________________________________________________________________________________
#______________________________________________________________________________________________________

 # LOGOUT VIEW
def custom_logout(request):
     logout(request)
     return redirect('custom_login')
