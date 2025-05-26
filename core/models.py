from django.db import models
from django.contrib.auth.models import User
from google import genai
from docx import Document
import fitz

# Gemini API key
genai_client = genai.Client(api_key="AIzaSyB2IyI2KVqDLexX2AdqPMP6aeja23aZCKw")

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

    # Combined internal + status logic into one field
    status = models.CharField(
        max_length=30,
        choices=[
            ("Pending", "Pending"),
            ("Submitted to Moderator", "Submitted to Moderator"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
            ("Submitted", "Submitted"),
            ("Not Sent", "Not Sent"),
        ],
        default="Pending"
    )

    def __str__(self):
        return self.eisa_id
