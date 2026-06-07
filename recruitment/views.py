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
from django.core.paginator import Paginator

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncWeek
from .models import User, Resume, Job, Application, AuditLog, Notification
from .forms import CandidateSignupForm, RecruiterSignupForm, ResumeUploadForm, ResumeUpdateForm, JobForm, ProfileEditForm, ApplicationForm
from .cv_processor import extract_text_from_pdf
from .ai_service import send_cv_to_n8n, send_application_for_scoring
from .notifications import notify_candidate
from .rate_limit import rate_limit

logger = logging.getLogger(__name__)


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _log_audit(request, action, detail=''):
    AuditLog.objects.create(
        user=request.user,
        action=action,
        detail=detail,
        ip_address=_get_ip(request) or None,
    )


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
        user.recruiter_approved = False  # Admin deve aprovar antes do primeiro acesso
        user.save()
        messages.success(
            self.request,
            'Conta de recrutador criada. Aguarde a aprovação do administrador antes de iniciar sessão.'
        )
        return super().form_valid(form)


@login_required
@rate_limit(rate='5/m', key='user')
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
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado com sucesso.')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'recruitment/profile.html', {'form': form})


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

def _build_dashboard_context(request):
    """Constrói o contexto partilhado para as vistas de dashboard (tabela e kanban)."""
    job_id = request.GET.get('job')
    min_score = request.GET.get('min_score', '')
    status_filter = request.GET.get('status', '')
    skills_filter = request.GET.get('skills', '').strip()

    applications = Application.objects.select_related(
        'candidate', 'candidate__resume', 'job'
    ).order_by('-similarity_score')

    is_recruiter_only = request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin)
    if is_recruiter_only:
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
        applications = applications.filter(candidate__resume__skills__icontains=skills_filter)

    jobs = Job.objects.filter(created_by=request.user) if is_recruiter_only else Job.objects.all()

    base_qs = Application.objects.filter(job__created_by=request.user) if is_recruiter_only else Application.objects.all()

    return {
        'applications': applications,
        'jobs': jobs,
        'current_job': job_id,
        'current_min_score': min_score,
        'current_status': status_filter,
        'current_skills': skills_filter,
        'total': base_qs.count(),
        'pre_selected': base_qs.filter(status='pre_selected').count(),
        'interviews': base_qs.filter(status='interview_scheduled').count(),
        'avg_score': round(base_qs.aggregate(avg=Avg('similarity_score'))['avg'] or 0, 1),
    }


@login_required
def admin_dashboard(request, view_mode=None):
    is_approved_recruiter = request.user.is_recruiter and request.user.recruiter_approved
    if not (request.user.is_staff or request.user.is_admin or is_approved_recruiter):
        if request.user.is_recruiter:
            messages.error(request, 'A sua conta de recrutador ainda não foi aprovada pelo administrador.')
        return redirect('home')

    if view_mode is None:
        view_mode = request.GET.get('view', 'table')

    context = _build_dashboard_context(request)
    context['view_mode'] = view_mode

    if view_mode == 'kanban':
        kanban = {'pending': [], 'pre_selected': [], 'interview_scheduled': [], 'rejected': []}
        for app in context['applications']:
            if app.status in kanban:
                kanban[app.status].append(app)
        context['kanban'] = kanban
        return render(request, 'recruitment/dashboard_kanban.html', context)

    # Tabela: paginar
    paginator = Paginator(context['applications'], 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    context['page_obj'] = page_obj
    context['applications'] = page_obj

    return render(request, 'recruitment/dashboard.html', context)


@login_required
def analytics_dashboard(request):
    is_approved_recruiter = request.user.is_recruiter and request.user.recruiter_approved
    if not (request.user.is_staff or request.user.is_admin or is_approved_recruiter):
        return redirect('home')

    is_recruiter_only = request.user.is_recruiter and not (request.user.is_staff or request.user.is_admin)
    base_qs = Application.objects.filter(job__created_by=request.user) if is_recruiter_only else Application.objects.all()

    # 1. Candidaturas por estado (donut)
    status_counts = {
        item['status']: item['count']
        for item in base_qs.values('status').annotate(count=Count('id'))
    }
    status_labels = ['Pendente', 'Pré-seleccionado', 'Rejeitado', 'Entrevista', 'Retirado']
    status_keys   = ['pending', 'pre_selected', 'rejected', 'interview_scheduled', 'withdrawn']
    status_data   = [status_counts.get(k, 0) for k in status_keys]
    status_colors = ['#FACC15', '#22C55E', '#EF4444', '#3B82F6', '#9CA3AF']

    # 2. Top vagas por número de candidaturas (bar horizontal)
    top_jobs = list(
        base_qs.values('job__title')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )
    job_labels = [item['job__title'] for item in top_jobs]
    job_data   = [item['count'] for item in top_jobs]

    # 3. Distribuição de scores (histogram — 10 buckets de 10 pts)
    buckets = [0] * 10
    for score in base_qs.exclude(similarity_score=0).values_list('similarity_score', flat=True):
        idx = min(int(score // 10), 9)
        buckets[idx] += 1
    score_labels = [f"{i*10}–{i*10+9}%" for i in range(10)]

    # 4. Candidaturas por semana (linha — últimas 8 semanas)
    from django.utils import timezone
    import datetime
    eight_weeks_ago = timezone.now() - datetime.timedelta(weeks=8)
    weekly_qs = (
        base_qs.filter(applied_at__gte=eight_weeks_ago)
        .annotate(week=TruncWeek('applied_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )
    weekly_labels = [item['week'].strftime('%d/%m') for item in weekly_qs]
    weekly_data   = [item['count'] for item in weekly_qs]

    total = base_qs.count()
    avg_score = round(base_qs.aggregate(avg=Avg('similarity_score'))['avg'] or 0, 1)
    conversion = round(status_counts.get('pre_selected', 0) / total * 100, 1) if total else 0

    return render(request, 'recruitment/analytics.html', {
        'total': total,
        'avg_score': avg_score,
        'conversion': conversion,
        'interviews': status_counts.get('interview_scheduled', 0),
        'status_labels': status_labels,
        'status_data': status_data,
        'status_colors': status_colors,
        'job_labels': job_labels,
        'job_data': job_data,
        'score_labels': score_labels,
        'score_buckets': buckets,
        'weekly_labels': weekly_labels,
        'weekly_data': weekly_data,
    })


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


class JobDetailView(LoginRequiredMixin, DetailView):
    model = Job
    template_name = 'recruitment/job_detail.html'
    context_object_name = 'job'

    def get_queryset(self):
        return Job.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_candidate:
            context['user_application'] = Application.objects.filter(
                candidate=self.request.user, job=self.object
            ).first()
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
    if existing and existing.status not in ('withdrawn',):
        messages.info(request, 'Já se candidatou a esta vaga.')
        return redirect('job_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            cv_file = form.cleaned_data.get('cv_file')

            if existing:
                # Re-candidatura após retirada
                application = existing
                application.status = 'pending'
                application.similarity_score = 0.0
                application.match_feedback = ''
                application.awaiting_score = False
                update_fields = ['status', 'similarity_score', 'match_feedback', 'awaiting_score', 'updated_at']
            else:
                application = Application(candidate=request.user, job=job, status='pending')
                update_fields = None  # vai usar .save() completo

            if cv_file:
                # Guardar e extrair texto do CV específico
                if application.cv_file:
                    try:
                        application.cv_file.delete(save=False)
                    except Exception:
                        pass
                application.cv_file = cv_file
                if update_fields:
                    update_fields.extend(['cv_file', 'cv_parsed_text'])
                try:
                    if update_fields:
                        application.save(update_fields=update_fields)
                    else:
                        application.save()
                    texto = extract_text_from_pdf(application.cv_file.path)
                    application.cv_parsed_text = texto or ''
                    application.save(update_fields=['cv_parsed_text'])
                except Exception as exc:
                    logger.error(f"[apply_job] Erro ao extrair CV específico: {exc}")
                    application.cv_parsed_text = ''
                    application.save(update_fields=['cv_parsed_text'])
            else:
                application.cv_file = None
                application.cv_parsed_text = ''
                if update_fields:
                    update_fields.extend(['cv_file', 'cv_parsed_text'])
                if update_fields:
                    application.save(update_fields=update_fields)
                else:
                    application.save()

            send_application_for_scoring(application)

            if existing:
                messages.success(request, f'Re-candidatura submetida com sucesso para: {job.title}!')
            else:
                messages.success(request, f'Candidatura submetida com sucesso para: {job.title}!')
            return redirect('job_list')
    else:
        form = ApplicationForm()

    return render(request, 'recruitment/apply_job.html', {
        'job': job,
        'form': form,
        'profile_resume': getattr(request.user, 'resume', None),
        'is_reapply': existing is not None,
    })


# ---------------------------------------------------------------------------
# Vagas — Recrutador
# ---------------------------------------------------------------------------

class JobRecruiterListView(LoginRequiredMixin, ListView):
    model = Job
    template_name = 'recruitment/job_manage.html'
    context_object_name = 'jobs'

    def dispatch(self, request, *args, **kwargs):
        is_approved = request.user.is_recruiter and request.user.recruiter_approved
        if not (is_approved or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores aprovados.')
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
        is_approved = request.user.is_recruiter and request.user.recruiter_approved
        if not (is_approved or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores aprovados.')
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
        is_approved = request.user.is_recruiter and request.user.recruiter_approved
        if not (is_approved or request.user.is_staff or request.user.is_admin):
            messages.error(request, 'Acesso restrito a recrutadores aprovados.')
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
    is_admin = request.user.is_staff or request.user.is_admin
    application = get_object_or_404(Application, pk=pk)

    # Recrutador só pode gerir candidaturas das suas próprias vagas
    if not is_admin and application.job.created_by != request.user:
        messages.error(request, 'Sem permissão para alterar esta candidatura.')
        return redirect('admin_dashboard')
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
        _log_audit(request, 'status_change',
                   f'Candidatura pk={pk} ({application.candidate.username} → {application.job.title}) → {label}.')
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

    _log_audit(request, 'export_csv',
               f'Exportação de {applications.count()} candidaturas.')

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
    is_admin = request.user.is_staff or request.user.is_admin
    job = get_object_or_404(Job, pk=pk) if is_admin else get_object_or_404(Job, pk=pk, created_by=request.user)
    job.is_active = not job.is_active
    job.save(update_fields=['is_active'])
    estado = 'activada' if job.is_active else 'desactivada'
    _log_audit(request, 'job_toggle', f'Vaga "{job.title}" (pk={job.pk}) {estado}.')
    messages.success(request, f'Vaga "{job.title}" {estado}.')
    return redirect('job_manage')
