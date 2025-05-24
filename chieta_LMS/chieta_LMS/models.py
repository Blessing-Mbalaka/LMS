from django.db import models 
from django.contrib.auth.models import AbstractUser 
from django.db import models
from django.contrib.auth.models import User
from google import genai
from docx import Document
import fitz  


# Gemini API key
genai_client = genai.Client(api_key="AIzaSyB2IyI2KVqDLexX2AdqPMP6aeja23aZCKw")

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
