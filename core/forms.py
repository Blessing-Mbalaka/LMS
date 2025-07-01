from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Qualification, AssessmentCentre, CustomUser

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


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ['name', 'qualification_type', 'saqa_id', 'code', 'description', 'level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'qualificationType'
            }),
            'saqa_id': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'id': 'saqaId'
            }),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        }

class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email address", required=True)
    first_name = forms.CharField(label="First name", required=True)
    last_name = forms.CharField(label="Last name", required=True)

class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name",)

def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.username = user.email
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
        return user
