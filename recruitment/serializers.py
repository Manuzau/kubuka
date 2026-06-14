from rest_framework import serializers
from .models import User, Resume


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_candidate', 'is_recruiter')
        read_only_fields = ('is_candidate', 'is_recruiter')


class ResumeSerializer(serializers.ModelSerializer):
    candidate_name = serializers.ReadOnlyField(source='candidate.username')

    class Meta:
        model = Resume
        fields = ('id', 'candidate', 'candidate_name', 'file', 'score', 'feedback', 'created_at')
        read_only_fields = ('candidate', 'score', 'feedback', 'created_at')
