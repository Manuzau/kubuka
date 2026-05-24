from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_candidate = models.BooleanField(default=False)
    is_recruiter = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def has_resume(self):
        return hasattr(self, 'resume')


class Resume(models.Model):
    candidate = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resume')
    file = models.FileField(upload_to='resumes/')
    parsed_text = models.TextField(blank=True, null=True)

    summary = models.TextField(verbose_name="Resumo Profissional", blank=True, null=True)
    skills = models.TextField(verbose_name="Habilidades e Competências", blank=True, null=True)
    experience = models.TextField(verbose_name="Experiência Profissional", blank=True, null=True)
    education = models.TextField(verbose_name="Formação Académica", blank=True, null=True)
    languages = models.TextField(verbose_name="Idiomas", blank=True, null=True)

    score = models.FloatField(default=0.0)
    feedback = models.TextField(blank=True, null=True)
    ai_processed = models.BooleanField(default=False)
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
    is_active = models.BooleanField(default=True, verbose_name="Vaga Activa")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='jobs_created', verbose_name="Criado por"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('pre_selected', 'Pré-seleccionado'),
        ('rejected', 'Rejeitado'),
    ]

    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    similarity_score = models.FloatField(default=0.0)
    match_feedback = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job')

    def __str__(self):
        return f"{self.candidate.username} → {self.job.title} ({self.status})"
