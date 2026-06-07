import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Resume, Job, Application
from .serializers import UserSerializer, ResumeSerializer
from .notifications import notify_candidate


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or request.user.is_admin))


class IsRecruiterOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user:
            return False
        is_approved_recruiter = request.user.is_recruiter and getattr(request.user, 'recruiter_approved', False)
        return bool(is_approved_recruiter or request.user.is_staff or request.user.is_admin)


class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_staff or getattr(user, 'is_admin', False)):
            return Resume.objects.all().order_by('-score')
        return Resume.objects.filter(candidate=user)

    def perform_create(self, serializer):
        serializer.save(candidate=self.request.user)


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)


class ApplicationStatusView(APIView):
    """POST /api/application/<id>/update-status/ — pré-seleccionar, rejeitar ou agendar entrevista."""
    permission_classes = [IsRecruiterOrAdmin]

    def post(self, request, application_id):
        from django.utils.dateparse import parse_datetime
        try:
            application = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response({'error': f'Candidatura {application_id} não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # Recrutador só pode alterar candidaturas das suas próprias vagas
        is_admin = request.user.is_staff or request.user.is_admin
        if not is_admin and application.job.created_by != request.user:
            return Response({'error': 'Sem permissão para alterar esta candidatura.'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        valid = [s[0] for s in Application.STATUS_CHOICES]
        if new_status not in valid:
            return Response({'error': f'Status inválido. Valores aceites: {valid}'}, status=status.HTTP_400_BAD_REQUEST)

        update_fields = ['status', 'updated_at']
        application.status = new_status

        if new_status == 'interview_scheduled':
            interview_date_str = request.data.get('interview_date')
            if interview_date_str:
                interview_date = parse_datetime(interview_date_str)
                if interview_date:
                    application.interview_date = interview_date
                    update_fields.append('interview_date')
            application.candidate_availability_enabled = application.job.allow_candidate_unavailability
            update_fields.append('candidate_availability_enabled')

        recruiter_notes = request.data.get('recruiter_notes')
        if recruiter_notes is not None:
            application.recruiter_notes = recruiter_notes
            update_fields.append('recruiter_notes')

        application.save(update_fields=update_fields)
        notify_candidate(application)
        return Response({'success': True, 'application_id': application_id, 'status': application.status})


class RecruiterNotesView(APIView):
    """POST /api/application/<id>/notes/ — guardar notas internas do recrutador."""
    permission_classes = [IsRecruiterOrAdmin]

    def post(self, request, application_id):
        try:
            application = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response({'error': f'Candidatura {application_id} não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # Recrutador só pode adicionar notas às candidaturas das suas próprias vagas
        is_admin = request.user.is_staff or request.user.is_admin
        if not is_admin and application.job.created_by != request.user:
            return Response({'error': 'Sem permissão para aceder a esta candidatura.'}, status=status.HTTP_403_FORBIDDEN)

        notes = request.data.get('recruiter_notes', '')
        application.recruiter_notes = notes
        application.save(update_fields=['recruiter_notes', 'updated_at'])
        return Response({'success': True, 'application_id': application_id})
