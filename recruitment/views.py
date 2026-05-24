import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, TemplateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages

from .models import User, Resume, Job, Application
from .forms import CandidateSignupForm, RecruiterSignupForm, ResumeUploadForm, ResumeUpdateForm, JobForm
from .cv_processor import extract_text_from_pdf
from .ai_service import send_cv_to_n8n, send_application_for_scoring

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

    context = {
        'applications': applications,
        'jobs': jobs,
        'selected_job': job_id,
        'min_score': min_score,
        'status_filter': status_filter,
        'skills_filter': skills_filter,
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
        applied_ids = Application.objects.filter(
            candidate=self.request.user
        ).values_list('job_id', flat=True)
        context['applied_job_ids'] = set(applied_ids)
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

    if Application.objects.filter(candidate=request.user, job=job).exists():
        messages.info(request, 'Já se candidatou a esta vaga.')
    else:
        application = Application.objects.create(
            candidate=request.user,
            job=job,
            status='pending',
        )
        # Calcular score de correspondência (non-blocking)
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
        if self.request.user.is_staff or self.request.user.is_admin:
            return Job.objects.all().order_by('-created_at')
        return Job.objects.filter(created_by=self.request.user).order_by('-created_at')


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

    application = get_object_or_404(Application, pk=pk)
    new_status = request.POST.get('status')
    valid = [s[0] for s in Application.STATUS_CHOICES]

    if new_status in valid:
        application.status = new_status
        application.save(update_fields=['status'])
        label = {'pre_selected': 'Pré-seleccionado', 'rejected': 'Rejeitado', 'pending': 'Pendente'}.get(new_status, new_status)
        messages.success(request, f'Candidatura de {application.candidate.username} marcada como: {label}.')
    else:
        messages.error(request, 'Estado inválido.')

    return redirect('admin_dashboard')


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
