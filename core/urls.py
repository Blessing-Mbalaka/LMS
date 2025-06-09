from django.contrib import admin
from django.urls import path, include
from core.views import (
    generate_tool_page,
    generate_tool,
    assessor_dashboard,
    view_assessment,
    upload_assessment,
    assessment_archive,
    assessor_reports,
    submit_generated_paper,
    add_question,
    add_case_study,
    add_feedback,
    moderator_developer_dashboard,
    moderate_assessment,
    checklist_stats,
    toggle_checklist_item, qcto_dashboard, qcto_moderate_assessment, qcto_compliance,qcto_assessment_review,
    qcto_archive,

)

urlpatterns = [
    path('', assessor_dashboard, name='home'),
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),
    path('upload_assessment/', upload_assessment, name='upload_assessment'),
    path('assessor-developer/assessment_archive/', assessment_archive, name='assessment_archive'),
    path('reports/', assessor_reports, name='assessor_reports'),
    path('generate-paper/', generate_tool_page, name='generate_tool_page'),
    path('api/generate-paper/', generate_tool, name='generate_tool'),
    path("submit-generated-paper/", submit_generated_paper, name="submit_generated_paper"),
    path('add-question/', add_question, name='add_question'), 
    path('add-case-study/', add_case_study, name='add_case_study'),
    path("moderator/", moderator_developer_dashboard, name="moderator_developer"),
    path("moderator/<str:eisa_id>/moderate/", moderate_assessment, name="moderate_assessment"),
    path("moderator/<str:eisa_id>/feedback/add/", add_feedback, name="add_feedback"),
    path( "moderator/checklist/<int:item_id>/toggle/", toggle_checklist_item,name="toggle_checklist_item"),
    path( "moderator/checklist/stats/", checklist_stats,name="checklist_stats"),
    path('qcto/dashboard/', qcto_dashboard, name='qcto_dashboard'),
    path('qcto/<str:eisa_id>/moderate/', qcto_moderate_assessment, name='qcto_moderate_assessment'),
     path('qcto/compliance/', qcto_compliance, name='qcto_compliance'),
    path('qcto/review/', qcto_assessment_review, name='qcto_assessment_review'),
    path('qcto/archive/', qcto_archive, name='qcto_archive'),
    
]

    





   
  