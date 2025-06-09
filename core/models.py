from django.db import models

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
    qualification = models.CharField(max_length=255)
    text          = models.TextField()
    marks         = models.IntegerField()
    case_study    = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.qualification}: {self.text[:50]}…"


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
