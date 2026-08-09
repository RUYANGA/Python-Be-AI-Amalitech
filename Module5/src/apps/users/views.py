from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import LoginSerializer, LogoutSerializer, RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterSerializer},
        summary="Register a new user",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginSerializer},
        summary="Login and receive JWT tokens",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={205: None},
        summary="Logout and blacklist refresh token",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_205_RESET_CONTENT)
