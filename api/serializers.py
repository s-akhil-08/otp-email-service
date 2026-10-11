from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
import random

from .models import User, TempUser, OTP

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'mobile', 'is_verified']


class SignupSerializer(serializers.ModelSerializer):
    confirmPassword = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = TempUser
        fields = ['email', 'name', 'mobile', 'password', 'confirmPassword']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data.get('password') != data.get('confirmPassword'):
            raise serializers.ValidationError({'confirmPassword': 'Passwords do not match.'})
        return data

    def to_internal_value(self, data):
        email = data.get('email')
        if email:
            email = email.lower()
            TempUser.objects.filter(email__iexact=email).delete()
            data = data.copy()
            data['email'] = email
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        return super().to_internal_value(data)

    def create(self, validated_data):
        validated_data.pop('confirmPassword', None)
        validated_data['email'] = validated_data['email'].lower()
        raw_password = validated_data['password']
        validated_data['password'] = make_password(raw_password)
        validated_data['raw_password'] = raw_password
        validated_data['otp'] = str(random.randint(100000, 999999))
        temp_user = TempUser.objects.create(**validated_data)
        return temp_user


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    type = serializers.ChoiceField(choices=['signup', 'forgot_password'], default='signup')
