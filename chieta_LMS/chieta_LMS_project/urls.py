# chieta_LMS/chieta_LMS/urls.py

from django.contrib import admin
from django.urls import path, include
from chieta_LMS.views import (
    generate_paper,
    assessor_dashboard,
    view_assessment,
)

urlpatterns = [
 
    path('admin/', admin.site.urls),

    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),

    path('generate-paper/', generate_paper, name='generate_paper'),

    path('', include('chieta_lms.urls')),
]
