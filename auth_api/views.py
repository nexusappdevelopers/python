from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import DeviceDetails, STATE_ACTIVE
from api.utils import create_response

from .serializers import LoginSerializer, SignupSerializer, TokenRefreshSerializer


class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return create_response(
                data=serializer.data,
                message="OTP has been sent to your email account.",
                status_code=status.HTTP_201_CREATED,
            )
        first_error_message = next(iter(serializer.errors.values()))[0]
        return create_response(
            error=first_error_message,
            message="Validation errors",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            if user.is_verified and user.state_id == STATE_ACTIVE:
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token

                # Store device details if provided
                device_token = request.data.get("device_token")
                if device_token:
                    existing = (
                        DeviceDetails.objects.filter(created_by_id=user.id).order_by("-updated_at").first()
                    )
                    if existing:
                        existing.device_token = device_token
                        existing.device_name = request.data.get("device_name", "")
                        existing.device_type = request.data.get("device_type", 1)
                        existing.type_id = 1
                        existing.device_os = request.data.get("device_os", "")
                        existing.app_version = request.data.get("app_version", "")
                        existing.save()
                    else:
                        DeviceDetails.objects.create(
                            created_by_id=user.id,
                            device_token=device_token,
                            device_name=request.data.get("device_name", ""),
                            device_type=request.data.get("device_type", 1),
                            type_id=1,
                            device_os=request.data.get("device_os", ""),
                            app_version=request.data.get("app_version", ""),
                        )

                return create_response(
                    data={
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "contact_no": user.contact_no,
                        "is_verified": user.is_verified,
                        "coins": user.coins,
                        "free_analysis": user.free_analysis,
                        "access_token": str(access_token),
                        "refresh_token": str(refresh),
                    },
                    message="Login successful",
                    status_code=status.HTTP_200_OK,
                )

        # Invalid -> mirror repo behavior (flags may be embedded)
        errors = serializer.errors
        flags = None
        message = "Invalid email or password."
        status_code_resp = status.HTTP_401_UNAUTHORIZED

        if isinstance(errors, dict):
            non_field = errors.get("non_field_errors")
            if isinstance(non_field, list) and non_field and isinstance(non_field[0], dict):
                flags = non_field[0].get("flags")
                message = non_field[0].get("detail", message)
                status_code_resp = status.HTTP_403_FORBIDDEN
            elif isinstance(non_field, list) and non_field:
                message = str(non_field[0])
            elif "flags" in errors or "detail" in errors:
                try:
                    top_detail = errors.get("detail")
                    if isinstance(top_detail, list) and top_detail:
                        top_detail = str(top_detail[0])
                    flags_val = errors.get("flags")
                    if isinstance(flags_val, list) and flags_val:
                        flags_val = flags_val[0]
                    message = top_detail or message
                    flags = flags_val
                    status_code_resp = status.HTTP_403_FORBIDDEN
                except Exception:
                    pass

        payload = {"detail": message}
        if flags is not None:
            payload["flags"] = flags
        return Response(payload, status=status_code_resp)


class LogoutView(APIView):
    """
    JWT logout (industry standard): blacklist the *refresh token*.

    Requires `rest_framework_simplejwt.token_blacklist` installed + migrated.
    Client should delete access token locally regardless.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh)
            # Blacklist the refresh token (requires simplejwt blacklist app)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        return create_response(message="Successfully logged out.", status_code=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken(serializer.validated_data["refresh"])
        access_token = refresh.access_token
        return Response({"access": str(access_token)}, status=status.HTTP_200_OK)

