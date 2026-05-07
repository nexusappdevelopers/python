import random

from rest_framework import serializers

from api.models import STATE_DELETED, STATE_INACTIVE
from api.models import DeviceDetails
from apps.models import User
from smtp.services import send_otp_email


class SignupSerializer(serializers.ModelSerializer):
    # Device details fields
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_name = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.IntegerField(required=False, default=1)  # Default to Android
    device_os = serializers.CharField(required=False, allow_blank=True)
    app_version = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "full_name",
            "contact_no",
            "otp",
            "created_at",
            "device_token",
            "device_name",
            "device_type",
            "device_os",
            "app_version",
        )
        extra_kwargs = {
            "password": {"write_only": True, "required": True},
            "email": {"required": True},
        }

    def create(self, validated_data):
        # Extract device details from validated_data
        device_token = validated_data.pop("device_token", None)
        device_name = validated_data.pop("device_name", "")
        device_type = validated_data.pop("device_type", 1)
        device_os = validated_data.pop("device_os", "")
        app_version = validated_data.pop("app_version", "")

        # Create user (inactive until OTP verified)
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            full_name=validated_data.get("full_name", ""),
            contact_no=validated_data.get("contact_no", ""),
            state_id=1,  # Inactive until OTP verified
            otp=self.generate_otp(),
        )

        user.is_verified = False
        user.save(update_fields=["is_verified"])

        # Store device details if device_token is provided
        if device_token:
            existing = (
                DeviceDetails.objects.filter(created_by_id=user.id).order_by("-updated_at").first()
            )
            if existing:
                existing.device_token = device_token
                existing.device_name = device_name
                existing.device_type = device_type
                existing.type_id = 1
                existing.device_os = device_os
                existing.app_version = app_version
                existing.access_token = ""
                existing.save()
            else:
                DeviceDetails.objects.create(
                    created_by_id=user.id,
                    device_token=device_token,
                    device_name=device_name,
                    device_type=device_type,
                    type_id=1,
                    device_os=device_os,
                    app_version=app_version,
                    access_token="",
                )

        # Send OTP email (best-effort)
        try:
            send_otp_email(user, user.otp)
        except Exception:
            pass

        return user

    def generate_otp(self):
        return random.randint(100000, 999999)

    def validate_contact_no(self, value):
        if value:
            cleaned = "".join(filter(str.isdigit, value))
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise serializers.ValidationError("Contact number must be between 10 and 15 digits.")
            return cleaned
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_name = serializers.CharField(required=False, allow_blank=True)
    device_os = serializers.CharField(required=False, allow_blank=True)
    app_version = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.IntegerField(required=False)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password") or ""

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        # Deleted account – treat as not registered
        if user.state_id == STATE_DELETED:
            raise serializers.ValidationError(
                {
                    "detail": "This account is not registered with us.",
                    "flags": {
                        "otp_verification_required": False,
                        "account_inactive_by_admin": False,
                        "deleted_account": True,
                    },
                }
            )

        # Unverified – ask to verify OTP
        if not user.is_verified:
            raise serializers.ValidationError(
                {
                    "detail": "Please verify OTP to activate your account.",
                    "flags": {
                        "otp_verification_required": True,
                        "account_inactive_by_admin": bool(getattr(user, "has_admin_updated", False)),
                        "deleted_account": False,
                    },
                }
            )

        # Inactive (admin-disabled vs needs OTP)
        if user.state_id == STATE_INACTIVE:
            admin_disabled = bool(getattr(user, "has_admin_updated", False))
            detail_msg = (
                "Your account has been disabled by admin."
                if admin_disabled
                else "Please verify OTP to activate your account."
            )
            raise serializers.ValidationError(
                {
                    "detail": detail_msg,
                    "flags": {
                        "otp_verification_required": not admin_disabled,
                        "account_inactive_by_admin": admin_disabled,
                        "deleted_account": False,
                    },
                }
            )

        # Verify password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        attrs["user"] = user
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

