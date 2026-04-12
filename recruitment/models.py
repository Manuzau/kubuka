from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_candidate = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def has_resume(self):
        return hasattr(self, 'resume')

class Resume(models.Model):
    candidate = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resume')
    file = models.FileField(upload_to='resumes/')
    parsed_text = models.TextField(blank=True, null=True)
    
    # Structured Data
    summary = models.TextField(verbose_name="Resumo Profissional", blank=True, null=True)
    skills = models.TextField(verbose_name="Habilidades e Competências", blank=True, null=True, help_text="Liste suas habilidades separadas por vírgula")
    experience = models.TextField(verbose_name="Experiência Profissional", blank=True, null=True)
    education = models.TextField(verbose_name="Formação Acadêmica", blank=True, null=True)
    languages = models.TextField(verbose_name="Idiomas", blank=True, null=True)

    score = models.FloatField(default=0.0)
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resume of {self.candidate.username}"

class Job(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título da Vaga")
    company = models.CharField(max_length=200, verbose_name="Empresa")
    description = models.TextField(verbose_name="Descrição")
    requirements = models.TextField(verbose_name="Requisitos")
    location = models.CharField(max_length=100, verbose_name="Localização")
    salary_range = models.CharField(max_length=100, blank=True, null=True, verbose_name="Faixa Salarial")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Relação ManyToMany com User para representar candidaturas
    applicants = models.ManyToManyField(User, related_name='applied_jobs', blank=True)

    def __str__(self):
        return f"{self.title} at {self.company}"
