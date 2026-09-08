from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet

user_list = UserViewSet.as_view({"get": "list", "post": "create"})
user_detail = UserViewSet.as_view({"get": "retrieve", "delete": "destroy"})

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("users/", user_list, name="user-list"),
    path("users/<int:pk>/", user_detail, name="user-detail"),
]
