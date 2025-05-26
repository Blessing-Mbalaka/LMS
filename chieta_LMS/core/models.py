from django.db import models 
from django.contrib.auth.models import AbstractUser 
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
saqa_id              = models.CharField(max_length=20)
file                 = models.FileField(upload_to="assessments/")
memo                 = models.FileField(upload_to="assessments/memos/", blank=True, null=True)
comment              = models.TextField(blank=True)
forward_to_moderator = models.BooleanField(default=False)
internal             = models.CharField(
max_length=20,
choices=[
("Pending", "Pending"),
("Submitted to Moderator", "Submitted to Moderator"),
("Approved", "Approved"),
("Rejected", "Rejected"),
],
default="Pending"
)
moderator_notes      = models.TextField(blank=True)
created_at           = models.DateTimeField(auto_now_add=True)

def __str__(self):
    return self.eisa_id
class GeneratedQuestion(models.Model):
    assessment = models.ForeignKey(
Assessment,
related_name="questions",
on_delete=models.CASCADE
)
order      = models.PositiveIntegerField()
text       = models.TextField()
marks      = models.IntegerField()
case_study = models.TextField(blank=True, null=True)

class Meta:
    ordering = ['order']

def __str__(self):
    return f"{self.assessment.eisa_id} - Q{self.order}"


#Assessor Developer models
class Assessment(models.Model):
    eisa_id = models.CharField(max_length=20, unique=True)
    qualification = models.CharField(max_length=100)
    paper = models.CharField(max_length=10)
    moderator = models.CharField(max_length=100, blank=True)
    status = models.CharField(
    max_length=20,
    choices=[
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Submitted', 'Submitted'),
    ('Not Sent', 'Not Sent'),
    ],
default='Pending'
)
def __str__(self):
    return self.eisa_id
