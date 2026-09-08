from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsSuperUserOnly
from .models import User
from .serializers import UserSerializer, CreateUserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    Hanya superuser yang boleh create/delete user (BRD poin 1).
    List/retrieve tetap dibatasi authenticated user.
    """
    queryset = User.objects.all()

    def get_serializer_class(self):
        return CreateUserSerializer if self.action == "create" else UserSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsSuperUserOnly()]
        return [IsAuthenticated()]
