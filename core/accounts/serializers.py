from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_superuser", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User(username=validated_data["username"], email=validated_data.get("email", ""), is_staff=True)
        user.set_password(validated_data["password"])
        user.save()
        return user
