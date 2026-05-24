import csv
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, TemplateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse

from django.db.models import Avg, Count
from .models import User, Resume, Job, Application
from .forms import CandidateSignupForm, RecruiterSignupForm, ResumeUploadForm, ResumeUpdateForm, JobForm
from .cv_processor import extract_text_from_pdf
from .ai_service import send_cv_to_n8n, send_application_for_scoring
from .notifications import notify_candidate
from .models import Notification

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = 'recruitment/index.html'

    def get_template_names(self):
        if self.request.user.is_authenticated:
            return ['recruitment/home_authenticated.html']
        return ['recruitment/index.html']


class SignupView(CreateView):
    model = User
    form_class = CandidateSignupForm
    template_name = 'recruitment/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_candidate = True
        user.save()
        return super().form_valid(form)


class RecruiterSignupView(CreateView):
    model = User
    form_class = RecruiterSignupForm
    template_name = 'recruitment/signup_recruiter.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_recruiter = True
        user.save()
        messages.success(
            self.request,
            'Conta de recrutador criada com sucesso. Pode agora iniciar sessão.'
        )
        return super().form_valid(form)


@login_required
def upload_resume(request):
    if not request.user.is_candidate:
        return redirect('home')

    resume_instance = getattr(request.user, 'resume', None)

    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES, instance=resume_instance)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.candidate = request.user
            resume.ai_processed = False

            # Extrair texto com pdfplumber + OCR
            try:
                pdf_path = resume.file.path if resume_instance else None
                # Precisamos guardar primeiro para ter o path do ficheiro
                resume.save()
                texto = extract_text_from_pdf(resume.file.path)
                resume.parsed_text = texto if texto else ''
                resume.save(update_fields=['parsed_text'])
            except Exception as exc:
                logger.error(f"[upload_resume] Erro ao extrair texto: {exc}")
                resume.parsed_text = ''
                resume.save(update_fields=['parsed_text'])

            # Enviar ao n8n para análise (non-blocking; falha silenciosa)
            send_cv_to_n8n(resume)

            return redirect('upload_success')
    else:
        form = ResumeUploadForm(instance=resume_instance)

    return render(request, 'recruitment/upload.html', {'form': form})


@login_required
def upload_success(request):
    return render(request, 'recruitment/upload_success.html')


@login_required
def profile_view(request):
    return render(request, 'recruitment/profile.html')


# ---------------------------------------------------------------------------
# Candidaturas do candidato
# ---------------------------------------------------------------------------

@login_required
def my_applications(request):
    if not request.user.is_candidate:
        return redirect('home')
    applications = (
        Application.objects
        .filter(candidate=request.user)
        .select_related('job')
        .order_by('-applied_at')
    )
    return render(request, 'recruitment/my_applications.html', {'applications': applications})


# ---------------------------------------------------------------------------
# Candidatura — Retirar / Indisponibilidade
# ---------------------------------------------------------------------------

@login_required
def withdraw_application(request, application_id):
    if not request.user.is_candidate:
        return redirect('home')
    application = get_object_or_404(Application, pk=application_id, candidate=request.user)
    if application.status != 'pending':
        messages.error(request, 'Não é possível retirar uma candidatura que já está em processo avançado.')
        return redirect('job_list')
    application.status = 'withdrawn'
    application.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'A sua candidatura foi retirada com sucesso.')
    return redirect('job_list')


@login_required
def submit_unavailability(request, application_id):
    if not request.user.is_candidate:
        return redirect('home')
    application = get_object_or_404(Application, pk=application_id, candidate=request.user)
    if not application.candidate_availability_enabled:
        messages.error(request, 'Esta opção não está disponível para esta candidatura.')
        return redirect('my_applications')
    if application.status != 'interview_scheduled':
        messages.error(request, 'Só pode indicar indisponibilidade para entrevistas agendadas.')
        return redirect('my_applications')
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Por favor indique o motivo da indisponibilidade.')
        return redirect('my_applications')
    application.candidate_unavailability_reason = reason
    application.availability_responded = True
    application.save(update_fields=['candidate_unavailability_reason', 'availability_responded', 'updated_at'])
    messages.success(request, 'A sua indisponibilidade foi registada. O recrutador será notificado.')
    return redirect('my_applications')


# ---------------------------------------------------------------------------
# Notificações — Candidato
# ---------------------------------------------------------------------------

@login_required
def notifications_view(request):
    if not request.user.is_candidate:
        return redirect('home')
    notifications = Notification.objects.filter(user=request.user).select_related('application__job')
    # Mark all as read on visit
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'recruitment/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, pk):
    if request.method == 'POST':
        Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect('notifications')


# ---------------------------------------------------------------------------
# Dashboard — Admin / Recrutador
# ---------------------------------------------------------------------------

@login_required
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_admin or request.user.is_recruiter):
        return redirect('home')

    # Filtros opcionais
    job_id = request.GET.get('job')
    min_score = request.GET.get('min_score', '')
    status_filter = request.GET.get('status', '')
    skills_filter = request.GET.get('skills', '').strip()

    applications = Application.objects.select_related(
        'candidate', 'candidate__resume', 'job'
    ).order_by('-similarity_score')

    # Recrutadores só vêem candidaturas das suas vagas
    if request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin):
        applications = applications.filter(job__created_by=request.user)

    if job_id:
        applications = applications.filter(job_id=job_id)
    if min_score:
        try:
            applications = applications.filter(similarity_score__gte=float(min_score))
        except ValueError:
            pass
    if status_filter:
        applications = applications.filter(status=status_filter)
    if skills_filter:
        applications = applications.filter(
            candidate__resume__skills__icontains=skills_filter
        )

    # Vagas disponíveis para o filtro
    if request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin):
        jobs = Job.objects.filter(created_by=request.user)
    else:
        jobs = Job.objects.all()

    base_qs = Application.objects.all()
    if request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin):
        base_qs = base_qs.filter(job__created_by=request.user)

    total = base_qs.count()
    pre_selected = base_qs.filter(status='pre_selected').count()
    interviews = base_qs.filter(status='interview_scheduled').count()
    avg_score = round(base_qs.aggregate(avg=Avg('similarity_score'))['avg'] or 0, 1)

    context = {
        'applications': applications,
        'jobs': jobs,
        'current_job': job_id,
        'current_min_score': min_score,
        'current_status': status_filter,
        'current_skills': skills_filter,
        'total': total,
        'pre_selected': pre_selected,
        'interviews': interviews,
        'avg_score': avg_score,
    }
    return render(request, 'recruitment/dashboard.html', context)


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class ResumeUpdateView(LoginRequiredMixin, UpdateView):
    model = Resume
    form_class = ResumeUpdateForm
    template_name = 'recruitment/resume_edit.html'

    def get_queryset(self):
        return Resume.objects.filter(candidate=self.request.user)

    def get_success_url(self):
        return reverse_lazy('resume_detail', kwargs={'pk': self.object.pk})


class ResumeDetailView(LoginRequiredMixin, DetailView):
    model = Resume
    template_name = 'recruitment/resume_detail.html'
    context_object_name = 'resume'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_admin or user.is_recruiter:
            return Resume.objects.all()
        return Resume.objects.filter(candidate=user)


# ---------------------------------------------------------------------------
# Vagas — Candidato
# ---------------------------------------------------------------------------

class JobListView(LoginRequiredMixin, ListView):
    model = Job
    template_name = 'recruitment/job_list.html'
    context_object_name = 'jobs'
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            apps_by_job = {
                app.job_id: app
                for app in Application.objects.filter(candidate=self.request.user)
            }
            for job in context['jobs']:
                job.user_application = apps_by_job.get(job.pk)
        return context


@login_required
def apply_job(request, pk):
    if not request.user.is_candidate:
        messages.error(request, 'Apenas candidatos podem candidatar-se a vagas.')
        return redirect('job_list')

    job = get_object_or_404(Job, pk=pk, is_active=True)

    if not hasattr(request.user, 'resume'):
        messages.error(request, 'Precisa de submeter um currículo antes de se candidatar.')
        return redirect('upload_resume')

    existing = Application.objects.filter(candidate=request.user, job=job).first()
    if existing:
        if existing.status == 'withdrawn':
            existing.status = 'pending'
            existing.save(update_fields=['status', 'updated_at'])
            send_application_for_scoring(existing)
            messages.success(request, f'Re-candidatura submetida com sucesso para: {job.title}!')
        else:
            messages.info(request, 'Já se candidatou a esta vaga.')
    else:
        application = Application.objects.create(
            candidate=request.user,
            job=job,
            status='pending',
        )
        send_application_for_scoring(application)
        messages.success(request, f'Candidatura submetida com sucesso para: {job.title}!')

    return redirect('job_list')


# ---------------------------------------------------------------------------
# Vagas — Recrutador
# ---------------------------------------------------------------------------

class JobRecruiterListView(LoginRequiredMixin, ListView):
    model = Job
    template_name = 'recruitment/job_manage.html'
    context_object_name = 'jobs'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Job.objects.annotate(application_count=Count('applications'))
        if self.request.user.is_staff or self.request.user.is_admin:
            return qs.order_by('-created_at')
        return qs.filter(created_by=self.request.user).order_by('-created_at')


class JobCreateView(LoginRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = 'recruitment/job_form.html'
    success_url = reverse_lazy('job_manage')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Vaga criada com sucesso.')
        return super().form_valid(form)


class JobUpdateView(LoginRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = 'recruitment/job_form.html'
    success_url = reverse_lazy('job_manage')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_admin:
            return Job.objects.all()
        return Job.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Vaga actualizada com sucesso.')
        return super().form_valid(form)


@login_required
def application_update_status_view(request, pk):
    """View HTML para pré-seleccionar ou rejeitar uma candidatura."""
    if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
        messages.error(request, 'Acesso restrito a recrutadores.')
        return redirect('home')

    from django.utils.dateparse import parse_datetime
    application = get_object_or_404(Application, pk=pk)
    new_status = request.POST.get('status')
    valid = [s[0] for s in Application.STATUS_CHOICES]

    if new_status in valid:
        update_fields = ['status', 'updated_at']
        application.status = new_status

        if new_status == 'interview_scheduled':
            interview_date_str = request.POST.get('interview_date')
            if interview_date_str:
                interview_date = parse_datetime(interview_date_str)
                if interview_date:
                    application.interview_date = interview_date
                    update_fields.append('interview_date')
            application.candidate_availability_enabled = application.job.allow_candidate_unavailability
            update_fields.append('candidate_availability_enabled')

        recruiter_notes = request.POST.get('recruiter_notes')
        if recruiter_notes is not None:
            application.recruiter_notes = recruiter_notes
            update_fields.append('recruiter_notes')

        application.save(update_fields=update_fields)
        notify_candidate(application)
        label = application.get_status_display()
        messages.success(request, f'Candidatura de {application.candidate.username} marcada como: {label}.')
    else:
        messages.error(request, 'Estado inválido.')

    return redirect('admin_dashboard')


@login_required
def export_applications_csv(request):
    if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
        return redirect('home')

    applications = Application.objects.select_related('candidate', 'candidate__resume', 'job').order_by('-similarity_score')
    if request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin):
        applications = applications.filter(job__created_by=request.user)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="candidaturas.csv"'
    response.write('﻿')  # BOM for Excel UTF-8

    writer = csv.writer(response)
    writer.writerow(['Candidato', 'Email', 'Vaga', 'Empresa', 'Score (%)', 'Estado', 'Data de Candidatura'])
    for app in applications:
        writer.writerow([
            app.candidate.username,
            app.candidate.email,
            app.job.title,
            app.job.company,
            app.similarity_score,
            app.get_status_display(),
            app.applied_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@login_required
def job_toggle_active(request, pk):
    if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
        return redirect('home')
    job = get_object_or_404(Job, pk=pk)
    job.is_active = not job.is_active
    job.save(update_fields=['is_active'])
    estado = 'activada' if job.is_active else 'desactivada'
    messages.success(request, f'Vaga "{job.title}" {estado}.')
    return redirect('job_manage')
