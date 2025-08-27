import os
import traceback
from django.contrib import messages

from .paper_forwarding import S_TO_ASSESSOR, S_TO_ETQA
from rest_framework.parsers import MultiPartParser, JSONParser
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import Assessment, GeneratedQuestion, Batch, AssessmentCentre, ExamNode
import json
import random
from django.db import models
from django.urls import reverse
import time 
import re
from django.db import IntegrityError
from .forms import EmailRegistrationForm
import uuid
import csv

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
from .models import Qualification, CustomUser, Paper
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import QuestionBankEntry, Assessment
import random
from .forms import QualificationForm
from django.db.models import Sum
from utils import populate_examnodes_from_structure_json, save_nodes_to_db
from .forms import CustomUserForm
from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .forms import AssessmentCentreForm
from .models import (
    QuestionBankEntry, CaseStudy, Assessment, GeneratedQuestion,
    Qualification, CustomUser, AssessmentCentre, Feedback)

from .forms import AssessmentCentreForm, CustomUserForm
from .question_bank import QUESTION_BANK
from google import genai
from django.conf import settings
from django.contrib.auth import get_user_model
from robustexamextractor import save_robust_extraction_to_db, extract_docx


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
    elif role == 'assessor_dev':
        return redirect('assessor_dashboard')
    elif role == 'qcto':
        return redirect('qcto_dashboard')
    elif role == 'etqa':
        return redirect('etqa_dashboard')
    elif role == 'learner':
        return redirect('student_dashboard')
    else:
        return redirect('home')
    
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, NoReverseMatch
from .models import Assessment

def assessment_detail(request, pk):
    a = get_object_or_404(Assessment, pk=pk)

    # Try legacy route if it exists *and* we have an eisa_id
    try:
        if getattr(a, "eisa_id", None):
            return redirect(reverse("view_assessment", args=[a.eisa_id]))
    except NoReverseMatch:
        pass  # fall through to fallback

    # Collect likely content fields (robust to naming differences)
    ctx = {
        "assessment": a,
        "paper": a,  # alias for older partials
        "paper_json": getattr(a, "structure_json", None) or getattr(a, "extracted_json", None),
        "paper_text": getattr(a, "extracted_text", None) or getattr(a, "paper_text", None),
        "paper_file": getattr(a, "file", None) or getattr(a, "paper_file", None),
        "memo_text": getattr(a, "memo_text", None) or getattr(a, "extracted_memo_text", None),
        "memo_file": getattr(a, "memo_file", None),
    }
    return render(request, "core/assessment_detail_fallback.html", ctx)


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


from uuid import uuid4
from django.shortcuts            import render, redirect, get_object_or_404
from django.contrib              import messages
from django.contrib.auth.decorators import login_required

from .models     import (
    Qualification, Paper, Assessment,
    CustomUser
)
from utils      import (
    extract_full_docx_structure)



#Helper Function
# --- robust helpers (safe defaults) ---------------------------------
MARK_RE = re.compile(r'(\d+)\s*(?:mark|marks)\b', re.I)

def extract_marks_from_text(text: str) -> int:
    if not text:
        return 0
    m = MARK_RE.findall(text)
    if m:
        # take the last number in the line like "(10 Marks)"
        try:
            return int(m[-1])
        except ValueError:
            return 0
    # bare numbers at the end e.g. "... [5]"
    tail = re.findall(r'(\d+)\s*$', text)
    return int(tail[-1]) if tail else 0

def extract_node_text_from_robust(node: dict) -> str:
    # prefer explicit text field
    if isinstance(node.get('text'), str):
        return node['text']
    # try content array
    parts = []
    for item in node.get('content', []):
        if isinstance(item, dict):
            if 'text' in item and isinstance(item['text'], str):
                parts.append(item['text'])
            # table text flatten (header + cells)
            if item.get('type') == 'table':
                t = item.get('table', {})
                for row in t.get('rows', []):
                    for cell in row.get('cells', []):
                        ct = cell.get('text', '')
                        if ct:
                            parts.append(ct)
    return ' '.join(p.strip() for p in parts if p)

def extract_marks_from_robust_data(node: dict) -> int:
    # explicit marks first
    val = node.get('marks')
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        nums = re.findall(r'\d+', val)
        return int(nums[0]) if nums else 0
    # fall back to text/content
    return extract_marks_from_text(extract_node_text_from_robust(node))

def handle_robust_image_content(node: dict, paper_obj) -> list:
    """
    Placeholder: return lightweight descriptors only.
    If you later persist files, do it here and return stored paths.
    """
    meta = node.get('image') or {}
    # Avoid dumping heavy/binary data into JSONField
    cleaned = {
        k: v for k, v in meta.items()
        if isinstance(v, (str, int, float, bool)) or v is None
    }
    return [cleaned] if cleaned else []
# --------------------------------------------------------------------

def save_robust_manifest_to_db(nodes, paper_obj):
    """Save robust extraction nodes to database with better content handling"""
    try:
        # Track mapping from node numbers to DB records
        node_map = {}
        order_index = 0
        
        # First pass: create all nodes
        for node_data in nodes:
            # Extract basic node data
            node_type = node_data.get('type', 'unknown')
            node_number = node_data.get('number', '')
            node_text = node_data.get('text', '')
            node_marks = node_data.get('marks', '')
            
            # Process content properly based on type
            content_items = []
            
            # Handle content items
            for item in node_data.get('content', []):
                if isinstance(item, dict):
                    # Handle table content
                    if item.get('type') == 'table' and 'rows' in item:
                        content_items.append({
                            'type': 'table',
                            'rows': item['rows']
                        })
                    # Handle image content
                    elif item.get('type') == 'figure':
                        image_data = {}
                        if 'images' in item:
                            image_data['images'] = item['images']
                        if 'data_uri' in item:
                            image_data['data_uri'] = item['data_uri']
                        content_items.append({
                            'type': 'figure',
                            **image_data
                        })
                    # Other content
                    else:
                        content_items.append(item)
            
            # Create the node
            node = ExamNode.objects.create(
                paper=paper_obj,
                node_type=node_type,
                number=node_number,
                text=node_text,
                marks=node_marks,
                content=content_items,  # Store as proper JSON
                order_index=order_index
            )
            
            # Track in map for parent relationships
            if node_number:
                node_map[node_number] = node
                
            order_index += 1
            
        # Second pass: establish parent-child relationships
        for node_data in nodes:
            node_number = node_data.get('number', '')
            if not node_number or node_number not in node_map:
                continue
                
            # Find parent if exists
            parts = node_number.split('.')
            if len(parts) > 1:
                parent_number = '.'.join(parts[:-1])
                if parent_number in node_map:
                    node = node_map[node_number]
                    node.parent = node_map[parent_number]
                    node.save()
                    
        return True
        
    except Exception as e:
        print(f"Error saving manifest to DB: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def find_marks_in_following_tables(nodes, current_index):
    """Algorithm to find marks in following table nodes - handles your specific case"""
    print(f"🔍 Looking for marks in tables following node {current_index}")
    
    # Look at the next few nodes for tables
    for i in range(current_index + 1, min(current_index + 5, len(nodes))):
        next_node = nodes[i]
        
        # Stop if we hit another question (marks belong to previous question)
        if next_node.get('type') == 'question':
            break
            
        # Check if this is a table with marks
        if next_node.get('type') == 'table':
            table_marks = extract_marks_from_table_content(next_node)
            if table_marks > 0:
                print(f"✅ Found {table_marks} marks in following table at index {i}")
                return table_marks
    
    print(f"❌ No marks found in following tables")
    return 0

def extract_marks_from_table_content(node_data):
    """Extract marks from table content in node_data"""
    try:
        # Look through content array for tables
        for content_item in node_data.get('content', []):
            if content_item.get('type') == 'table':
                marks = extract_marks_from_table(content_item)
                if marks > 0:
                    return marks
        
        # Fallback: look for marks in the raw text
        text = extract_node_text_from_robust(node_data)
        return extract_marks_from_text(text)
        
    except Exception as e:
        print(f"⚠️ Error extracting marks from table content: {e}")
        return 0

# Enhanced marks extraction with better table parsing
def extract_marks_from_table(table_item):
    """Extract marks from table structure - enhanced for your specific format"""
    try:
        table_data = table_item.get('table', {})
        rows = table_data.get('rows', [])
        
        print(f"🔍 Analyzing table with {len(rows)} rows")
        
        # Strategy 1: Look for "Total" row
        for row_idx, row in enumerate(rows):
            cells = row.get('cells', [])
            
            if len(cells) > 0:
                first_cell_text = cells[0].get('text', '').strip().lower()
                
                if 'total' in first_cell_text:
                    print(f"📊 Found total row at index {row_idx}")
                    
                    # Look for number in any cell of this row
                    for cell_idx, cell in enumerate(cells):
                        cell_text = cell.get('text', '').strip()
                        print(f"   Cell {cell_idx}: '{cell_text}'")
                        
                        # Direct number
                        if cell_text.isdigit():
                            marks = int(cell_text)
                            print(f"✅ Found marks: {marks}")
                            return marks
                        
                        # Extract numbers from text
                        numbers = re.findall(r'\d+', cell_text)
                        if numbers:
                            marks = int(numbers[-1])
                            print(f"✅ Extracted marks from '{cell_text}': {marks}")
                            return marks
        
        # Strategy 2: Look for "Marks" column and sum individual marks
        marks_column_index = None
        
        # Find the marks column
        for row_idx, row in enumerate(rows):
            cells = row.get('cells', [])
            for col_idx, cell in enumerate(cells):
                cell_text = cell.get('text', '').strip().lower()
                if 'marks' in cell_text or 'mark' in cell_text:
                    marks_column_index = col_idx
                    print(f"📊 Found marks column at index {col_idx}")
                    break
            if marks_column_index is not None:
                break
        
        # Sum marks from the marks column
        if marks_column_index is not None:
            total_marks = 0
            for row_idx, row in enumerate(rows[1:], 1):  # Skip header
                cells = row.get('cells', [])
                if len(cells) > marks_column_index:
                    cell_text = cells[marks_column_index].get('text', '').strip()
                    
                    # Skip the "Total" row itself
                    first_cell = cells[0].get('text', '').strip().lower()
                    if 'total' in first_cell:
                        continue
                    
                    if cell_text.isdigit():
                        marks_value = int(cell_text)
                        total_marks += marks_value
                        print(f"   Row {row_idx}: +{marks_value} marks")
            
            if total_marks > 0:
                print(f"✅ Calculated total marks: {total_marks}")
                return total_marks
        
        # Strategy 3: Look for patterns in all cell text
        all_text = []
        for row in rows:
            for cell in row.get('cells', []):
                all_text.append(cell.get('text', ''))
        
        combined_text = ' '.join(all_text)
        text_marks = extract_marks_from_text(combined_text)
        if text_marks > 0:
            print(f"✅ Found marks in combined text: {text_marks}")
            return text_marks
                
    except Exception as e:
        print(f"⚠️ Error extracting marks from table: {e}")
        
    return 0

# Enhanced admin dashboard calculation
def calculate_total_marks_from_manifest(nodes):
    """Enhanced marks calculation that looks at following tables"""
    total_marks = 0
    
    for i, node in enumerate(nodes):
        if node.get('type') == 'question':
            # Try direct extraction first
            extracted_marks = extract_marks_from_robust_data(node)
            
            # If no marks found, look in following tables
            if extracted_marks == 0:
                extracted_marks = find_marks_in_following_tables(nodes, i)
            
            total_marks += extracted_marks
            
            if extracted_marks > 0:
                question_num = node.get('number', 'Unknown')
                print(f"📝 Q{question_num}: {extracted_marks} marks")
    
    print(f"💯 Total calculated marks: {total_marks}")
    return total_marks

# core/views.py (near your other helpers)
def build_questions_tree_for_paper(paper):
    nodes = list(
        ExamNode.objects.filter(paper=paper)
        .select_related('parent')
        .order_by('order_index')
    )

    questions = []
    node_map = {}

    # pass 1: shape dicts
    for node in nodes:
        node_dict = {
            'id': str(node.id),
            'type': node.node_type,
            'number': node.number or '',
            'text': node.text or '',
            'marks': node.marks or '',
            'content': node.content or [],   # keep JSON as-is
            'children': []
        }
        node_map[str(node.id)] = node_dict
        if node.node_type == 'question':
            questions.append(node_dict)

    # pass 2: wire parents/children
    for node in nodes:
        if node.parent and str(node.parent.id) in node_map:
            parent_dict = node_map[str(node.parent.id)]
            child_dict  = node_map[str(node.id)]
            parent_dict['children'].append(child_dict)

    return questions

#===================================================================================

@login_required
def admin_dashboard(request):
    """Administrator dashboard view - handles file uploads and paper selection"""

    # Handle file upload
    if request.method == 'POST' and request.FILES.get('file_input'):
        file_obj = request.FILES['file_input']
        paper_number = request.POST.get('paper_number', 'Unnamed Paper')
        qual_pk = (request.POST.get('qualification') or '').strip()
        if not qual_pk:
            messages.error(request, "Please select a qualification.")
            return redirect('admin_dashboard')
        try:
            qualification_obj = Qualification.objects.get(pk=int(qual_pk))
        except (ValueError, Qualification.DoesNotExist):
            messages.error(request, "Invalid qualification selected.")
            return redirect('admin_dashboard')

        # Create temp directory
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)

        # Create a unique filename for this upload
        unique_filename = f"upload_{uuid.uuid4().hex}.docx"
        temp_path = os.path.join(temp_dir, unique_filename)

        # DEBUG: Print file information
        print(f"📄 Processing file: {file_obj.name} ({file_obj.size} bytes)")

        # Write file to disk
        with open(temp_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        # After writing file to disk
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            print("❌ ERROR: File was saved with 0 bytes!")
        else:
            print(f"✅ File saved with {file_size} bytes")

        # Process the document - ENSURE THIS RUNS
        print("🔍 Starting robust extraction...")
        manifest = extract_docx(
            temp_path,
            out_dir=None,
            use_gemini=False,
            use_gemma=False
        )

        # DEBUG: Check manifest structure
        node_count = len(manifest.get('nodes', []))
        print(f"📊 Extraction found {node_count} nodes")

        # After extraction
        if not manifest:
            print("❌ Extraction returned None!")
        elif not manifest.get('nodes'):
            print("❌ Extraction returned no nodes!")
        else:
            print(f"✅ Extraction found {len(manifest['nodes'])} nodes")
            # Print first node structure
            if manifest['nodes']:
                print(f"First node: {manifest['nodes'][0]}")

        if not manifest or 'nodes' not in manifest or not manifest['nodes']:
            messages.error(request, "Extraction failed: No content found in document")
            return redirect('admin_dashboard')

        # Create paper object
        paper_obj = Paper.objects.create(
            name=paper_number,
            qualification=qualification_obj,
            created_by=request.user,
            is_randomized=False
        )
############################################################################
############################################################################
############################################################################
            #Our Eisa tools are here
        Assessment.objects.create(
            qualification=qualification_obj,
            paper=paper_number,
            file=file_obj,           # the uploaded Word file
            created_by=request.user,
            paper_link=paper_obj,
            status="Pending"         # The initial status in the pipeline
)############################################################################
#############################################################################
#############################################################################
#############################################################################
        


        # CRITICAL: Save extracted content to database
        print("💾 Saving nodes to database...")
        conversion_success = save_robust_manifest_to_db(manifest['nodes'], paper_obj)

        if not conversion_success:
            messages.error(request, "Failed to save extracted content to database")
            paper_obj.delete()  # Clean up failed paper
            return redirect('admin_dashboard')

        # Count extracted elements
        questions = sum(1 for n in manifest['nodes'] if n.get('type') == 'question')
        tables = sum(1 for n in manifest['nodes'] for c in n.get('content', [])
                     if isinstance(c, dict) and c.get('type') == 'table')
        images = sum(1 for n in manifest['nodes'] for c in n.get('content', [])
                     if isinstance(c, dict) and c.get('type') == 'figure')

        # Calculate total marks
        total_marks = sum(
            int(node.get('marks', 0) or 0)
            for node in manifest['nodes']
            if node.get('type') == 'question' and node.get('marks')
        )

        # Update paper with marks
        paper_obj.total_marks = total_marks
        paper_obj.save()

        messages.success(request,
            f"🎉 EXTRACTION SUCCESS!\n"
            f"📝 {questions} questions extracted\n"
            f"📊 {tables} tables preserved\n"
            f"🖼️ {images} images captured\n"
            f"💯 {total_marks} total marks calculated"
        )

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass

        tools = Assessment.objects.select_related("qualification", "created_by").order_by("-created_at")


        # Redirect to paper review page
        return redirect('load_saved_paper', paper_pk=paper_obj.id)

   
    tools = Assessment.objects.select_related("qualification", "created_by")\
                             .order_by("-created_at")
    total_users = CustomUser.objects.filter(is_superuser=False).count()
    quals = Qualification.objects.all()

    return render(request, "core/administrator/admin_dashboard.html", {
        "tools": tools,
        "total_users": total_users,
        "qualifications": quals,
    })
#_____________________________________________________________________________________________________


#_____________________________________________________________________________________________________
def qualification_management_view(request):
    qualifications = Qualification.objects.all()
    form = QualificationForm()

    if request.method == 'POST':
        form = QualificationForm(request.POST)
        print (request.POST)
        if form.is_valid():
            print ("form is saving")
            form.save()
            messages.success(request, "Qualification added successfully.")
            return redirect('manage_qualifications')
        else:
            print("Form errors:", form.errors)  
            messages.error(request, "Please correct the errors below.")

    return render(request, 'core/administrator/qualifications.html', {
        'qualifications': qualifications,
        'form': form,
    })

#0) Databank View 2025/06/10 made to handle logic for the databank for the question generation.

def databank_view(request):
    # Get questions from ExamNode
    entries = ExamNode.objects.filter(
        node_type='question'
    ).select_related(
        'paper__qualification'
    ).order_by('-created_at')

    return render(request, "core/administrator/databank.html", {
        "entries": entries,
        "qualifications": Qualification.objects.all(),
    })

# -------------------------------------------
# 1) Add a new question to the Question Bank
# ---------------------------------------

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

            qualification = Qualification.objects.filter(id=qual).first()
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
                status="pending"
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
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.models import Assessment, Qualification, Paper
from utils import (extract_full_docx_structure, ensure_ids, auto_classify_blocks_with_gemini)
import uuid

@require_http_methods(["GET", "POST"])
def upload_assessment(request):
    """Enhanced upload using robust extractor"""
    qualifications = Qualification.objects.all()
    submissions = Assessment.objects.all().order_by("-created_at")

    if request.method == "POST":
        eisa_id = f"EISA-{uuid.uuid4().hex[:8].upper()}"
        qual_id = request.POST.get("qualification")
        qualification_obj = get_object_or_404(Qualification, pk=qual_id)

        paper_number = request.POST["paper_number"].strip()
        saqa = request.POST["saqa_id"].strip()
        file = request.FILES.get("file_input") 
        memo = request.FILES.get("memo_file")
        comment = request.POST.get("comment_box", "").strip()
        forward = request.POST.get("forward_to_moderator") == "on"

        if file and file.name.endswith(".docx"):
            try:
                print("🚀 Using ROBUST EXTRACTOR with database integration...")
                
                # Use the robust extractor function - ONE CALL DOES EVERYTHING!
                paper_obj = save_robust_extraction_to_db(
                    docx_file=file,
                    paper_name=paper_number,
                    qualification=qualification_obj,
                    user=request.user,
                    use_gemini=False,  # Disable due to API issues
                    use_gemma=False    # Disable due to memory issues
                )
                
                # 
                if paper_obj and hasattr(paper_obj, 'extract_dir'):
                    from utils import copy_images_to_media_folder
                    media_dir = os.path.join(paper_obj.extract_dir, "media")
                    copy_images_to_media_folder(media_dir)
                    print("Copying images from temp media folder:", media_dir)


                
                if paper_obj:
                    # Create RAW assessment (uploaded docx itself) → goes straight to ETQA
                    raw_assessment = Assessment.objects.create(
                        eisa_id=f"EISA-{uuid.uuid4().hex[:8].upper()}",
                        qualification=qualification_obj,
                        paper=paper_number,
                        saqa_id=saqa,
                        file=file,          # original uploaded .docx
                        memo=memo,
                        comment=comment,
                        created_by=request.user,
                        status=S_TO_ETQA

                    )

                    # Create EXTRACTED assessment (linked to structured Paper) → starts pipeline
                    extracted_assessment = Assessment.objects.create(
                        eisa_id=f"EISA-{uuid.uuid4().hex[:8].upper()}",
                        qualification=qualification_obj,
                        paper=f"{paper_number} (Extracted)",
                        saqa_id=saqa,
                        created_by=request.user,
                        paper_link=paper_obj,   # link to extracted Paper + ExamNodes
                        status=S_TO_ASSESSOR  # ✅ pipeline starts here

                    )


                    # Count what was extracted
                    nodes = ExamNode.objects.filter(paper=paper_obj)
                    questions = nodes.filter(node_type='question').count()
                    tables = nodes.filter(node_type='table').count()
                    images = nodes.filter(node_type='image').count();

                    messages.success(request, 
                        f"🎉 ROBUST EXTRACTION SUCCESS!\n"
                        f"📝 {questions} questions extracted\n"
                        f"📊 {tables} tables preserved\n" 
                        f"🖼️ {images} images captured\n"
                        f"💯 {paper_obj.total_marks} total marks calculated"
                    )
                    
                    return redirect("load_saved_paper", paper_obj.pk)
                else:
                    messages.error(request, "❌ Robust extraction failed - please try again")
                    
            except Exception as e:
                print(f"❌ Robust extraction error: {str(e)}")
                import traceback
                print(traceback.format_exc())
                messages.error(request, f"Extraction failed: {str(e)}")
                
        else:
            messages.error(request, "Please upload a .docx file")

        return redirect("upload_assessment")

    return render(request, "core/assessor-developer/upload_assessment.html", {
        "submissions": submissions,
        "qualifications": qualifications,
    })
# ---------------------------------------
# 4) DRF endpoint: returns JSON (for AJAX)
# ---------------------------------------
from django.db import transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from django.http import JsonResponse
from django.db.models import Q
import json, random, re, traceback

@api_view(["POST"])
@parser_classes([MultiPartParser, JSONParser])
def generate_tool(request):
    """
    Accepts POST with:
      - qualification (string: id, code, or name)
      - mark_target (int or numeric string)
      - optional file (PDF/DOCX)
    Returns JSON: {"questions": [...], "total": <int>}
    """

    # --- tiny, safe text extractor (no extra deps) --------------------------
    def _extract_text(uploaded_file, content_type: str) -> str:
        try:
            pos = uploaded_file.tell()
        except Exception:
            pos = None
        try:
            data = uploaded_file.read()
            if not data:
                return ""
            try:
                return data.decode("utf-8", "ignore")
            except Exception:
                return ""
        finally:
            try:
                if pos is not None:
                    uploaded_file.seek(pos)
            except Exception:
                pass

    try:
        qual       = (request.data.get("qualification") or "").strip()
        raw_target = (request.data.get("mark_target") or "").strip()
        demo_file  = request.FILES.get("file")

        # Validate mark_target
        if not raw_target.isdigit():
            return JsonResponse({"error": "mark_target must be a number."}, status=400)
        target = int(raw_target)

        all_qs = []

        # -------- If a file was uploaded, use Gemini path -------------------
        if demo_file:
            text = _extract_text(demo_file, getattr(demo_file, "content_type", "") or "")

            # Optional examples from your in-memory bank
            samples  = QUESTION_BANK.get(qual, [])[:3]
            examples = "\n".join(f"- {s.get('text','')}" for s in samples)

            prompt = (
                f"You’re an assessment generator for **{qual}**.\n"
                f"Here are some example questions:\n{examples}\n\n"
                "Return pure JSON with a top-level key 'questions' where each item has "
                "'text' (string), 'marks' (integer), and optional 'case_study' (string).\n\n"
                f"Past-Papers Text:\n{text}"
            )

            resp = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
            raw = (getattr(resp, "text", "") or "").strip()
            if not raw:
                return JsonResponse({"error": "Gemini returned an empty response."}, status=502)

            # Clean up JSON fences & smart quotes
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw).strip()
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")

            # Parse JSON robustly
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                m = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)
                if not m:
                    return JsonResponse(
                        {"error": "Invalid JSON from model.", "raw_snippet": cleaned[:300]},
                        status=502
                    )
                try:
                    data = json.loads(m.group(1))
                except Exception as err:
                    return JsonResponse(
                        {"error": "Invalid JSON from model.", "details": str(err), "raw_snippet": cleaned[:300]},
                        status=502
                    )

            if not isinstance(data, dict) or "questions" not in data:
                return JsonResponse(
                    {"error": "Missing 'questions' key in model output.", "raw_snippet": cleaned[:300]},
                    status=502
                )

            items = data.get("questions") or []
            if isinstance(items, dict):
                items = [items]

            for q in items:
                if not isinstance(q, dict):
                    continue
                q_text = (q.get("text") or "").strip()
                try:
                    q_marks = int(q.get("marks", 0))
                except Exception:
                    q_marks = 0
                if q_text:
                    all_qs.append({
                        "text": q_text,
                        "marks": max(q_marks, 0),
                        "case_study": str(q.get("case_study") or "")
                    })

        # -------- Otherwise, pull from QuestionBankEntry (database) ---------
        else:
            # Resolve qualification by id, code, or name
            qual_obj = Qualification.objects.filter(
                Q(id__iexact=str(qual)) | Q(code__iexact=str(qual)) | Q(name__iexact=str(qual))
            ).first() if qual else None

            if not qual_obj:
                return JsonResponse({"error": f"Unknown qualification '{qual}'."}, status=404)

            entries = list(QuestionBankEntry.objects.filter(qualification=qual_obj))
            if not entries:
                return JsonResponse(
                    {"error": f"No questions found in the bank for qualification '{qual}'."},
                    status=404
                )

            random.shuffle(entries)
            running = 0
            for e in entries:
                m = int(e.marks or 0)
                if running + m <= target:
                    all_qs.append({
                        "text": e.text,
                        "marks": m,
                        "case_study": str(e.case_study) if getattr(e, "case_study", None) else ""
                    })
                    running += m
                if running >= target:
                    break

        # -------- Second pass: cap to target and sanitize -------------------
        random.shuffle(all_qs)
        final_selection = []
        running_sum = 0
        for q in all_qs:
            m = int(q.get("marks") or 0)
            if m < 0:
                m = 0
            if running_sum + m <= target:
                final_selection.append(q)
                running_sum += m
            if running_sum >= target:
                break

        return JsonResponse({"questions": final_selection, "total": running_sum})

    except Exception as e:
        return JsonResponse(
            {"error": str(e), "traceback": traceback.format_exc().splitlines()[:5]},
            status=500
        )

#================End of Generate Tool==============================================


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
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
# from core.models import Assessment   # ensure this import exists

@login_required
def assessor_dashboard(request):
    user = request.user

    # Be defensive in case user has no qualification attribute
    qualification = getattr(user, "qualification", None)

    # Base queryset
    qs = Assessment.objects.all()

    # Scope by user's EISA centre, but include unassigned so nothing disappears
    user_eisa = getattr(getattr(user, "profile", None), "eisa_id", None)
    if user_eisa:
        qs = qs.filter(Q(eisa_id=user_eisa) | Q(eisa_id__isnull=True))

    # Keep your original qualification scoping if present
    if qualification:
        qs = qs.filter(qualification=qualification)

    # Show only items waiting for the Assessor
    assessments = qs.filter(status__in=[S_TO_ASSESSOR, "Pending"]).order_by("-created_at")
    return render(request, "core/assessor-developer/assessor_dashboard.html", {
        "assessments": assessments,
        "papers": assessments,         # alias for older partials
        "qualification": qualification,
        "user": user,
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
            moderator_notes=content,
            

            status=S_TO_ETQA
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
        assessment.status = 'Submitted to Moderator'
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
    MODERATOR_QUEUE_ALIASES = [
    "Submitted to Moderator",
    "submitted to moderator",
    "Submitted to Moderator ",
    "Submitted to moderator",
    "ToModerator",
    "to_moderator"
]

    pending = Assessment.objects.filter(
        status__in=["Pending"] + MODERATOR_QUEUE_ALIASES,
        paper__isnull=False
    ).order_by("-created_at")
        

    forwarded = Assessment.objects.filter(
        status="Submitted to ETQA",
        paper__isnull=False  #  also filter here
    ).order_by("-created_at")

    recent_fb = Feedback.objects.select_related("assessment") \
                                .order_by("-created_at")[:10]

    return render(request, "core/moderator/moderator_developer.html", {
        "pending_assessments":   pending,
        "forwarded_assessments": forwarded,
        "recent_feedback":       recent_fb,
    })



def moderate_assessment(request, identifier):
    assessment = Assessment.objects.filter(eisa_id=identifier).first()
    if not assessment and identifier.isdigit():
        assessment = Assessment.objects.filter(paper_link_id=int(identifier)).first()
    if not assessment:
        raise Http404("Assessment not found.")

    questions = assessment.generated_questions.all()
    if request.method == 'POST':
        notes = request.POST.get('moderator_notes', '').strip()
        assessment.moderator_notes = notes
        assessment.status = 'Submitted to Moderator'
        assessment.save()
        return redirect('assessor_dashboard')

    return render(request, 'core/assessor-developer/view_assessment.html', {
        'assessment': assessment,
        'questions': questions
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
# 1) QCTO Dashboard: list assessments submitted to ETQA
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
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .models import Assessment
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .models import Assessment

@require_http_methods(["GET", "POST"])
def qcto_compliance(request):
    if request.method == "POST":
        eisa_id = request.POST.get("eisa_id")
        assessment = get_object_or_404(Assessment, eisa_id=eisa_id)

        # read the notes and decision from the form
        notes = request.POST.get("qcto_notes", "").strip()
        decision = request.POST.get("decision")

        # update status and save
        if decision == "approve":
            assessment.status = "Submitted to QCTO"   # ✅ this is key
            messages.success(request, f"{eisa_id} sent to QCTO Final Review.")
        elif decision == "reject":
            assessment.status = "Non-compliant"
            messages.success(request, f"{eisa_id} marked non-compliant.")
        else:
            messages.error(request, "Invalid decision.")
            return redirect("qcto_compliance")

        assessment.qcto_notes = notes
        assessment.save()

        # ✅ redirect to refresh the page so it's removed from the list
        return redirect("qcto_compliance")

    # GET: show only those not yet reviewed
    assessments = Assessment.objects.exclude(status__in=["Submitted to QCTO", "Submitted to ETQA", "Approved by ETQA", "Non-compliant", "Rejected"]).order_by('-created_at')

    return render(request, "core/qcto/qcto_compliance.html", {
        "assessments": assessments
    })


# 5) QCTO Final Assessment Review: list for QCTO decision
@login_required
# @staff_member_required
@require_http_methods(["GET", "POST"])
def qcto_assessment_review(request):
    if request.method == "POST":
        eisa_id = request.POST.get("eisa_id")
        assessment = get_object_or_404(Assessment, eisa_id=eisa_id)

        notes    = request.POST.get("qcto_notes", "").strip()
        decision = request.POST.get("decision")

        if decision == "approve":
            assessment.status = "Submitted to ETQA"
            messages.success(request, f"{eisa_id} approved and forwarded to ETQA.")
        elif decision == "reject":
            assessment.status = "Rejected"
            messages.success(request, f"{eisa_id} has been rejected.")
        else:
            messages.error(request, "Invalid decision.")

        assessment.qcto_notes = notes
        assessment.save()
        return redirect("qcto_assessment_review")

    # GET: only show those pending QCTO
    assessments = Assessment.objects.filter(status="Submitted to QCTO").order_by("-created_at")
    return render(request, "core/qcto/assessment_review.html", {
        "assessments": assessments
    })




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
def review_saved_selector(request):
    """View to select a saved paper for review"""

    filter_type = request.GET.get("type", "")

    # Get papers query
    all_papers = Paper.objects.order_by("-created_at")

    # Filter papers
    original_papers = all_papers.filter(is_randomized=False)
    randomized_papers = all_papers.filter(is_randomized=True)

    # Get qualifications for filtering
    qualifications = Qualification.objects.all()

    selected_paper = None
    question_nodes = []
    questions_count = tables_count = images_count = 0

    if request.method == "POST":
        paper_id = request.POST.get("paper_id")
        if paper_id:
            selected_paper = Paper.objects.filter(pk=paper_id).first()
            if selected_paper:
                nodes = ExamNode.objects.filter(paper=selected_paper)
                question_nodes = nodes.filter(node_type='question').order_by('order_index')
                questions_count = question_nodes.count()
                tables_count = nodes.filter(node_type='table').count()
                images_count = nodes.filter(node_type='image').count()
            return render(request, "core/administrator/review_saved_selector.html", {
                "original_papers": original_papers,
                "randomized_papers": randomized_papers,
                "papers": all_papers,  # For dropdown
                "qualifications": qualifications,
                "filter_type": filter_type,
                "selected_paper": selected_paper,
                "question_nodes": question_nodes,
                "questions_count": questions_count,
                "tables_count": tables_count,
                "images_count": images_count,
            })

    return render(request, "core/administrator/review_saved_selector.html", {
        "original_papers": original_papers,
        "randomized_papers": randomized_papers,
        "papers": all_papers,  # For dropdown
        "qualifications": qualifications,
        "filter_type": filter_type,
        "selected_paper": selected_paper,
        "question_nodes": question_nodes,
        "questions_count": questions_count,
        "tables_count": tables_count,
        "images_count": images_count,
    })

@login_required
def load_saved_paper_view(request, paper_pk):
    """View for loading and reviewing a saved paper"""
    try:
        # Get paper with optimized query
        paper = get_object_or_404(Paper.objects.select_related('qualification'), id=paper_pk)
        
        # Get all nodes with parent relationships
        nodes = list(ExamNode.objects.filter(
            paper=paper
        ).select_related('parent').order_by('order_index'))
        
        # Debug information
        node_types = {}
        for node in nodes:
            node_type = node.node_type
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print(f"Found {len(nodes)} nodes: {node_types}")
        
        # Build node hierarchy for template
        questions = []
        node_map = {}
        
        # Create dictionaries for each node
        for node in nodes:
            # Process content to ensure it's a list
            content = node.content or []
            
            # Create node dict for template
            node_dict = {
                'id': str(node.id),
                'type': node.node_type,
                'number': node.number or '',
                'text': node.text or '',
                'marks': node.marks or '',
                'content': content,  # Already JSON from db
                'children': []
            }
            
            # Store in map for parent relationships
            node_map[str(node.id)] = node_dict
            
            # Add top-level nodes to questions list
            if node.node_type == 'question':
                questions.append(node_dict)
        
        # Build parent-child relationships
        for node in nodes:
            if node.parent and str(node.parent.id) in node_map:
                parent_dict = node_map[str(node.parent.id)]
                child_dict = node_map[str(node.id)]
                parent_dict['children'].append(child_dict)
        
        # Get question stats
        question_nodes = [n for n in nodes if n.node_type == 'question']
        tables_count = sum(1 for n in nodes if n.node_type == 'table')
        images_count = sum(1 for n in nodes if n.node_type == 'image')
        
        print(f"Prepared {len(questions)} top-level questions with {len(question_nodes)} total questions")
        
        # Get linked assessment if any
        assessment = Assessment.objects.filter(paper_link=paper).first()
        
        context = {
            'paper': paper,
            'questions': questions,
            'assessment': assessment,
            'total_marks': paper.total_marks,
            'node_count': len(nodes),
            'question_nodes': question_nodes,
            'questions_count': len(question_nodes),
            'tables_count': tables_count,
            'images_count': images_count,
        }
        print(f"Questions passed to template: {len(questions)}")
        return render(request, 'core/administrator/review_paper.html', context)
        
    except Exception as e:
        print(f"Error in load_saved_paper_view: {str(e)}")
        import traceback
        print(traceback.format_exc())
        messages.error(request, f"Error loading paper: {str(e)}")
        return redirect('review_saved_selector')

@login_required
def student_dashboard(request):
    """Dashboard view for students/learners to see their available assessments"""

    user_qualification = request.user.qualification

    # Only include assessments with papers and nodes
    assessments = Assessment.objects.filter(
        status__in=["Approved by ETQA", "approved", "etqa_approved"],
        qualification=user_qualification,
        paper_link__isnull=False
    ).select_related(
        'qualification',
        'paper_link'
    ).order_by('-created_at')

    assessment_data = []
    for assessment in assessments:
        paper = assessment.paper_link

        has_nodes = paper.nodes.filter(
            node_type='question',
            parent__isnull=True
        ).exists() if paper else False

        if not has_nodes:
            continue  # skip assessments with no real questions

        attempt_count = ExamAnswer.objects.filter(
            question__assessment=assessment,
            user=request.user
        ).values('attempt_number').distinct().count()

        assessment_data.append({
            'assessment': assessment,
            'attempt_count': attempt_count,
            'max_attempts': 3,
            'can_attempt': attempt_count < 3
        })

    return render(request, "core/student/dashboard.html", {
        'assessment_data': assessment_data,
        'user': request.user,
        'qualification': user_qualification
    })


def custom_logout(request):
     logout(request)
     return redirect('custom_login')

@login_required
def randomize_paper_structure_view(request, paper_pk):
    """View to create a randomized version of an existing paper"""
    try:
        # Get original paper
        original_paper = get_object_or_404(Paper, pk=paper_pk)
        
        if original_paper.is_randomized:
            messages.error(request, "Cannot randomize an already randomized paper")
            return redirect('review_saved_selector')

        # Create new randomized paper
        randomized_paper = Paper.objects.create(
            name=f"{original_paper.name} (Randomized)",
            qualification=original_paper.qualification,
            created_by=original_paper.created_by,
            is_randomized=True
        )

        # Get all question nodes from original paper
        nodes = ExamNode.objects.filter(
            paper=original_paper,
            node_type='question'
        ).order_by('?')  # Random order

        # Copy nodes to new paper
        for index, node in enumerate(nodes, 1):
            ExamNode.objects.create(
                paper=randomized_paper,
                node_type=node.node_type,
                number=f"{index}",  # Sequential numbering
                text=node.text,
                marks=node.marks,
                content=node.content,
                order_index=index,
                payload=node.payload
            )

        messages.success(request, f"Created randomized paper (ID: {randomized_paper.pk})")
        return redirect('load_saved_paper', paper_pk=randomized_paper.pk)

    except Exception as e:
        messages.error(request, f"Failed to randomize paper: {str(e)}")
        return redirect('review_saved_selector')

@login_required
def save_blocks_view(request, paper_id):
    """Save extracted blocks to database"""
    try:
        paper = get_object_or_404(Paper, id=paper_id)
        blocks = request.session.get('extracted_blocks')
        
        if not blocks:
            messages.error(request, "No blocks found to save")
            return JsonResponse({'status': 'error', 'message': 'No blocks found'})
            
        success = save_nodes_to_db(blocks, paper)
        
        if success:
            messages.success(request, "Blocks saved successfully")
            return JsonResponse({'status': 'success', 'redirect': reverse('view_paper', args=[paper_id])})
        else:
            messages.error(request, "Failed to save blocks")
            return JsonResponse({'status': 'error', 'message': 'Save failed'})
            
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def write_exam(request, assessment_id):
    """
    Render the write page for a single assessment.
    - Old pipeline: GeneratedQuestion
    - New pipeline: ExamNode-based paper
    """
    assessment = get_object_or_404(
        Assessment.objects.select_related('paper_link', 'qualification'),
        id=assessment_id
    )

    # Optional safety: only show assessments matching the learner’s qualification
    if request.user.qualification and assessment.qualification_id != request.user.qualification_id:
        messages.error(request, "This assessment is not assigned to your qualification.")
        return redirect('student_dashboard')

    paper = assessment.paper_link  # may be None for old pipeline
    generated_qs = assessment.generated_questions.all().order_by('id')  # old

    # new: only if there's a paper with nodes
    exam_nodes = (
        paper.nodes.filter(node_type='question', parent__isnull=True)
        .order_by('order_index')
        if paper else []
    )

    context = {
        'assessment': assessment,
        'generated_qs': generated_qs,   # old pipeline
        'exam_nodes': exam_nodes,       # new pipeline
        'attempt_number': 1,            # demo; bump if you track attempts
    }
    return render(request, 'write_exam.html', context)


@login_required
@require_http_methods(["POST"])
def submit_exam(request, assessment_id):
    """
    Accepts both:
      - answer_<GeneratedQuestion.id>          (old pipeline)
      - answer_node_<ExamNode.uuid>           (new pipeline)

    Old: creates ExamAnswer rows (your existing flow).
    New: collects node answers; optionally save into StudentWrittenPaper if present.
    """
    assessment = get_object_or_404(Assessment, id=assessment_id)
    attempt_number = int(request.POST.get('attempt_number', 1))

    # --- OLD PIPELINE: GeneratedQuestion → ExamAnswer ---
    saved_count_old = 0
    for key, value in request.POST.items():
        if not key.startswith('answer_'):
            continue
        # ignore the new pipeline prefix
        if key.startswith('answer_node_'):
            continue

        # key is "answer_<gq_id>"
        try:
            gq_id = int(key.split('_', 1)[1])
        except (IndexError, ValueError):
            continue

        gq = GeneratedQuestion.objects.filter(id=gq_id, assessment=assessment).first()
        if not gq:
            continue

        try:
            with transaction.atomic():
                ExamAnswer.objects.create(
                    user=request.user,
                    question=gq,
                    answer_text=value.strip(),
                    attempt_number=attempt_number
                )
                saved_count_old += 1
        except IntegrityError:
            # If unique_together blocks dupes, you can update instead:
            ans = ExamAnswer.objects.get(
                user=request.user, question=gq, attempt_number=attempt_number
            )
            ans.answer_text = value.strip()
            ans.save(update_fields=['answer_text'])

    # --- NEW PIPELINE: ExamNode → collect answers ---
    node_answers = {}
    for key, value in request.POST.items():
        # keys like: answer_node_<uuid>
        if not key.startswith('answer_node_'):
            continue
        node_uuid = key.replace('answer_node_', '', 1).strip()
        node_answers[node_uuid] = (value or '').strip()

    saved_new = len(node_answers)

    # OPTIONAL: persist node answers if you’ve added StudentWrittenPaper
    # if node_answers:
    #     paper = assessment.paper_link
    #     if paper:
    #         swp, _ = StudentWrittenPaper.objects.get_or_create(
    #             learner=request.user,
    #             paper=paper,
    #         )
    #         # merge into existing JSON (so multiple submits don’t clobber)
    #         existing = swp.answers_json or {}
    #         existing.update(node_answers)
    #         swp.answers_json = existing
    #         swp.save(update_fields=['answers_json', 'last_updated'])

    messages.success(
        request,
        f"Submitted: {saved_count_old} legacy answers"
        + (f", {saved_new} structured answers." if saved_new else ".")
    )
    return redirect('student_dashboard')

    #Views for the Demo 

@login_required
def papers_demo(request):
    """
    Simple demo page: list ALL papers from the DB in a table.
    No status/qualification filtering (for now).
    """
    #papers = Paper.objects.select_related('qualification').order_by('-created_at')
    papers = Paper.objects.filter(qualification=request.user.qualification)
    return render(request, 'core/student/papers_demo.html', {
        'papers': papers,
        'user': request.user,
    })




@login_required
def write_paper_simple(request, paper_id):
    paper = get_object_or_404(Paper.objects.select_related('qualification'), id=paper_id)

    # ⬇ Instead of nodes = paper.nodes.filter(...), build the same rich structure:
    questions = build_questions_tree_for_paper(paper)

    return render(request, 'core/student/write_paper_simple.html', {
        'paper': paper,
        'questions': questions,   # ← same shape as review page
        'attempt_number': 1,
    })


@login_required
@require_http_methods(["POST"])
def submit_paper_simple(request, paper_id):
    """
    Accepts answer_node_<ExamNode.uuid> fields. For now we just count & confirm.
    If you’ve added StudentWrittenPaper, uncomment the persistence block.
    """
    paper = get_object_or_404(Paper, id=paper_id)

    # Gather answers
    node_answers = {}
    for key, val in request.POST.items():
        if key.startswith('answer_node_'):
            node_uuid = key.replace('answer_node_', '', 1)
            node_answers[node_uuid] = (val or '').strip()

    saved_new = len(node_answers)

    # OPTIONAL: Persist to StudentWrittenPaper
    # if node_answers:
    #     swp, _ = StudentWrittenPaper.objects.get_or_create(
    #         learner=request.user,
    #         paper=paper,
    #     )
    #     existing = swp.answers_json or {}
    #     existing.update(node_answers)
    #     swp.answers_json = existing
    #     swp.save(update_fields=['answers_json', 'last_updated'])

    messages.success(request, f"Submitted {saved_new} answers for '{paper.name}'.")
    return redirect('papers_demo')
#end of demo views



# core/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, NoReverseMatch
from django.template.loader import select_template, TemplateDoesNotExist
from .models import Assessment  # adjust if located elsewhere

def assessment_detail(request, pk):
    a = get_object_or_404(Assessment, pk=pk)

    # 1) Try to send to your existing legacy viewer by eisa_id (if present & route exists)
    eisa = getattr(a, "eisa_id", None)
    if eisa:
        for route_name in ("view_assessment", "core:view_assessment"):
            try:
                return redirect(reverse(route_name, args=[eisa]))
            except NoReverseMatch:
                pass  # try next candidate

    # 2) Otherwise, render an existing review template *by PK* if we can find one
    candidate_templates = [
        # 👇 put likely paths here; we'll try each in order
        "core/assessor-developer/review_saved.html",
        "core/assessor/review_saved.html",
        "core/review_saved.html",
        "core/components/review_saved.html",
    ]
    try:
        tmpl = select_template(candidate_templates)
        return render(request, tmpl.template.name, {"assessment": a, "paper": a})
    except TemplateDoesNotExist:
        # 3) Absolute fallback: a tiny built-in viewer so you can proceed tonight
        return render(request, "core/assessment_detail_fallback.html", {
            "assessment": a,
            "paper": a,  # alias for older partials
        })


# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, NoReverseMatch

@login_required
def open_assessment_paper(request, pk):
    a = get_object_or_404(Assessment, pk=pk)
    # Prefer extracted Paper review if present
    if a.paper_link_id:
        return redirect('load_saved_paper', paper_pk=a.paper_link_id)
    # Legacy viewer by eisa_id
    if getattr(a, "eisa_id", None):
        try:
            return redirect(reverse('view_assessment', args=[a.eisa_id]))
        except NoReverseMatch:
            pass
    # Last resort: your fallback detail
    return redirect('assessment_detail', pk=a.pk)
# Canonical statuses
S_ETQA_QUEUE = "submitted_to_etqa"
S_APPROVED   = "approved"

# Accept historical/mixed variants so tonight's data still shows up
ETQA_QUEUE_ALIASES = {S_ETQA_QUEUE, "Submitted to ETQA", "ToETQA", "to_etqa", "ToETQA", "submitted_to_ETQA"}
APPROVED_ALIASES   = {S_APPROVED, "Approved by ETQA", "Approved"}

@login_required
def etqa_dashboard(request):
    centers = AssessmentCentre.objects.all()
    qualifications = Qualification.objects.all()

    # EISA scoping (include unassigned so you can still see new items)
    qs = Assessment.objects.all().select_related("qualification")
    user_eisa = getattr(getattr(request.user, "profile", None), "eisa_id", None)
    if user_eisa:
        qs = qs.filter(Q(eisa_id=user_eisa) | Q(eisa_id__isnull=True))

    # Selected qualification (GET from change, POST from form submit)
    selected_qualification = request.GET.get("qualification_id") or request.POST.get("qualification")
    if selected_qualification:
        qs = qs.filter(qualification_id=selected_qualification)

    # Lists for template
    assessments_for_etqa = qs.filter(status__in=ETQA_QUEUE_ALIASES).order_by("-created_at")
    approved_assessments = qs.filter(status__in=APPROVED_ALIASES).order_by("-created_at")

    # Handle approvals (bulk approve selected ids)
    if request.method == "POST":
        selected_ids = request.POST.getlist("assessment_ids")
        selected_assessments = Assessment.objects.filter(id__in=selected_ids)

        if not selected_assessments.exists():
            messages.error(request, "Please select at least one assessment.")
            return redirect("etqa_dashboard")

        # Move to canonical final status
        updated = selected_assessments.update(status=S_APPROVED)
        messages.success(request, f"Approved {updated} assessment(s).")
        return redirect("etqa_dashboard")

    created_batch = None  # keep your existing variable for the template

    return render(request, "core/etqa/etqa_dashboard.html", {
        "centers": centers,
        "qualifications": qualifications,
        "selected_qualification": selected_qualification,
        "approved_assessments": approved_assessments,
        "assessments_for_etqa": assessments_for_etqa,
        "created_batch": created_batch,
    })
from django.shortcuts import render
from core.models import Assessment

def assessment_tracking_overview(request):
    assessments = Assessment.objects.select_related('qualification', 'paper_link', 'created_by').order_by('-created_at')
    return render(request, 'core/assessor-developer/assessment_tracking_overview.html', {
        'assessments': assessments
    })

from django.views.decorators.http import require_POST
@require_POST
def forward_assessment(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    # Forward status order: Pending → Submitted to Moderator → Submitted to QCTO → Submitted to ETQA
    if assessment.status == "Pending":
        assessment.status = "Submitted to Moderator"
    elif assessment.status == "Submitted to Moderator":
        assessment.status = "Submitted to QCTO"
    elif assessment.status == "Submitted to QCTO":
        assessment.status = "Submitted to ETQA"
    assessment.save()
    return redirect(request.META.get('HTTP_REFERER', 'assessor_dashboard'))