from rest_framework import serializers
from provider.models import DocumentHistory, FaxProvider

class DocumentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentHistory
        exclude = ['is_deleted']

class FaxProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaxProvider
        fields = [
            'id', 'username', 'password', 'company_number', 'provider',
            'status', 'is_valid', 'is_deleted', 'last_validated_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_valid', 'last_validated_at']

    def validate(self, data):
        user = self.context['request'].user
        username = data.get('username')

        if self.instance is None:
            if FaxProvider.objects.filter(user=user, username__iexact=username).exists():
                raise serializers.ValidationError({
                    "username": f"Username '{username}' already exists for this user."
                })

        password = data.get('password', '')
        if password and len(password) < 8:
            raise serializers.ValidationError({
                "password": "Password must be at least 8 characters long."
            })

        return data

    def create(self, validated_data):
        validated_data['username'] = validated_data['username'].lower()
        validated_data['company_number'] = validated_data['company_number'].lower()

        # Optionally normalize provider to lowercase
        validated_data['provider'] = validated_data.get('provider', 'faxage').lower()

        validated_data['status'] = "active"
        return super().create(validated_data)