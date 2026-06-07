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

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file
        if not file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Apenas ficheiros PDF são aceites.')
        if hasattr(file, 'content_type') and file.content_type not in ('application/pdf', 'application/x-pdf'):
            raise forms.ValidationError('O tipo do ficheiro não é PDF válido.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('O ficheiro não pode exceder 5 MB.')
        return file


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


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'company')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-2 border rounded'}),
            'company': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
        }


class ApplicationForm(forms.Form):
    cv_file = forms.FileField(
        required=False,
        label="CV específico para esta vaga (opcional)",
        help_text="Se não carregar nenhum ficheiro, será usado o CV do seu perfil.",
    )

    def clean_cv_file(self):
        file = self.cleaned_data.get('cv_file')
        if not file:
            return file
        if not file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Apenas ficheiros PDF são aceites.')
        if hasattr(file, 'content_type') and file.content_type not in ('application/pdf', 'application/x-pdf'):
            raise forms.ValidationError('O tipo do ficheiro não é PDF válido.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('O ficheiro não pode exceder 5 MB.')
        return file


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = (
            'title', 'company', 'description', 'requirements',
            'location', 'salary_range', 'deadline',
            'contact_email_primary', 'contact_email_secondary',
            'allow_candidate_unavailability', 'min_score_required', 'is_active',
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'company': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full p-2 border rounded'}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'class': 'w-full p-2 border rounded'}),
            'location': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'salary_range': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'deadline': forms.DateInput(attrs={'class': 'w-full p-2 border rounded', 'type': 'date'}),
            'contact_email_primary': forms.EmailInput(attrs={'class': 'w-full p-2 border rounded'}),
            'contact_email_secondary': forms.EmailInput(attrs={'class': 'w-full p-2 border rounded'}),
            'min_score_required': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded', 'min': 0, 'max': 100, 'step': 5,
            }),
        }

    def clean_contact_email_primary(self):
        value = self.cleaned_data.get('contact_email_primary')
        if not value:
            raise forms.ValidationError('O email de contacto principal é obrigatório.')
        return value
