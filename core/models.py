from django.db import models
from django.contrib.auth.models import User

class Assessment(models.Model):
    eisa_id              = models.CharField(max_length=20, unique=True)
    qualification        = models.CharField(max_length=100)
    paper                = models.CharField(max_length=10)
    saqa_id              = models.CharField(max_length=20, blank=True, null=True)
    moderator            = models.CharField(max_length=100, blank=True)
    file                 = models.FileField(upload_to="assessments/", blank=True, null=True)
    memo                 = models.FileField(upload_to="assessments/memos/", blank=True, null=True)
    comment              = models.TextField(blank=True)
    forward_to_moderator = models.BooleanField(default=False)
    moderator_notes      = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    qcto_notes           = models.TextField(blank=True)

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

    def __str__(self):
        return self.eisa_id


class CaseStudy(models.Model):
    title   = models.CharField(max_length=200)
    content = models.TextField()
    
    
    def __str__(self):
        return self.title


class GeneratedQuestion(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        related_name='generated_questions',
        on_delete=models.CASCADE
    )
    text       = models.TextField()
    marks      = models.PositiveIntegerField()
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
        ("standard",   "Standard"),
        ("case_study", "Case Study"),
        ("mcq",        "Multiple Choice"),
    ]

    qualification   = models.CharField(max_length=255)
    question_type   = models.CharField(
                        max_length=20,
                        choices=QUESTION_TYPE_CHOICES,
                        default="standard"
                     )
    text            = models.TextField()
    marks           = models.PositiveIntegerField()
    # only used when question_type == "case_study"
    case_study      = models.ForeignKey(
                        "CaseStudy",
                        on_delete=models.SET_NULL,
                        null=True, blank=True
                     )
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:30]}…"

class MCQOption(models.Model):
    question = models.ForeignKey(
                  QuestionBankEntry,
                  on_delete=models.CASCADE,
                  limit_choices_to={"question_type": "mcq"},
                  related_name="options"
               )
    text     = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✗'} {self.text}"


class ChecklistItem(models.Model):
    label     = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class Feedback(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    to_user    = models.CharField(max_length=100)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Revised", "Revised"),
        ("Completed", "Completed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.assessment.eisa_id} → {self.to_user}"

#User Admin
# models.py

class Qualification(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ASSESSOR', 'Assessor'),
        ('MODERATOR', 'Moderator'),
        ('QCTO', 'QCTO'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

    #temporary assessmentcentre
    class AssessmentCentre(models.Model):
        name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    responsible_person = models.CharField(max_length=100)
    qualification_assigned = models.ForeignKey(
        Qualification, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='centres'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    #temporary user rofile model
    class UserProfile(models.Model):
        user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)
    qualification = models.ForeignKey('Qualification', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.BooleanField(default=True)