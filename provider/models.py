from django.db import models
from django.contrib.auth import get_user_model
from FAX_POD.middleware.encryption_fields import EncryptedTextField, EncryptedCharField, EncryptedJSONField, EncryptedDateField

User = get_user_model()
class DocumentHistory(models.Model):
    userId = models.IntegerField()
    file_name = models.CharField(max_length=500)
    file_path = models.TextField()
    is_deleted = models.BooleanField(default=False)

    # Ordered Service
    service_name = EncryptedCharField(max_length=500, blank=True, null=True)

    # Demographics
    first_name = EncryptedCharField(max_length=500, blank=True, null=True)
    last_name = EncryptedCharField(max_length=500, blank=True, null=True)
    middle_name = EncryptedCharField(max_length=500, blank=True, null=True)
    DOB = EncryptedCharField(blank=True, null=True)
    gender = EncryptedCharField(max_length=500, blank=True, null=True)
    ethnicity = EncryptedCharField(max_length=500, blank=True, null=True)
    language = EncryptedCharField(max_length=500, blank=True, null=True)
    height = EncryptedCharField(max_length=500, blank=True, null=True)
    weight = EncryptedCharField(max_length=500, blank=True, null=True)

    # Contact
    phone = EncryptedCharField(max_length=500, blank=True, null=True)
    mobile = EncryptedCharField(max_length=500, blank=True, null=True)
    emergency_contact = EncryptedCharField(max_length=500, blank=True, null=True)
    emergency_contact_relationship = EncryptedCharField(max_length=500, blank=True, null=True)
    email = EncryptedTextField(blank=True, null=True)
    residential_address_line_1 = EncryptedTextField(blank=True, null=True)
    residential_address_line_2 = EncryptedTextField(blank=True, null=True)
    residential_address_city = EncryptedCharField(max_length=500, blank=True, null=True)
    residential_address_state = EncryptedTextField(max_length=500, blank=True, null=True)
    residential_address_zip_code = EncryptedCharField(max_length=500, blank=True, null=True)
    residential_address_country = EncryptedCharField(max_length=500, blank=True, null=True)
    residential_address_full_address = EncryptedTextField(blank=True, null=True)
    delivery_address_line_1 = EncryptedTextField(blank=True, null=True)
    delivery_address_line_2 = EncryptedTextField(blank=True, null=True)
    delivery_address_city = EncryptedCharField(max_length=500, blank=True, null=True)
    delivery_address_state = EncryptedCharField(max_length=500, blank=True, null=True)
    delivery_address_zip_code = EncryptedCharField(max_length=500, blank=True, null=True)
    delivery_address_country = EncryptedTextField(max_length=500, blank=True, null=True)
    delivery_address_full_address = EncryptedTextField(blank=True, null=True)

    # Insurance
    insurance_carrier = EncryptedCharField(max_length=500, blank=True, null=True)
    insurance_id = EncryptedTextField(max_length=500, blank=True, null=True)
    group_id = EncryptedCharField(max_length=500, blank=True, null=True)
    coverage_start = models.DateField(blank=True, null=True)
    insurance_plan_name = EncryptedCharField(max_length=500, blank=True, null=True)
    secondary_carrier = EncryptedCharField(max_length=500, blank=True, null=True)
    secondary_insurance_id = EncryptedCharField(max_length=500, blank=True, null=True)
    secondary_group_id = EncryptedCharField(max_length=500, blank=True, null=True)

    # Clinical Details
    ordering_provider = EncryptedCharField(max_length=500, blank=True, null=True)
    NPI = EncryptedCharField(max_length=500, blank=True, null=True)
    provider_address = EncryptedTextField(blank=True, null=True)
    facility = EncryptedCharField(max_length=500, blank=True, null=True)
    diagnosis_codes = EncryptedCharField(max_length=500, blank=True, null=True)
    procedure_codes = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_phone_number = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_fax = EncryptedCharField(max_length=500, blank=True, null=True)
    referring_md = EncryptedCharField(max_length=500, blank=True, null=True)
    e_signature = EncryptedCharField(max_length=500, blank=True, null=True)
    e_signature_date = models.DateField(blank=True, null=True)

    # Lists (stored as JSON strings)
    vitals = EncryptedCharField(blank=True, null=True)
    assessments = EncryptedCharField(blank=True, null=True)
    medications = EncryptedCharField(blank=True, null=True)
    medical_history = EncryptedCharField(blank=True, null=True)
    presenting_symptoms = EncryptedCharField(blank=True, null=True)
    social_history = EncryptedCharField(blank=True, null=True)

    # Procedure Codes (multiple)
    procedure_codes_list = EncryptedCharField(blank=True, null=True)

    # E-signature block (multiple)
    e_signature_list = EncryptedCharField(blank=True, null=True)

    # Clinical Expanded
    ordering_provider_first_name = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_last_name = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_name = EncryptedCharField(max_length=500, blank=True, null=True)
    provider_address_line_1 = EncryptedTextField(blank=True, null=True)
    provider_address_line_2 = EncryptedTextField(blank=True, null=True)
    provider_address_city = EncryptedTextField(max_length=500, blank=True, null=True)
    provider_address_state = EncryptedCharField(max_length=500, blank=True, null=True)
    provider_address_zip_code = EncryptedCharField(max_length=500, blank=True, null=True)
    provider_address_country = EncryptedCharField(max_length=500, blank=True, null=True)
    provider_address_full_address = EncryptedTextField(blank=True, null=True)
    facility_expanded = EncryptedCharField(max_length=500, blank=True, null=True)
    diagnosis_codes_expanded = EncryptedTextField(max_length=500, blank=True, null=True)
    procedure_codes_expanded = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_phone_number_expanded = EncryptedCharField(max_length=500, blank=True, null=True)
    ordering_provider_fax_expanded = EncryptedCharField(max_length=500, blank=True, null=True)
    referring_md_expanded = EncryptedCharField(max_length=500, blank=True, null=True)
    type_of_fax = EncryptedCharField(max_length=500, blank=True, null=True)
    fax_category = EncryptedCharField(max_length=500, blank=True, null=True)
    total_pages = EncryptedCharField(max_length=500, blank=True, null=True)
    uploaded = models.BooleanField(default=False)
    compliance_report = EncryptedTextField(blank=True, null=True)

    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    document_type = EncryptedCharField(max_length=500, default="fax")  # e.g. fax, upload

    def __str__(self):
        return f"{self.file_name} by User {self.userId}"


""" Table used for storing user faxes details that user wants to fetch faxes with its method and type """
class FaxProvider(models.Model):
    PROVIDER_CHOICES = (
        ('faxage', 'Faxage'),
        # Add more providers here later
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fax_providers')

    username = EncryptedCharField(max_length=255)
    password = EncryptedTextField()  # 🔐 Encrypted for security
    company_number = EncryptedCharField(max_length=255)

    provider = EncryptedCharField(max_length=100, choices=PROVIDER_CHOICES, default='faxage')

    status = models.CharField(max_length=10, choices=(('active', 'Active'), ('inactive', 'Inactive')), default='active')
    is_valid = models.BooleanField(default=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)  # ✅ Soft delete

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     unique_together = ('user', 'username')

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.username} ({self.provider})"

