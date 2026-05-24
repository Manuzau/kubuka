from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Resume, Job


class CandidateSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class RecruiterSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ('file',)


class ResumeUpdateForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ('summary', 'experience', 'education', 'skills', 'languages')
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-2 border rounded'}),
            'experience': forms.Textarea(attrs={'rows': 6, 'class': 'w-full p-2 border rounded'}),
            'education': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-2 border rounded'}),
            'skills': forms.Textarea(attrs={'rows': 3, 'class': 'w-full p-2 border rounded'}),
            'languages': forms.Textarea(attrs={'rows': 2, 'class': 'w-full p-2 border rounded'}),
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ('title', 'company', 'description', 'requirements', 'location', 'salary_range', 'is_active')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'company': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full p-2 border rounded'}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'class': 'w-full p-2 border rounded'}),
            'location': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'salary_range': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
        }
