
from django.contrib import admin
from django.urls import path, include
from .views import generate_paper


urlpatterns = [
    path('admin/', admin.site.urls),
    path("generate-paper/", generate_paper, name="generate_paper"),
    path("chieta/", include("chieta_lms.urls")),

]
