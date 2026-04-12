from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views, api_views

router = DefaultRouter()
router.register(r'api/resumes', api_views.ResumeViewSet, basename='resume-api')
router.register(r'api/profile', api_views.UserProfileViewSet, basename='profile-api')

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='recruitment/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('upload/', views.upload_resume, name='upload_resume'),
    path('upload/success/', views.upload_success, name='upload_success'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('resume/<int:pk>/', views.ResumeDetailView.as_view(), name='resume_detail'),
    path('resume/<int:pk>/edit/', views.ResumeUpdateView.as_view(), name='resume_edit'),
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/apply/', views.apply_job, name='apply_job'),

    # API
    path('', include(router.urls)),
]
