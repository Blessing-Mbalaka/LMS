# core/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Qualification
from .models import AssessmentCentre
User = get_user_model()


class CustomUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'qualification', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
        }


class AssessmentCentreForm(forms.ModelForm):
    class Meta:
        model = AssessmentCentre
        fields = ['name', 'location', 'qualification_assigned']

        from .models import Qualification

class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ['name', 'qualification_type', 'saqa_id', 'code', 'description', 'level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'qualificationType'  # 👈 JS will hook onto this
            }),
            'saqa_id': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'id': 'saqaId'  # 👈 JS will update this
            }),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        }