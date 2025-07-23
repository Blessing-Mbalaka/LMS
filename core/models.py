from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings
import random
from django.utils.html import mark_safe

#************************
# Qualification creation
#************************
class Qualification(models.Model):
    QUALIFICATION_CHOICES = [
        ('default', 'Not Yet Assigned'),
        ('Maintenance Planner', 'Maintenance Planner'),
        ('Quality Controller', 'Quality Controller'),
        ('Chemical Plant', 'Chemical Plant'),
    ]
    QUALIFICATION_SAQA_MAPPING = {
        'Maintenance Planner': '101874',
        'Quality Controller':  '117309',
        'Chemical Plant':      '102156',
    }

    name               = models.CharField(max_length=100, unique=True)
    saqa_id            = models.CharField(max_length=20, unique=True)
    qualification_type = models.CharField(
        max_length=50,
        choices=QUALIFICATION_CHOICES,
        default='Chemical Plant',
    )
    code               = models.CharField(max_length=20, unique=True, null=True, blank=True)
    description        = models.TextField(blank=True)
    level              = models.PositiveIntegerField(null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.qualification_type in self.QUALIFICATION_SAQA_MAPPING:
            expected = self.QUALIFICATION_SAQA_MAPPING[self.qualification_type]
            if self.saqa_id != expected:
                raise ValidationError(f"SAQA ID for {self.qualification_type} must be {expected}")

    def is_predefined(self):
        return self.qualification_type in self.QUALIFICATION_SAQA_MAPPING

    def __str__(self):
        return f"{self.name} - SAQA ID: {self.saqa_id}"


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
    question   = models.ForeignKey(
                     QuestionBankEntry,
                     on_delete=models.CASCADE,
                     limit_choices_to={"question_type": "mcq"},
                     related_name="options"
                 )
    text       = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✗'} {self.text}"


#*****************************************
# Assessment + Build-A-Paper & Randomization
#*****************************************
class Assessment(models.Model):
    eisa_id             = models.CharField(max_length=20, unique=True)
    qualification       = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    paper               = models.CharField(max_length=10)
    paper_link          = models.ForeignKey(
                             "Paper",
                             null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name="assessments"
                         )
    saqa_id             = models.CharField(max_length=20, blank=True, null=True)
    moderator           = models.CharField(max_length=100, blank=True)
    file                = models.FileField(upload_to="assessments/", blank=True, null=True)
    memo                = models.FileField(upload_to="assessments/memos/", blank=True, null=True)
    comment             = models.TextField(blank=True)
    forward_to_moderator= models.BooleanField(default=False)
    moderator_notes     = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    qcto_notes          = models.TextField(blank=True)
    is_selected_by_etqa = models.BooleanField(default=False)
    

    STATUS_CHOICES = [
        ("Pending",                  "Pending"),
        ("Submitted to Moderator",   "Submitted to Moderator"),
        ("Returned for Changes",     "Returned for Changes"),
        ("Approved by Moderator",    "Approved by Moderator"),
        ("Submitted to QCTO",        "Submitted to QCTO"),
        ("Approved by QCTO",         "Approved by QCTO"),
        ("Submitted to ETQA",        "Submitted to ETQA"),
        ("Released to students",         "Released to students"),
        ("Rejected",                 "Rejected"),
        
    ]
    status      = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Pending")
    created_by  = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      null=True, blank=True,
                      on_delete=models.SET_NULL,
                      related_name="uploaded_assessments"
                  )

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

    def __str__(self):
        return self.eisa_id


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

class ExtractedQuestion(models.Model):
    number = models.CharField(max_length=20)  # e.g. 1.1.1
    instruction = models.TextField(blank=True)
    question_text = models.TextField()
    case_study = models.TextField(blank=True)
    marks = models.CharField(max_length=10, blank=True)
    table_data = models.JSONField(null=True, blank=True)
    source_paper = models.ForeignKey('Assessment', on_delete=models.SET_NULL, null=True)


#<-------------------------------------------Questions storage Models --------------------------------------------------->
# core/models.py
from django.db import models


class Paper(models.Model):          #  ✅ only one “(models.Model)”, colon right here
    name          = models.CharField(max_length=50)          # inside the class
    qualification = models.ForeignKey(
        "Qualification",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    total_marks   = models.PositiveIntegerField(default=0)

    created_at    = models.DateTimeField(auto_now_add=True)
    structure_json = models.JSONField(blank=True, null=True)
    is_randomized = models.BooleanField(default=False)



    def __str__(self):
        return self.name


class QuestionNode(models.Model):
    number = models.CharField(max_length=10)       # e.g. "1.1"
paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
marks = models.IntegerField(default=0)         # total marks for this node
instruction = models.TextField(blank=True)
active = models.BooleanField(default=True)     # use in live pools or archive

class QuestionItem(models.Model):
    node = models.ForeignKey(QuestionNode, on_delete=models.CASCADE, related_name='items')
    number = models.CharField(max_length=20)       # e.g. "1.1.1"
    text = models.TextField(blank=True)
    marks = models.IntegerField(default=0)
    case_study = models.TextField(blank=True)
    table_data = models.JSONField(blank=True, null=True)
    image_data = models.TextField(blank=True, null=True)
    question_type = models.CharField(
        max_length=50,
        choices=[
            ("constructed", "Constructed Response"),
            ("extended", "Extended Constructed Response"),
            ("case_study", "Case Study"),
            ("mcq", "Multiple Choice"),
            ("true_false", "True/False"),
            ("performance", "Performance Task"),
            ("tech", "Technology Enhanced"),
            ("mix_match", "Mix and Match")
        ]
    )
    active = models.BooleanField(default=True)

from django.db import models


#The pool the randomization will use.
class QuestionPoolEntry(models.Model):
    paper_number = models.CharField(max_length=10)  # e.g. "1A"
    qualification_id = models.CharField(max_length=50)  # e.g. "NQF4"

    question_number = models.CharField(max_length=20)  # e.g. "1.1", "1.1.1"
    parent_number = models.CharField(max_length=20, blank=True, null=True)  # optional

    question_type = models.CharField(max_length=50)  # e.g. mcq, extended
    marks = models.PositiveIntegerField(default=0)

    question_text = models.TextField(blank=True)
    table_data = models.JSONField(blank=True, null=True)
    image_data_uri = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paper_number} - Q{self.question_number} ({self.question_type})"

from django.db.models import JSONField                


class ExamNode(models.Model):
    id         = models.CharField(primary_key=True, max_length=32)  # the UUID hex
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, null=True, blank=True)
                                                                                        #The Paper we love!!The paper we Need!!!!!
    parent     = models.ForeignKey(
                    'self', null=True, blank=True,
                    on_delete=models.CASCADE, related_name='children')
    node_type  = models.CharField(max_length=50)     # "question", "table", ...
    number     = models.CharField(max_length=20, blank=True)
    marks      = models.CharField(max_length=10,  blank=True)
    text      = models.TextField(blank=True)
    content   = models.JSONField(default=list, blank=True)
    data_uri  = models.TextField(blank=True)  # for figures

    payload    = JSONField()                         # raw dict for convenience
    updated_at = models.DateTimeField(auto_now=True)
    is_top_level = models.BooleanField(default=False)  #True if 1.1, 2.1 etc.
    order_index = models.IntegerField(default=0)       # Helps re-order after randomization

    def __str__(self):
        return f"{self.node_type} {self.number or ''} ({self.id})"
    
#<---------------------------------------------------------------------------------------------->
    
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

#Trying to store everything relationaly---in addition to the current structured JSON.

class QuestionParent(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='parents')
    block_id = models.CharField(max_length=50, unique=True)  # Matches JSON `id`
    number = models.CharField(max_length=20, blank=True)
    marks = models.CharField(max_length=10, blank=True)
    text = models.TextField(blank=True)

class QuestionChild(models.Model):
    parent = models.ForeignKey(QuestionParent, on_delete=models.CASCADE, related_name='children')
    block_id = models.CharField(max_length=50, unique=True)  # Matches JSON `id`
    number = models.CharField(max_length=20, blank=True)
    marks = models.CharField(max_length=10, blank=True)
    text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
class QuestionContent(models.Model):
    parent_block = models.ForeignKey(QuestionParent, on_delete=models.CASCADE, null=True, blank=True, related_name='content_blocks')
    child_block = models.ForeignKey(QuestionChild, on_delete=models.CASCADE, null=True, blank=True, related_name='content_blocks')

    block_type = models.CharField(max_length=20)  # e.g., 'question_text', 'table', 'figure'
    text = models.TextField(blank=True)
    rows = models.JSONField(null=True, blank=True)  # optional for tables
    data_uri = models.TextField(blank=True)  # for images or diagrams
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
