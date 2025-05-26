
from django.contrib import admin
from django.urls import path, include
from core.views import generate_paper, assessor_dashboard, view_assessment

urlpatterns = [
    path('admin/', admin.site.urls),

    # AJAX endpoint for your Generate-tool form
    path('generate-paper/', generate_paper, name='generate_paper'),

    # Direct dashboard & view pages
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),

    # All the rest of your app’s URLs (upload, archive, reports, generate page, etc.)
    path('', include('chieta_LMS.urls')),
]


