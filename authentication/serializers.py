from rest_framework import serializers
from .models import Users # OTP
from django.contrib.auth.hashers import make_password
from FAX_POD import utils


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'password',
            'status',
            'is_deleted',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        if Users.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError('A user with this email already exists.')

        password = validated_data.pop('password')
        user = Users(**validated_data)
        user.password = make_password(password)
        user.is_active = True
        user.save()

        return user

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.status = validated_data.get('status', instance.status)
        instance.is_deleted = validated_data.get('is_deleted', instance.is_deleted)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField()


# class RoleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Roles
#         fields = ['id', 'role_name']
