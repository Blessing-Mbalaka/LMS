from django.db import models 
from django.contrib.auth.models import AbstractUser 
from django.db import models
from django.contrib.auth.models import User
from google import genai
from docx import Document
import fitz  # PyMuPDf


# Gemini API key
genai_client = genai.Client(api_key="AIzaSyB2IyI2KVqDLexX2AdqPMP6aeja23aZCKw")
