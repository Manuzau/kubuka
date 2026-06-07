from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Resume, Job, Application, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Perfil KUBUKA', {'fields': ('is_candidate', 'is_recruiter', 'recruiter_approved', 'is_admin', 'company')}),
    )
    list_display = ('username', 'email', 'is_candidate', 'is_recruiter', 'recruiter_approved', 'is_staff', 'is_admin')
    list_filter = ('is_candidate', 'is_recruiter', 'recruiter_approved', 'is_staff', 'is_admin')
    actions = ['approve_recruiters', 'revoke_recruiters']

    @admin.action(description='Aprovar recrutadores seleccionados')
    def approve_recruiters(self, request, queryset):
        updated = queryset.filter(is_recruiter=True).update(recruiter_approved=True)
        self.message_user(request, f'{updated} recrutador(es) aprovado(s).')

    @admin.action(description='Revogar aprovação de recrutadores seleccionados')
    def revoke_recruiters(self, request, queryset):
        updated = queryset.filter(is_recruiter=True).update(recruiter_approved=False)
        self.message_user(request, f'{updated} recrutador(es) com aprovação revogada.')


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'score', 'ai_processed', 'created_at')
    list_filter = ('ai_processed',)
    search_fields = ('candidate__username', 'candidate__email')
    readonly_fields = ('created_at',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'is_active', 'min_score_required', 'created_by', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'company', 'location')
    readonly_fields = ('created_at',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'similarity_score', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('candidate__username', 'job__title')
    readonly_fields = ('applied_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'ip_address', 'detail')
    list_filter = ('action',)
    search_fields = ('user__username', 'detail')
    readonly_fields = ('timestamp', 'user', 'action', 'detail', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
