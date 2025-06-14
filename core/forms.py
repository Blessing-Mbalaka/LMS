# core/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Qualification
from .models import AssessmentCentre
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

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

        User = get_user_model()


#User creation form 
# core/forms.py
class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email address", required=True)

    class Meta:
        model = User
        fields = ("email",)  

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        # override save so that username is set to email if your user model still requires username
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        # if your AUTH_USER_MODEL still has a username field, you can do:
        if hasattr(user, "username"):
            user.username = user.email
        if commit:
            user.save()
        return user
