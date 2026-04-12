import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, TemplateView, DetailView, UpdateView
from django.urls import reverse_lazy
from .models import User, Resume, Job
from .forms import CandidateSignupForm, ResumeUploadForm, ResumeUpdateForm
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    
from django.contrib import messages

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

@login_required
def upload_resume(request):
    if not request.user.is_candidate:
        return redirect('home')

    # Check if resume already exists
    resume_instance = getattr(request.user, 'resume', None)

    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES, instance=resume_instance)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.candidate = request.user

            # Mock AI Processing
            # 1. Extract text (mock)
            try:
                reader = PyPDF2.PdfReader(resume.file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                resume.parsed_text = text
            except Exception as e:
                resume.parsed_text = f"Error extracting text: {str(e)}"

            # 2. Mock LLM Analysis
            resume.score = random.randint(50, 95)
            resume.feedback = "Ótimo currículo. Possui experiência relevante em Python e Django. Sugerimos focar mais em testes automatizados."

            resume.save()
            return redirect('upload_success')
    else:
        form = ResumeUploadForm(instance=resume_instance)

    return render(request, 'recruitment/upload.html', {'form': form})

@login_required
def admin_dashboard(request):
    if not request.user.is_staff and not request.user.is_admin:
        return redirect('home')

    resumes = Resume.objects.select_related('candidate').order_by('-score')
    return render(request, 'recruitment/dashboard.html', {'resumes': resumes})

def upload_success(request):
    return render(request, 'recruitment/upload_success.html')

@login_required
def profile_view(request):
    return render(request, 'recruitment/profile.html')

class ResumeUpdateView(LoginRequiredMixin, UpdateView):
    model = Resume
    form_class = ResumeUpdateForm
    template_name = 'recruitment/resume_edit.html'
    
    def get_queryset(self):
        # Ensure users can only edit their own resume
        return Resume.objects.filter(candidate=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('resume_detail', kwargs={'pk': self.object.pk})

class ResumeDetailView(LoginRequiredMixin, DetailView):
    model = Resume
    template_name = 'recruitment/resume_detail.html'
    context_object_name = 'resume'

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Resume.objects.none()
            
        # Admins can view all resumes
        if user.is_staff or getattr(user, 'is_admin', False):
            return Resume.objects.all()
            
        # Candidates can only view their own resume
        return Resume.objects.filter(candidate=user)

class JobListView(LoginRequiredMixin, ListView):
    model = Job
    template_name = 'recruitment/job_list.html'
    context_object_name = 'jobs'
    ordering = ['-created_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passar lista de IDs de jobs que o usuário já se candidatou
        context['applied_job_ids'] = self.request.user.applied_jobs.values_list('id', flat=True)
        return context

@login_required
def apply_job(request, pk):
    if not request.user.is_candidate:
        messages.error(request, 'Apenas candidatos podem se aplicar a vagas.')
        return redirect('job_list')
        
    job = get_object_or_404(Job, pk=pk)
    
    if not hasattr(request.user, 'resume'):
        messages.error(request, 'Você precisa cadastrar um currículo antes de se candidatar.')
        return redirect('upload_resume')
        
    if request.user in job.applicants.all():
        messages.info(request, 'Você já se candidatou a esta vaga.')
    else:
        job.applicants.add(request.user)
        messages.success(request, f'Candidatura realizada com sucesso para a vaga: {job.title}!')
        
    return redirect('job_list')
