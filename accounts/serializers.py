from rest_framework import serializers
from .utils import to_e164

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150)
    phone = serializers.CharField(min_length=3, max_length=25)
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    lang = serializers.ChoiceField(choices=["ar", "fr"], default="ar", required=False)

    # ✅ جديد: الدور
    role = serializers.ChoiceField(choices=["client", "worker"], default="client", required=False)

    def validate_phone(self, value):
        try:
            return to_e164(value)
        except Exception:
            raise serializers.ValidationError("invalid_phone_format")

class VerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()

    def validate_phone(self, value):
        try:
            return to_e164(value)
        except Exception:
            raise serializers.ValidationError("invalid_phone_format")

class LoginSerializer(serializers.Serializer):
    phone_or_username = serializers.CharField()
    password = serializers.CharField(write_only=True)

from rest_framework import serializers
from .utils import to_e164

# موجود لديك مسبقًا: RegisterSerializer, VerifySerializer, LoginSerializer ...

class ResendSerializer(serializers.Serializer):
    phone = serializers.CharField()
    lang = serializers.ChoiceField(choices=["ar", "fr"], default="ar", required=False)

    def validate_phone(self, value):
        try:
            return to_e164(value)
        except Exception:
            raise serializers.ValidationError("invalid_phone_format")

class PasswordResetStartSerializer(serializers.Serializer):
    phone = serializers.CharField()
    lang = serializers.ChoiceField(choices=["ar", "fr"], default="ar", required=False)

    def validate_phone(self, value):
        try:
            return to_e164(value)
        except Exception:
            raise serializers.ValidationError("invalid_phone_format")

class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    new_password_confirm = serializers.CharField(min_length=6, max_length=128, write_only=True)

    def validate_phone(self, value):
        try:
            return to_e164(value)
        except Exception:
            raise serializers.ValidationError("invalid_phone_format")

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "passwords_do_not_match"})
        return attrs
