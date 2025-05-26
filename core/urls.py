
from django.contrib import admin
from django.urls import path, include
from core.views import (
    generate_paper,
    assessor_dashboard,
    view_assessment,
    upload_assessment,
    assessment_archive,
    assessor_reports,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # AJAX endpoint for your Generate-tool form
    path('generate-paper/', generate_paper, name='generate_paper'),

    # Direct dashboard & view pages
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),
    path('upload-assessment/', upload_assessment,        name='upload_assessment'),
    path('assessment-archive/', assessment_archive,      name='assessment_archive'),
    path('reports/', assessor_reports,                   name='assessor_reports'),
    path('generate-paper/', generate_paper,              name='generate_paper'),
    path('', include('chieta_LMS.urls')),
]




   
  
   
   
    
    

