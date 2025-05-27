from django.contrib import admin
from django.urls import path, include
from core.views import (
    generate_tool,
    assessor_dashboard,
    view_assessment,
    upload_assessment,
    assessment_archive,
    assessor_reports,
)


urlpatterns = [
    
    path('', assessor_dashboard, name='home'),
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),
    path('upload_assessment/', upload_assessment,        name='upload_assessment'),
    path('assessor-developer/assessment_archive/', assessment_archive, name='assessment_archive'),
    path('reports/', assessor_reports,                   name='assessor_reports'),
    path('generate-paper/', generate_tool,              name='generate_tool'),
    
]




   
  