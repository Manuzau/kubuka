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

_PWD_RESET_TEMPLATES = {
    'template_name': 'recruitment/password_reset.html',
    'email_template_name': 'recruitment/emails/password_reset_email.txt',
    'subject_template_name': 'recruitment/emails/password_reset_subject.txt',
}

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
    path('dashboard/kanban/', views.admin_dashboard, {'view_mode': 'kanban'}, name='dashboard_kanban'),
    path('dashboard/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('dashboard/export/', views.export_applications_csv, name='export_applications_csv'),

    # Detalhe e edição de currículo
    path('resume/<int:pk>/', views.ResumeDetailView.as_view(), name='resume_detail'),
    path('resume/<int:pk>/edit/', views.ResumeUpdateView.as_view(), name='resume_edit'),

    # Reset de palavra-passe
    path('password-reset/', auth_views.PasswordResetView.as_view(**_PWD_RESET_TEMPLATES), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='recruitment/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='recruitment/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='recruitment/password_reset_complete.html'), name='password_reset_complete'),

    # Vagas — candidato
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply_job, name='apply_job'),
    path('my-applications/', views.my_applications, name='my_applications'),

    # Notificações — candidato
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Candidatura — retirar / indisponibilidade
    path('application/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('application/<int:application_id>/unavailability/', views.submit_unavailability, name='submit_unavailability'),

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
