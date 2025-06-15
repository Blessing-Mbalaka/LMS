from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings

#*****************ADMIN************************************************************************
# Qualification creation
class Qualification(models.Model):
    QUALIFICATION_CHOICES = [
        ('default', 'Not Yet Assigned'),
        ('Maintenance Planner', 'Maintenance Planner'),
        ('Quality Controller', 'Quality Controller'),
        ('Chemical Plant', 'Chemical Plant'),
    ]

    QUALIFICATION_SAQA_MAPPING = {
        'Maintenance Planner': '101874',
        'Quality Controller': '117309',
        'Chemical Plant': '102156',
    }

    name = models.CharField(max_length=100, unique=True)
    saqa_id = models.CharField(max_length=20, unique=True)
    qualification_type = models.CharField(
        max_length=50,
        choices=QUALIFICATION_CHOICES,
        default='Chemical Plant',
    )
    code = models.CharField(max_length=20, unique=True, null=True, blank=True)

    description = models.TextField(blank=True)
    level = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - SAQA ID: {self.saqa_id}"

    def clean(self):
        if self.qualification_type in self.QUALIFICATION_SAQA_MAPPING:
            expected_saqa_id = self.QUALIFICATION_SAQA_MAPPING[self.qualification_type]
            if self.saqa_id != expected_saqa_id:
                raise ValidationError(
                    f"SAQA ID for {self.qualification_type} must be {expected_saqa_id}"
                )

    def is_predefined(self):
        return self.qualification_type in self.QUALIFICATION_SAQA_MAPPING.keys()

# User creation
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('default', 'Awaiting Activation'),                  
        ('admin', 'Administrator'),
        ('assessor_dev', 'Assessor (Developer)'),
        ('moderator', 'Moderator (Developer)'),
        ('qcto', 'QCTO Validator'),
        ('etqa', 'ETQA'),
        ('learner', 'Learner'),
        ('assessor_marker', 'Assessor (Marker)'),
        ('internal_mod', 'Internal Moderator'),
        ('external_mod', 'External Moderator (QALA)'),
    ]

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='learner')
    qualification = models.ForeignKey(
        Qualification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    email = models.EmailField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(default=now)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    qualification_updated_at = models.DateTimeField(null=True, blank=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    @property
    def name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username 
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.pk:
            original = CustomUser.objects.get(pk=self.pk)
            if original.qualification != self.qualification:
                self.qualification_updated_at = now()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

class Assessment(models.Model):
    eisa_id = models.CharField(max_length=20, unique=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    paper = models.CharField(max_length=10)
    saqa_id = models.CharField(max_length=20, blank=True, null=True)
    moderator = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="assessments/", blank=True, null=True)
    memo = models.FileField(upload_to="assessments/memos/", blank=True, null=True)
    comment = models.TextField(blank=True)
    forward_to_moderator = models.BooleanField(default=False)
    moderator_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    qcto_notes = models.TextField(blank=True)


    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Submitted to Moderator", "Submitted to Moderator"),
        ("Returned for Changes", "Returned for Changes"),
        ("Approved by Moderator", "Approved by Moderator"),
        ("Submitted to ETQA", "Submitted to ETQA"),
        ("Approved by ETQA", "Approved by ETQA"),
        ("Rejected", "Rejected"),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Pending")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_assessments",
    )

    def __str__(self):
        return self.eisa_id

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

class QuestionBankEntry(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("standard", "Standard"),
        ("case_study", "Case Study"),
        ("mcq", "Multiple Choice"),
    ]

    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default="standard"
    )
    text = models.TextField()
    marks = models.PositiveIntegerField()
    case_study = models.ForeignKey(
        "CaseStudy",
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:30]}…"

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

class AssessmentCentre(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True)
    qualification_assigned = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name
