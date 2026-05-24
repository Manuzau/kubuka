from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views, api_views
from .callback_views import (
    resume_ai_callback,
    resume_ai_result,
    application_score_result,
    application_update_status,
)

router = DefaultRouter()
router.register(r'api/resumes', api_views.ResumeViewSet, basename='resume-api')
router.register(r'api/profile', api_views.UserProfileViewSet, basename='profile-api')

urlpatterns = [
    # Páginas públicas / candidato
    path('', views.HomeView.as_view(), name='home'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('signup/recruiter/', views.RecruiterSignupView.as_view(), name='signup_recruiter'),
    path('login/', auth_views.LoginView.as_view(template_name='recruitment/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('upload/', views.upload_resume, name='upload_resume'),
    path('upload/success/', views.upload_success, name='upload_success'),
    path('profile/', views.profile_view, name='profile'),

    # Painel de administrador / recrutador
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/export/', views.export_applications_csv, name='export_applications_csv'),

    # Detalhe e edição de currículo
    path('resume/<int:pk>/', views.ResumeDetailView.as_view(), name='resume_detail'),
    path('resume/<int:pk>/edit/', views.ResumeUpdateView.as_view(), name='resume_edit'),

    # Vagas — candidato
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/apply/', views.apply_job, name='apply_job'),
    path('my-applications/', views.my_applications, name='my_applications'),

    # Vagas — recrutador
    path('recruiter/jobs/', views.JobRecruiterListView.as_view(), name='job_manage'),
    path('recruiter/jobs/new/', views.JobCreateView.as_view(), name='job_create'),
    path('recruiter/jobs/<int:pk>/edit/', views.JobUpdateView.as_view(), name='job_edit'),
    path('recruiter/jobs/<int:pk>/toggle/', views.job_toggle_active, name='job_toggle_active'),
    path('recruiter/jobs/<int:pk>/toggle/', views.job_toggle_active, name='job_toggle'),
    path('application/<int:pk>/update-status/', views.application_update_status_view, name='application_update_status_view'),

    # Callbacks internos do n8n
    path('internal/resume/<int:resume_id>/callback/', resume_ai_callback, name='resume_ai_callback'),
    path('api/resume/<int:resume_id>/ai-result/', resume_ai_result, name='resume_ai_result'),
    path('api/application/<int:application_id>/score-result/', application_score_result, name='application_score_result'),
    path('api/application/<int:application_id>/update-status/', application_update_status, name='application_update_status'),

    # API REST — acções do recrutador
    path('api/application/<int:application_id>/status/', api_views.ApplicationStatusView.as_view(), name='application_status_api'),
    path('api/application/<int:application_id>/notes/', api_views.RecruiterNotesView.as_view(), name='application_notes_api'),

    # API REST (DRF)
    path('', include(router.urls)),
]
