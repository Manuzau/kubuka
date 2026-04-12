from rest_framework import serializers
from .models import User, Resume

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_candidate', 'is_admin')
        read_only_fields = ('is_candidate', 'is_admin')

class ResumeSerializer(serializers.ModelSerializer):
    candidate_name = serializers.ReadOnlyField(source='candidate.username')

    class Meta:
        model = Resume
        fields = ('id', 'candidate', 'candidate_name', 'file', 'parsed_text', 'score', 'feedback', 'created_at')
        read_only_fields = ('candidate', 'parsed_text', 'score', 'feedback', 'created_at')
