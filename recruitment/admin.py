from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Resume, Job, Application


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Perfil KUBUKA', {'fields': ('is_candidate', 'is_recruiter', 'is_admin')}),
    )
    list_display = ('username', 'email', 'is_candidate', 'is_recruiter', 'is_staff', 'is_admin')
    list_filter = ('is_candidate', 'is_recruiter', 'is_staff', 'is_admin')


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'score', 'ai_processed', 'created_at')
    list_filter = ('ai_processed',)
    search_fields = ('candidate__username', 'candidate__email')
    readonly_fields = ('created_at',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'company', 'location')
    readonly_fields = ('created_at',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'similarity_score', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('candidate__username', 'job__title')
    readonly_fields = ('applied_at',)
