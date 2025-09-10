from rest_framework import status
from rest_framework.response import Response
from FAX_POD import settings
from django.core.mail import send_mail
from authentication.models import EmailTemplate #OTP,
from django.template import Template, Context
from django.core.mail import EmailMultiAlternatives
import json
from Crypto.Cipher import AES
import base64
import json
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad
import hashlib
import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime
import requests
from io import BytesIO
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
import random
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile


def success_response(message, data=None, status_code=status.HTTP_200_OK, api_status_code=status.HTTP_200_OK):
    """
    A utility function to generate success API responses.

    Args:
    - message (str): A message to send with the response.
    - data (dict, optional): The data to include in the response. Defaults to None.
    - status_code (int, optional): The HTTP status code for the response. Defaults to HTTP_200_OK.

    Returns:
    - Response: A DRF Response object with the provided message, data, and status code.
    """
    response_data = {
        "message": message,
        "data": data if data else {},
        "status": status_code,
    }

    return Response(response_data, status=api_status_code, )


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST, api_status_code=status.HTTP_400_BAD_REQUEST):
    """
    A utility function to generate error API responses.

    Args:
    - message (str): A message to send with the response.
    - errors (dict, optional): The error details to include in the response. Defaults to None.
    - status_code (int, optional): The HTTP status code for the response. Defaults to HTTP_400_BAD_REQUEST.

    Returns:
    - Response: A DRF Response object with the provided message, error details, and status code.
    """
    response_data = {
        "message": message,
        "errors": errors if errors else {},
        "status": status_code,
    }

    return Response(response_data, status=api_status_code)
    
def send_mail_to_user(subject=None, message=None, recipient_list=None):
    send_mail(
                        subject=subject,
                        message= message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipient_list,
                    )
    
    
def get_email_html(template_name, context_data):
    try:
        template = EmailTemplate.objects.get(name=template_name)
        subject = Template(template.subject).render(Context(context_data))
        html_body = Template(template.html_body).render(Context(context_data))
        return subject, html_body
    except EmailTemplate.DoesNotExist as e:
        raise ValueError(f"Template '{template_name}' not found.") from e
    

def send_html_email(to_email, template_name, context_data):
    try:
        print(to_email,template_name,context_data)
        subject, html_body = get_email_html(template_name, context_data)
        email = EmailMultiAlternatives(
            subject=subject,
            body=html_body,  # Provide HTML content directly
            from_email='from@example.com',
            to=[to_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send()
    except ValueError as e:
        print(e)
        
def decrypt_data(encrypted_data):
    try:
        # Derive the AES-256 key using SHA256 from the same secret
        key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()

        cipher = AES.new(key, AES.MODE_ECB)
        decoded_encrypted = base64.b64decode(encrypted_data)
        decrypted_bytes = cipher.decrypt(decoded_encrypted)

        decrypted_text = unpad(decrypted_bytes, AES.block_size).decode("utf-8")
        return json.loads(decrypted_text)
    except Exception as e:
        print("❌ Decryption failed:", e)
        return None

def encrypt_data(data):
    try:
        # Convert dictionary or object to JSON string
        json_str = json.dumps(data)

        # Derive the AES-256 key using SHA256 from the SECRET_KEY
        key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()

        # Create AES cipher in ECB mode
        cipher = AES.new(key, AES.MODE_ECB)

        # Pad the plaintext to AES block size
        padded_data = pad(json_str.encode('utf-8'), AES.block_size)

        # Encrypt and encode in base64 for transport
        encrypted = cipher.encrypt(padded_data)
        encoded_encrypted = base64.b64encode(encrypted).decode('utf-8')

        return encoded_encrypted
    except Exception as e:
        print("❌ Encryption failed:", e)
        return None

def upload_pdf_to_azure(file_obj):
    """
    Uploads a file-like object to Azure Blob Storage and returns its public URL.
    Assumes the file_obj.name is already a unique and valid filename.
    """
    try:
        # Setup BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )

        container_name = settings.AZURE_STORAGE_CONTAINER_NAME

        # ✅ Use file_obj.name directly (already has unique name)
        filename = file_obj.name

        # Upload to blob
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
        blob_client.upload_blob(file_obj, overwrite=True)

        # Construct public URL (assuming container has "Blob" public access)
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{filename}"
        print("blob_url", blob_url)
        return blob_url

    except Exception as e:
        print("❌ Azure upload failed:", str(e))
        return None


def call_azure_openai(prompt):
    url = f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_KEY
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for medical document extraction."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2500
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        print("Azure OpenAI API error:", str(e))
        return None

def build_medical_prompt(extracted_text: str) -> str:
    return f"""
You are a highly intelligent medical document AI assistant.

Your job is to:
1. **Classify the type of fax** (choose one):
   - "CPAP Order"
   - "Chart Notes"
   - "Hospital Bed Request"
   - "Billing"
   - "Prescription"
   - "Referral"
   - "Lab Results"
   - "Other / Unknown"

2. **Extract all relevant structured data** from the fax text and populate the JSON below. Be very flexible in interpreting field labels, e.g.:
   - DOB = "Date of Birth", "Birthdate", "DOB",etc.
   - Sex = "Gender"
   - Doctor = "Physician", "Provider"
   - Phone = "Contact", "Tel", etc.
   - Address fields = "Ship To", "To Address", "Delivery", "Home", "Permanent", etc.
   - Diagnosis Codes = "Dx", "ICD-10"
   - Procedure Codes = "CPT", "HCPCS"
   - E-signature fields = "Signed by", "Dr. Signature", etc.

3. Populate the `fax_metadata.total_pages` field based on content hints (e.g., "Page 1 of 10").

4. If a field isn’t present, use empty string (`""`) or an empty list (`[]`), but always keep all keys.

**Instructions:**
- Output ONLY the JSON object—no markdown, no comments.
- Follow the format exactly.
- Make sure lists are properly formed.
- Prioritize clean and complete structured data extraction.

---

Output Format:

{{
  "ordered_service": {{
    "service_name": ""
  }},
  "type_of_fax": "<classified_type_here>",
  "demographics": {{
    "first_name": "", "last_name": "", "middle_name": "", "DOB": "",
    "gender": "", "ethnicity": "", "language": "", "height": "", "weight": ""
  }},
  "contact": {{
    "phone": "", "mobile": "", "emergency_contact": "", "emergency_contact_relationship": "",
    "email": "", "residential_address_line_1": "", "residential_address_line_2": "",
    "residential_address_city": "", "residential_address_state": "", "residential_address_zip_code": "",
    "residential_address_country": "", "residential_address_full_address": "",
    "delivery_address_line_1": "", "delivery_address_line_2": "", "delivery_address_city": "",
    "delivery_address_state": "", "delivery_address_zip_code": "", "delivery_address_country": "",
    "delivery_address_full_address": ""
  }},
  "insurance": {{
    "insurance_carrier": "", "insurance_id": "", "group_id": "", "coverage_start": "",
    "insurance_plan_name": "", "secondary_carrier": "", "secondary_insurance_id": "",
    "secondary_group_id": ""
  }},
  "clinical_details": {{
    "diagnosis_codes": "", "ordering_provider": "", "NPI": "", "provider_address": "", "facility": "",
    "procedure_codes": "", "ordering_provider_phone_number": "",
    "ordering_provider_fax": "", "referring_md": "", "e_signature": "", "e_signature_date": ""
  }},
  "medical_information_extracted": {{
    "vitals": ["<Always an array of strings like 'No alcohol use', 'Caffeine use: Yes'>"], "assessments": [], "medications": [],
    "medical_history": [], "presenting_symptoms": [], "social_history": []
  }},
  "procedure_codes": [
    {{
      "code": "", "quantity": "", "length_of_need": "",
      "product_name": "", "frequency": ""
    }}
  ],
  "e_signature": [
    {{
      "signature": "", "service_date": "", "signature_date": ""
    }}
  ],
  "clinical_details_expanded": {{
    "ordering_provider_first_name": "", "ordering_provider_last_name": "",
    "ordering_provider_name": "", "NPI": "", "provider_address_line_1": "",
    "provider_address_line_2": "", "provider_address_city": "", "provider_address_state": "",
    "provider_address_zip_code": "", "provider_address_country": "", "provider_address_full_address": "",
    "facility": "", "diagnosis_codes": "", "procedure_codes": "",
    "ordering_provider_phone_number": "", "ordering_provider_fax": "", "referring_md": ""
  }},
  "fax_metadata": {{
    "total_pages": ""
  }}
}}

---

Fax Text:
\"\"\"
{extracted_text}
\"\"\"

ONLY return the JSON.
"""

def is_scanned_pdf(file_bytes: bytes) -> bool:
    """
    Check if a PDF file is scanned (image-based) by testing if any text can be extracted.
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                return False  # Native text exists
        return True  # No text found on any page
    except Exception as e:
        print(f"⚠️ PDF scan detection failed: {e}")
        return True  # Default to scanned if anything fails

def extract_text_with_ocr(file_bytes: bytes) -> str:
    """
    Convert PDF pages to images and apply OCR using Tesseract.
    """
    try:
        images = convert_from_bytes(file_bytes)
        extracted_text = ""
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            extracted_text += f"\n--- Page {i + 1} ---\n{page_text}"
        return extracted_text.strip()
    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")
        return ""

def parse_date_safe(date_str):
    """
    Try parsing a date string in various common formats.
    Returns a string in 'YYYY-MM-DD' format or None if unparseable.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return None  # If all formats fail

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(email, otp, timeout=300):
    cache.set(f"otp_{email}", otp, timeout=timeout)

def get_stored_otp(email):
    return cache.get(f"otp_{email}")

def clear_stored_otp(email):
    cache.delete(f"otp_{email}")

""" Custom code user for fax pipeline """
def decode_base64_to_inmemory_file(filedata_base64, filename, mimetype):
    """Convert base64 string to InMemoryUploadedFile"""
    file_bytes = base64.b64decode(filedata_base64)
    file_stream = BytesIO(file_bytes)

    in_memory_file = InMemoryUploadedFile(
        file=file_stream,
        field_name="files",
        name=filename,
        content_type=mimetype,
        size=len(file_bytes),
        charset=None
    )
    print("in_memory_file",in_memory_file)
    return in_memory_file

def generate_unique_filename(filename):
    """Append timestamp to filename"""
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    print("unique",f"{name}_{timestamp}{ext}")
    return f"{name}_{timestamp}{ext}"

def upload_file_to_azure_blob(file):
    """Upload file to Azure Blob and return URL"""
    return upload_pdf_to_azure(file)