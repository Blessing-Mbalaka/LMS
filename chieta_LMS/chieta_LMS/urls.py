
from django.contrib import admin
from django.urls import path, include
from .views import generate_paper
from .views import assessor_dashboard, view_assessment


urlpatterns = [
    path('admin/', admin.site.urls),
    path("generate-paper/", generate_paper, name="generate_paper"),
    path("chieta/", include("chieta_lms.urls")),
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/str:eisa_id/', view_assessment, name='view_assessment'),

]




