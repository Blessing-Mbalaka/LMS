from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings
import random
from django.utils.html import mark_safe
import base64 
import uuid

#************************
# Qualification creation
#************************
from django.db import models
from django.core.exceptions import ValidationError

class Qualification(models.Model):
    # Define constants at class level
    QUALIFICATION_TYPES = [
        ("Maintenance Planner", "Maintenance Planner"),
        ("Quality Controller", "Quality Controller"),
        ("Chemical Plant", "Chemical Plant")
    ]

    QUALIFICATION_SAQA_MAPPING = {
        "Maintenance Planner": "101874",
        "Quality Controller": "117309", 
        "Chemical Plant": "102156"
        
    }

    MODULE_NUMBERS = [
        ('1A', 'Module 1A'),
        ('1B', 'Module 1B'),
        ('1C', 'Module 1C'),
        ('2A', 'Module 2A'),
        ('2B', 'Module 2B'),
        ('2C', 'Module 2C'),
        ('3A', 'Module 3A'),
        ('3B', 'Module 3B'),
        ('3C', 'Module 3C')
    ]

    name = models.CharField(
        max_length=100,
        choices=QUALIFICATION_TYPES,
        unique=True
    )
    saqa_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_module_choices_for_type(cls, qual_type):
        """Get valid module numbers for a qualification type"""
        if qual_type == "Chemical Plant":
            return cls.MODULE_NUMBERS  # All modules
        else:
            return [m for m in cls.MODULE_NUMBERS if m[0].startswith('1')]  # Only 1A-1C

    def clean(self):
        """Ensure SAQA ID matches qualification type"""
        expected_saqa = self.QUALIFICATION_SAQA_MAPPING.get(self.name)
        if expected_saqa and self.saqa_id != expected_saqa:
            raise ValidationError(f"SAQA ID for {self.name} must be {expected_saqa}")

    def __str__(self):
        return f"{self.name} (SAQA: {self.saqa_id})"


#****************
# Custom User
#****************
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('default',         'Awaiting Activation'),
        ('admin',           'Administrator'),
        ('assessor_dev',    'Assessor (Developer)'),
        ('moderator',       'Moderator (Developer)'),
        ('qcto',            'QCTO Validator'),
        ('etqa',            'ETQA'),
        ('learner',         'Learner'),
        ('assessor_marker', 'Assessor (Marker)'),
        ('internal_mod',    'Internal Moderator'),
        ('external_mod',    'External Moderator (QALA)'),
        ('assessment_center', 'Assessment Center')
    ]

    role                     = models.CharField(max_length=30, choices=ROLE_CHOICES, default='learner')
    qualification            = models.ForeignKey(
                                  Qualification,
                                  on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name='users'
                              )
    email                    = models.EmailField(unique=True)
    objects                  = UserManager()
    created_at               = models.DateTimeField(auto_now_add=True)
    activated_at             = models.DateTimeField(default=now)
    deactivated_at           = models.DateTimeField(null=True, blank=True)
    qualification_updated_at = models.DateTimeField(null=True, blank=True)
    last_updated_at          = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username

    def save(self, *args, **kwargs):
        if self.pk:
            orig = CustomUser.objects.get(pk=self.pk)
            if orig.qualification != self.qualification:
                self.qualification_updated_at = now()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"

#************************
# Question bank entry
#************************
class QuestionBankEntry(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("standard",   "Standard"),
        ("case_study", "Case Study"),
        ("mcq",        "Multiple Choice"),
    ]

    qualification  = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    question_type  = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default="standard")
    text           = models.TextField()
    marks          = models.PositiveIntegerField()
    case_study     = models.ForeignKey("CaseStudy", on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:30]}…"


#****************
# MCQ options
#****************
class MCQOption(models.Model):
    question = models.ForeignKey(
        QuestionBankEntry,
        on_delete=models.CASCADE,
        limit_choices_to={"question_type": "mcq"},
        related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✗'} {self.text}"


#*****************************************
# Assessment + Build-A-Paper & Randomization
#*****************************************
class Assessment(models.Model):
    PAPER_TYPE_CHOICES = [
        ('admin_upload', 'Admin Upload'),
        ('randomized', 'Randomized Paper')
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_moderation', 'Pending Moderation'),
        ('moderated', 'Moderated'),
        ('pending_etqa', 'Pending ETQA Review'),
        ('etqa_approved', 'ETQA Approved'),
        ('etqa_rejected', 'ETQA Rejected'),
        ('pending_qcto', 'Pending QCTO Review'),
        ('qcto_approved', 'QCTO Approved'),
        ('qcto_rejected', 'QCTO Rejected'),
        ('active', 'Active'),
        ('archived', 'Archived')
    ]

    eisa_id = models.CharField(max_length=50)  # Increased from 20
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    paper = models.CharField(max_length=50)
    paper_type = models.CharField(
        max_length=50,  # Increased from 20
        choices=PAPER_TYPE_CHOICES,
        default='admin_upload'
    )
    paper_link = models.ForeignKey(
        "Paper",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments"
    )
    saqa_id = models.CharField(max_length=50, blank=True, null=True)  # Increased from 20
    moderator = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="assessments/", blank=True, null=True)
    memo = models.FileField(
        upload_to="assessments/memos/", 
        blank=True, 
        null=True,
        help_text="Memo file for admin-uploaded assessments"
    )
    comment = models.TextField(blank=True)
    forward_to_moderator = models.BooleanField(default=False)
    moderator_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    qcto_notes = models.TextField(blank=True)
    
    # ETQA fields - only used for randomized papers
    is_selected_by_etqa = models.BooleanField(default=False)
    memo_file = models.FileField(
        upload_to='memos/randomized/', 
        null=True, 
        blank=True,
        help_text="Memo file for randomized assessments requiring ETQA approval"
    )
    etqa_approved = models.BooleanField(default=False)
    etqa_comments = models.TextField(blank=True)
    etqa_approved_date = models.DateTimeField(null=True, blank=True)

    # Add status tracking fields
    status = models.CharField(
        max_length=50,  # Increased from 20
        choices=STATUS_CHOICES,
        default='draft'
    )
    status_changed_at = models.DateTimeField(auto_now_add=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes'
    )



    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments_created"
    )
    module_name = models.CharField(
        max_length=100,
        help_text="e.g. Chemical Operations",
        default="Unknown Module"
    )
    module_number = models.CharField(
        max_length=2,
        choices=Qualification.MODULE_NUMBERS,
        help_text="Module identifier (1A, 1B, etc)",
        default="1A"
    )
    
    # Single memo field definition
    memo = models.FileField(
        upload_to="assessments/memos/",
        blank=True, 
        null=True,
        help_text="Assessment memo file"
    )

    def get_memo_path(self, filename):
        """Generate organized path for memo files"""
        safe_name = self.module_name.replace(' ', '_')
        return f'assessments/memos/{safe_name}/{self.module_number}/{filename}'

    # Combine save methods
    def save(self, *args, **kwargs):
        self.clean()
        if self.memo:
            new_name = f"memo_{self.module_number}_{self.qualification.name.replace(' ', '_')}.pdf"
            self.memo.name = self.get_memo_path(new_name)
        super().save(*args, **kwargs)

    def requires_etqa_approval(self):
        """Only randomized papers require ETQA approval"""
        return self.paper_type == 'randomized'

    def clean(self):
        """Validation to ensure correct memo field usage"""
        if self.paper_type == 'admin_upload':
            # Admin uploads should use the 'memo' field
            if self.memo_file:
                raise ValidationError({
                    'memo_file': 'For admin uploads, use the standard memo field'
                })
        else:
            # Randomized papers should use memo_file
            if self.memo:
                raise ValidationError({
                    'memo': 'For randomized papers, use the memo_file field'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # — new M2M through-model fields —
    questions            = models.ManyToManyField(
                               'QuestionBankEntry',
                               through='AssessmentQuestion',
                               related_name='assessments'
                           )
    questions_randomized = models.BooleanField(default=False)

    def randomize_questions(self):
        linked_qs = list(self.questions.all())
        if not linked_qs:
            return
        random.shuffle(linked_qs)
        for idx, q in enumerate(linked_qs, start=1):
            aq, _ = AssessmentQuestion.objects.get_or_create(
                assessment=self,
                question=q,
                defaults={'order': idx}
            )
            aq.order = idx
            aq.save(update_fields=['order'])
        self.questions_randomized = True
        self.save(update_fields=['questions_randomized'])

    def update_status(self, new_status, user):
        """Update assessment status with audit trail"""
        if new_status in dict(self.STATUS_CHOICES):
            self.status = new_status
            self.status_changed_at = now()
            self.status_changed_by = user
            self.save()

    def get_next_status(self):
        """Determine next status based on paper type and current status"""
        if self.paper_type == 'admin_upload':
            STATUS_FLOW = {
                'draft': 'pending_moderation',
                'pending_moderation': 'moderated',
                'moderated': 'pending_qcto',
                'pending_qcto': 'active'
            }
        else:  # randomized paper
            STATUS_FLOW = {
                'draft': 'pending_etqa',
                'pending_etqa': 'etqa_approved',
                'etqa_approved': 'pending_moderation',
                'pending_moderation': 'moderated',
                'moderated': 'pending_qcto',
                'pending_qcto': 'active'
            }
        return STATUS_FLOW.get(self.status)

    def can_transition_to(self, new_status, user):
        """Check if status transition is allowed for user role"""
        ALLOWED_TRANSITIONS = {
            'moderator': ['moderated', 'pending_moderation'],
            'etqa': ['etqa_approved', 'etqa_rejected'],
            'qcto': ['qcto_approved', 'qcto_rejected'],
            'admin': [s[0] for s in self.STATUS_CHOICES]
        }
        return new_status in ALLOWED_TRANSITIONS.get(user.role, [])

    class Meta:
        permissions = [
            ("can_moderate", "Can moderate assessments"),
            ("can_etqa_review", "Can review as ETQA"),
            ("can_qcto_review", "Can review as QCTO")
        ]

class AssessmentQuestion(models.Model):
    """Through-model to store per-question content, marks, and order."""
    assessment   = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    question     = models.ForeignKey(QuestionBankEntry, on_delete=models.CASCADE)
    order        = models.PositiveIntegerField(default=0)
    marks        = models.PositiveIntegerField(default=0)
    content_html = models.TextField(
        blank=True,
        help_text="Paste question text, tables, images (HTML) here."
    )

    class Meta:
        unique_together = ('assessment', 'question')
        ordering = ['order']

    def rendered_content(self):
        return mark_safe(self.content_html)

class CaseStudy(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self):
        return self.title

class GeneratedQuestion(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        related_name='generated_questions',
        on_delete=models.CASCADE
    )
    text = models.TextField()
    marks = models.PositiveIntegerField()
    case_study = models.ForeignKey(
        CaseStudy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]}… ({self.marks} marks)"



class MCQOption(models.Model):
    question = models.ForeignKey(
        QuestionBankEntry,
        on_delete=models.CASCADE,
        limit_choices_to={"question_type": "mcq"},
        related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✗'} {self.text}"

class ChecklistItem(models.Model):
    label = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label



class AssessmentCentre(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True)
    qualification_assigned = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

# Batch model ___________________________________________________________________________________________#

class Batch(models.Model):
    center = models.ForeignKey('AssessmentCentre', on_delete=models.CASCADE)
    qualification = models.ForeignKey('Qualification', on_delete=models.CASCADE)
    assessment = models.ForeignKey('Assessment', on_delete=models.CASCADE)
    assessment_date = models.DateField()
    # number_of_learners = models.PositiveIntegerField()
    submitted_to_center = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch - {self.center.name} | {self.qualification.name} | {self.assessment.eisa_id}"

#students model -------------------------------------------------------------------
class ExamAnswer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey('GeneratedQuestion', on_delete=models.CASCADE)
    answer_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)  # Track attempts

    class Meta:
        unique_together = ('user', 'question', 'attempt_number')  # Include attempts 
        verbose_name = 'Exam Answer'
        verbose_name_plural = 'Exam Answers'

    @property
    def assessment(self):
        """Quick access to the assessment through the question"""
        return self.question.assessment

    def __str__(self):
        return f"Answer by {self.user} for {self.question} (Attempt {self.attempt_number})"

# <-------------------------------------------Questions storage Models --------------------------------------------------->
# core/models.py
from django.db import models


class Paper(models.Model):
    name = models.CharField(max_length=255)
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    is_randomized = models.BooleanField(default=False)
    structure_json = models.JSONField(default=dict, blank=True)
    
    # Add total_marks field
    total_marks = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.qualification})"




class ExamNode(models.Model):
    """Single source of truth for all question/content storage"""
    BLOCK_TYPES = [
        ('question', 'Question'),
        ('table', 'Table'),
        ('image', 'Image'),
        ('case_study', 'Case Study'),
        ('instruction', 'Instruction')
    ]

    id = models.CharField(
        primary_key=True, 
        max_length=32,
        default=uuid.uuid4().hex
    )
    paper = models.ForeignKey(
        Paper, 
        on_delete=models.CASCADE,
        null=True,  # Allow null temporarily for migration
        default=None
    )
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True,
        on_delete=models.CASCADE
    )
    
    # Core fields with defaults
    node_type = models.CharField(
        max_length=50, 
        choices=BLOCK_TYPES,
        default='question'
    )
    number = models.CharField(max_length=20, blank=True, default='')
    marks = models.CharField(max_length=10, blank=True, default='0')
    text = models.TextField(blank=True, default='')
    
    # Structured content
    content = models.JSONField(
        default=dict,
        help_text="Structured content like tables, case studies"
    )
    
    # Binary content
    binary_content = models.BinaryField(
        null=True, 
        blank=True,
        help_text="For storing binary data like images"
    )
    content_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="MIME type for binary_content"
    )
    
    # Metadata with defaults
    order_index = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(
        
        auto_now_add=True  # Then add auto_now_add
    )
    
    class Meta:
        ordering = ['order_index']
        indexes = [
            models.Index(fields=['paper', 'order_index']),
            models.Index(fields=['node_type']),
            models.Index(fields=['parent', 'order_index'])
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(node_type__in=['question', 'table', 'image', 
                                            'case_study', 'instruction']),
                name='valid_node_type'
            )
        ]

    def clean(self):
        """Validate content based on node_type"""
        if self.node_type == 'image' and not self.binary_content:
            raise ValidationError("Images require binary content")
        if self.node_type == 'table' and not self.content:
            raise ValidationError("Tables require content")

    def get_full_structure(self):
        """Get complete nested structure including children"""
        structure = {
            'id': self.id,
            'type': self.node_type,
            'number': self.number,
            'marks': self.marks,
            'text': self.text,
            'content': self.get_content(),
            'order': self.order_index,
            'children': []
        }
        
        for child in self.examnode_set.order_by('order_index'):
            structure['children'].append(child.get_full_structure())
            
        return structure

    def get_content(self):
        """Return appropriate content based on type"""
        if self.node_type == 'image' and self.binary_content:
            # Changed from data_uri to proper base64 encoding
            return {
                'type': 'image',
                'content_type': self.content_type,
                'data': base64.b64encode(self.binary_content).decode()
            }
        return self.content  # Return JSON content field, not content1
    

    def __str__(self):
        return f"{self.paper.name} - {self.node_type} {self.number or ''}"


class Feedback(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    to_user = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Revised", "Revised"),
        ("Completed", "Completed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.assessment.eisa_id} → {self.to_user}"


class RegexPattern(models.Model):
    pattern = models.TextField()
    description = models.TextField()
    match_score = models.FloatField()
    example_usage = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
