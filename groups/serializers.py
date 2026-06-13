from rest_framework import serializers
from .models import Group, GroupMember, GroupInvite
from users.serializers import UserSerializer


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'avatar_url', 'invite_token', 'created_by', 'member_count', 'created_at']
        read_only_fields = ['id', 'invite_token', 'created_by', 'created_at']

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class GroupMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'role', 'joined_at']


class GroupInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupInvite
        fields = ['id', 'email', 'token', 'status', 'expires_at', 'created_at']