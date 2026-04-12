from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import User, Resume
from .serializers import UserSerializer, ResumeSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or request.user.is_admin))

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_staff or getattr(user, 'is_admin', False)):
            return Resume.objects.all().order_by('-score')
        return Resume.objects.filter(candidate=user)

    def perform_create(self, serializer):
        # We handle logic similar to the template view for AI mock processing here if needed
        # but for simplicity, we'll assume the same logic applies.
        # In a real app, this logic would be in a service layer.
        serializer.save(candidate=self.request.user)

class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
