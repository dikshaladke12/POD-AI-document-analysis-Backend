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

# class FaxProviderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FaxProvider
#         fields = [
#             'id', 'provider_name', 'authentication_type', 'authentication_value',
#             'fetch_api_url', 'fetch_method', 'fetch_headers', 'fetch_params',
#             'fax_numbers', 'status', 'is_valid', 'is_deleted', 'last_validated_at',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['created_at', 'updated_at', 'is_valid', 'last_validated_at']

#     def validate(self, data):
#         user = self.context['request'].user
#         provider_name = data.get('provider_name')

#         if self.instance is None:
#             if FaxProvider.objects.filter(user=user, provider_name__iexact=provider_name).exists():
#                 raise serializers.ValidationError({
#                     "provider_name": f"Provider '{provider_name}' already exists for this user."
#                 })
#         return data

#     def create(self, validated_data):
#         # Normalize inputs
#         validated_data['provider_name'] = validated_data['provider_name'].lower()
#         validated_data['authentication_type'] = validated_data['authentication_type'].lower()
#         validated_data['fetch_api_url'] = validated_data['fetch_api_url'].lower()

#         # Add static default values for fields not passed by frontend
#         validated_data['fetch_method'] = "GET"
#         validated_data['fetch_headers'] = {"accessToken": ""}
#         validated_data['fetch_params'] = {"status": "received"}
#         validated_data['status'] = "active"

#         return super().create(validated_data)
