import os
import requests
from django.conf import settings
from datetime import datetime
from FAX_POD.utils import (
    upload_pdf_to_azure,
    is_scanned_pdf,
    extract_text_with_ocr,
    call_azure_openai,
    build_medical_prompt,
    parse_date_safe,
    error_response
)
from provider.models import DocumentHistory
import tempfile
import textract
import json
import re
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging
logger = logging.getLogger(__name__)

def is_valid_provider(provider):
    return all([
        provider.username,
        provider.company_number,
        provider.password
    ])

def get_faxage_credentials(provider):
    return {
        "username": provider.username,
        "company": provider.company_number,
        "password": provider.password,
    }

def list_faxes_from_faxage(provider):
    creds = get_faxage_credentials(provider)

    try:
        response = requests.post("https://api.faxage.com/httpsfax.php", data={
            **creds,
            "operation": "listfax",
            "faxbox": "in",
            # "unhandled": "1"
        })

        if response.status_code != 200:
            print(f"❌ listfax failed: {response.status_code} - {response.text[:200]}")
            return []

        return extract_fax_ids(response.text)

    except Exception as e:
        print(f"❌ Exception in list_faxes_from_faxage: {e}")
        return []

def extract_fax_ids(response_text):
    return [
        line.strip().split()[0]
        for line in response_text.strip().splitlines()
        if line.strip().split() and line.strip().split()[0].isdigit()
    ]

def download_fax_pdf(provider, fax_id):
    creds = get_faxage_credentials(provider)

    try:
        response = requests.post("https://api.faxage.com/httpsfax.php", data={
            **creds,
            "operation": "getfax",
            "faxid": fax_id,
            "informat": "pdf"
        })

        content_type = response.headers.get("Content-Type", "")
        if "pdf" in content_type or response.content.startswith(b"%PDF"):
            return response.content
        else:
            print(f"❌ Unexpected content type for fax {fax_id}: {content_type}")
            return None

    except Exception as e:
        print(f"❌ Error downloading fax {fax_id}: {e}")
        return None


# def fetch_faxes_from_faxage(provider):
#     logger.warning("🔍 Starting fax fetch for: %s", provider.username)

#     if not is_valid_provider(provider):
#         logger.warning("❌ Invalid provider credentials")
#         return []

#     fax_ids = list_faxes_from_faxage(provider)
#     if not fax_ids:
#         logger.warning("ℹ️ No new faxes.")
#         return []

#     first_fax_id = fax_ids[0]
#     file_bytes = download_fax_pdf(provider, first_fax_id)
#     if not file_bytes:
#         logger.warning("❌ Failed to download fax.")
#         return []

#     logger.warning(f"✅ Fax {first_fax_id} downloaded with size: {len(file_bytes)} bytes")

#     return []

def fetch_faxes_from_faxage(provider):
    logger.warning("🔍 Starting fax fetch for: %s", provider.username)

    if not is_valid_provider(provider):
        logger.warning("❌ Invalid provider credentials")
        return []

    fax_ids = list_faxes_from_faxage(provider)
    if not fax_ids:
        logger.warning("ℹ️ No new faxes.")
        return []

    first_fax_id = fax_ids[0]
    file_bytes = download_fax_pdf(provider, first_fax_id)
    if not file_bytes:
        logger.warning("❌ Failed to download fax.")
        return []

    logger.warning(f"✅ Fax {first_fax_id} downloaded with size: {len(file_bytes)} bytes")

    # === Step 1: Upload to Azure ===
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    filename = f"fax_{first_fax_id}_{timestamp}.pdf"
    file_stream = BytesIO(file_bytes)
    in_memory_file = InMemoryUploadedFile(
        file=file_stream,
        field_name="files",
        name=filename,
        content_type="application/pdf",
        size=len(file_bytes),
        charset=None
    )

    # file_url = upload_pdf_to_azure(in_memory_file, filename_prefix=filename)
    file_url = "https://stgaidrivendtanalysis.blob.core.windows.net/document-analysis-system/07fbc533-eac2-48d3-af14-dc9ddff09f23_20250710_134503953560.pdf20250710_134503954560_20250711_131029536795.pdf20250711_131029541448 (1)_20250715_084907370569.pdf20250715_084907372661.pdf"

    if not file_url:
        logger.warning("❌ Upload to Azure failed.")
        return []

    logger.warning(f"📤 Uploaded to Azure: {file_url}")

    # === Step 2: Download back the uploaded file
    blob_response = requests.get(file_url)
    if blob_response.status_code != 200:
        logger.warning(f"❌ Blob download failed: {blob_response.status_code}")
        return []

    file_bytes_for_check = blob_response.content

    # === Step 3: Extract Text
    try:
        if is_scanned_pdf(file_bytes_for_check):
            extracted_text = extract_text_with_ocr(file_bytes_for_check)
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
                temp_file.write(file_bytes_for_check)
                temp_file.flush()
                extracted_text = textract.process(temp_file.name).decode("utf-8")
    except Exception as e:
        logger.warning(f"❌ Text extraction failed: {e}")
        return []

    logger.warning(f"🧠 Text extracted (length={len(extracted_text)})")

    # === Step 4: Azure OpenAI LLM
    prompt = build_medical_prompt(extracted_text)
    response_text = call_azure_openai(prompt)
    cleaned_output = re.sub(r"^```(?:json)?|```$", "", response_text.strip()).strip()

    try:
        structured_data = json.loads(cleaned_output)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned_output, re.DOTALL)
        structured_data = json.loads(match.group()) if match else {
            "error": "Invalid JSON",
            "raw_text": cleaned_output[:1000]
        }

    # === Step 5: Save to DB
    try:
        ordered_service = structured_data.get("ordered_service", {})
        demographics = structured_data.get("demographics", {})
        contact = structured_data.get("contact", {})
        insurance = structured_data.get("insurance", {})
        clinical_details = structured_data.get("clinical_details", {})
        medical_info = structured_data.get("medical_information_extracted", {})
        procedure_codes = structured_data.get("procedure_codes", [])
        e_signatures = structured_data.get("e_signature", [])
        clinical_expanded = structured_data.get("clinical_details_expanded", {})
        fax_metadata = structured_data.get("fax_metadata", {})
        fax_type = structured_data.get("type_of_fax", "")

        doc = DocumentHistory.objects.create(
            userId=provider.id,
            file_name=filename,
            file_path=file_url,
            service_name=ordered_service.get("service_name", ""),
            first_name=demographics.get("first_name"),
            last_name=demographics.get("last_name"),
            middle_name=demographics.get("middle_name"),
            DOB=parse_date_safe(demographics.get("DOB")),
            gender=demographics.get("gender"),
            ethnicity=demographics.get("ethnicity"),
            language=demographics.get("language"),
            height=demographics.get("height"),
            weight=demographics.get("weight"),
            phone=contact.get("phone"),
            mobile=contact.get("mobile"),
            emergency_contact=contact.get("emergency_contact"),
            emergency_contact_relationship=contact.get("emergency_contact_relationship"),
            email=contact.get("email"),
            residential_address_line_1=contact.get("residential_address_line_1"),
            residential_address_line_2=contact.get("residential_address_line_2"),
            residential_address_city=contact.get("residential_address_city"),
            residential_address_state=contact.get("residential_address_state"),
            residential_address_zip_code=contact.get("residential_address_zip_code"),
            residential_address_country=contact.get("residential_address_country"),
            residential_address_full_address=contact.get("residential_address_full_address"),
            delivery_address_line_1=contact.get("delivery_address_line_1"),
            delivery_address_line_2=contact.get("delivery_address_line_2"),
            delivery_address_city=contact.get("delivery_address_city"),
            delivery_address_state=contact.get("delivery_address_state"),
            delivery_address_zip_code=contact.get("delivery_address_zip_code"),
            delivery_address_country=contact.get("delivery_address_country"),
            delivery_address_full_address=contact.get("delivery_address_full_address"),
            insurance_carrier=insurance.get("insurance_carrier"),
            insurance_id=insurance.get("insurance_id"),
            group_id=insurance.get("group_id"),
            coverage_start=parse_date_safe(insurance.get("coverage_start")),
            insurance_plan_name=insurance.get("insurance_plan_name"),
            secondary_carrier=insurance.get("secondary_carrier"),
            secondary_insurance_id=insurance.get("secondary_insurance_id"),
            secondary_group_id=insurance.get("secondary_group_id"),
            ordering_provider=clinical_details.get("ordering_provider"),
            NPI=clinical_details.get("NPI"),
            provider_address=clinical_details.get("provider_address"),
            facility=clinical_details.get("facility"),
            diagnosis_codes=clinical_details.get("diagnosis_codes"),
            procedure_codes=clinical_details.get("procedure_codes"),
            ordering_provider_phone_number=clinical_details.get("ordering_provider_phone_number"),
            ordering_provider_fax=clinical_details.get("ordering_provider_fax"),
            referring_md=clinical_details.get("referring_md"),
            e_signature=clinical_details.get("e_signature"),
            e_signature_date=parse_date_safe(clinical_details.get("e_signature_date")),
            vitals=medical_info.get("vitals"),
            assessments=medical_info.get("assessments"),
            medications=medical_info.get("medications"),
            medical_history=medical_info.get("medical_history"),
            presenting_symptoms=medical_info.get("presenting_symptoms"),
            social_history=medical_info.get("social_history"),
            procedure_codes_list=procedure_codes,
            e_signature_list=e_signatures,
            ordering_provider_first_name=clinical_expanded.get("ordering_provider_first_name"),
            ordering_provider_last_name=clinical_expanded.get("ordering_provider_last_name"),
            ordering_provider_name=clinical_expanded.get("ordering_provider_name"),
            provider_address_line_1=clinical_expanded.get("provider_address_line_1"),
            provider_address_line_2=clinical_expanded.get("provider_address_line_2"),
            provider_address_city=clinical_expanded.get("provider_address_city"),
            provider_address_state=clinical_expanded.get("provider_address_state"),
            provider_address_zip_code=clinical_expanded.get("provider_address_zip_code"),
            provider_address_country=clinical_expanded.get("provider_address_country"),
            provider_address_full_address=clinical_expanded.get("provider_address_full_address"),
            facility_expanded=clinical_expanded.get("facility"),
            diagnosis_codes_expanded=clinical_expanded.get("diagnosis_codes"),
            procedure_codes_expanded=clinical_expanded.get("procedure_codes"),
            ordering_provider_phone_number_expanded=clinical_expanded.get("ordering_provider_phone_number"),
            ordering_provider_fax_expanded=clinical_expanded.get("ordering_provider_fax"),
            referring_md_expanded=clinical_expanded.get("referring_md"),
            type_of_fax=fax_type,
            total_pages=fax_metadata.get("total_pages"),
            document_type="fax",
            uploaded=False
        )

        logger.warning(f"✅ Document saved to DB: ID={doc.id}, FaxID={first_fax_id}")
        return [file_url]

    except Exception as e:
        logger.warning(f"❌ Error saving document to DB: {e}")
        return []


# def fetch_faxes_from_faxage(provider):
#     logger.warning("🔍 Starting fax fetch for: %s", provider.username)

#     if not is_valid_provider(provider):
#         logger.warning("❌ Invalid provider credentials")
#         return []

#     fax_ids = list_faxes_from_faxage(provider)
#     if not fax_ids:
#         logger.warning("ℹ️ No new faxes.")
#         return []

#     first_fax_id = fax_ids[0]
#     file_bytes = download_fax_pdf(provider, first_fax_id)
#     if not file_bytes:
#         logger.warning("❌ Failed to download fax.")
#         return []

#     logger.warning(f"✅ Fax {first_fax_id} downloaded with size: {len(file_bytes)} bytes")

#     # === Step: Upload to Azure ===
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"fax_{first_fax_id}_{timestamp}.pdf"

#     # 2. Wrap bytes in InMemoryUploadedFile
#     file_stream = BytesIO(file_bytes)
#     in_memory_file = InMemoryUploadedFile(
#         file=file_stream,
#         field_name="files",
#         name=filename,  # 👈 this sets the actual file name
#         content_type="application/pdf",
#         size=len(file_bytes),
#         charset=None
#     )

#     # 3. Upload (this will now use your filename)
#     file_url = upload_pdf_to_azure(in_memory_file)



#     if file_url:
#         logger.warning(f"📤 Uploaded to Azure: {file_url}")
#         return [file_url]
#     else:
#         logger.warning("❌ Upload to Azure failed.")
#         return []



















































# second

# def fetch_faxes_from_faxage(provider):
#     credentials = {
#         "username": provider.username,
#         "company": provider.company_number,
#         "password": provider.password,
#     }
#     print("credentials:",credentials)

#     try:
#         # ✅ Fetch only unread faxes
#         list_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "listfax",
#             "faxbox": "in",
#             # "unhandled": "1"  # Only fetch unread faxes
#         })
#         if list_response.status_code != 200:
#             print(f"❌ Failed to list faxes: {list_response.text}")
#             return []

#         fax_ids = extract_fax_ids(list_response.text)
#         if not fax_ids:
#             print("ℹ️ No unread faxes found.")
#             return []

#         print(f"📥 Found {len(fax_ids)} unread faxes.")
#     except Exception as e:
#         print(f"❌ Error during listfax request: {e}")
#         return []

#     saved_paths = []

#     # ✅ Only process the first unread fax
#     first_fax_id = fax_ids[0]
#     try:
#         # Download the fax
#         response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "getfax",
#             "faxid": first_fax_id,
#             "informat": "pdf"
#         })

#         if "pdf" in response.headers.get("Content-Type", "") or response.content.startswith(b"%PDF"):
#             folder = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
#             os.makedirs(folder, exist_ok=True)

#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             filename = f"fax_{first_fax_id}_{timestamp}.pdf"
#             filepath = os.path.join(folder, filename)

#             with open(filepath, "wb") as f:
#                 f.write(response.content)

#             saved_paths.append(filepath)
#             print(f"✅ Saved fax {first_fax_id} at {filepath}")

#             # ✅ Mark as read
#             handled_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#                 **credentials,
#                 "operation": "handled",
#                 "recvid": first_fax_id,
#                 "handled": "1"
#             })

#             if handled_response.status_code == 200 and "marked handled" in handled_response.text.lower():
#                 print(f"📬 Marked fax {first_fax_id} as READ")
#             else:
#                 print(f"⚠️ Failed to mark fax {first_fax_id} as read: {handled_response.text[:100]}")

#         else:
#             print(f"❌ Unexpected content for fax {first_fax_id}: {response.text[:100]}")

#     except Exception as e:
#         print(f"❌ Error fetching fax {first_fax_id}: {e}")

#     return saved_paths

# def extract_fax_ids(response_text):
#     fax_ids = []
#     for line in response_text.strip().splitlines():
#         parts = line.strip().split()
#         if parts and parts[0].isdigit():
#             fax_ids.append(parts[0])
#     return fax_ids



# def fetch_faxes_from_faxage(provider):
#     credentials = {
#         "username": provider.username,
#         "company": provider.company_number,
#         "password": provider.password,
#     }

#     try:
#         list_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "listfax",
#             "faxbox": "in"
#         })

#         if list_response.status_code != 200:
#             print(f"❌ Failed to list faxes: {list_response.text}")
#             return []

#         fax_ids = extract_fax_ids(list_response.text)
#         if not fax_ids:
#             print("ℹ️ No faxes found.")
#             return []

#         print(f"📥 Found {len(fax_ids)} faxes.")
#     except Exception as e:
#         print(f"❌ Error during listfax request: {e}")
#         return []

#     saved_paths = []

#     for fax_id in fax_ids:
#         # 🚧 TODO: Add DB-level check here to avoid duplicates
#         # Example (commented):
#         # if FaxHistory.objects.filter(fax_id=fax_id, provider=provider).exists():
#         #     print(f"⏭️ Fax {fax_id} already exists — skipping")
#         #     continue

#         try:
#             response = requests.post("https://api.faxage.com/httpsfax.php", data={
#                 **credentials,
#                 "operation": "getfax",
#                 "faxid": fax_id,
#                 "informat": "pdf"
#             })

#             if "pdf" in response.headers.get("Content-Type", "") or response.content.startswith(b"%PDF"):
#                 folder = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
#                 os.makedirs(folder, exist_ok=True)

#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = f"fax_{fax_id}_{timestamp}.pdf"
#                 filepath = os.path.join(folder, filename)

#                 with open(filepath, "wb") as f:
#                     f.write(response.content)

#                 saved_paths.append(filepath)
#                 print(f"✅ Saved fax {fax_id} at {filepath}")
#             else:
#                 print(f"❌ Unexpected content for fax {fax_id}: {response.text[:100]}")

#         except Exception as e:
#             print(f"❌ Error fetching fax {fax_id}: {e}")

#     return saved_paths

# def extract_fax_ids(response_text):
#     """
#     Extracts fax IDs from listfax plain text response.
#     Format:
#     575497833 2022-09-02 06:06:30 (415)800-6052 (727)655-9881
#     """
#     fax_ids = []
#     for line in response_text.strip().splitlines():
#         parts = line.strip().split()
#         if parts and parts[0].isdigit():
#             fax_ids.append(parts[0])
#     return fax_ids



# def fetch_faxes_from_faxage(provider):
#     credentials = {
#         "username": provider.username,
#         "company": provider.company_number,
#         "password": provider.password,
#     }

#     try:
#         list_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "listfax",
#             "faxbox": "in"
#         })

#         if list_response.status_code != 200:
#             print(f"❌ Failed to list faxes: {list_response.text}")
#             return []

#         fax_ids = extract_fax_ids(list_response.text)
#         if not fax_ids:
#             print("ℹ️ No faxes found.")
#             return []

#         print(f"📥 Found {len(fax_ids)} faxes.")
#     except Exception as e:
#         print(f"❌ Error during listfax request: {e}")
#         return []

#     saved_paths = []

#     for fax_id in fax_ids:
#         # 🚧 TODO: Add DB-level check here to avoid duplicates
#         # Example (commented):
#         # if FaxHistory.objects.filter(fax_id=fax_id, provider=provider).exists():
#         #     print(f"⏭️ Fax {fax_id} already exists — skipping")
#         #     continue

#         try:
#             response = requests.post("https://api.faxage.com/httpsfax.php", data={
#                 **credentials,
#                 "operation": "getfax",
#                 "faxid": fax_id,
#                 "informat": "pdf"
#             })

#             if "pdf" in response.headers.get("Content-Type", "") or response.content.startswith(b"%PDF"):
#                 folder = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
#                 os.makedirs(folder, exist_ok=True)

#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = f"fax_{fax_id}_{timestamp}.pdf"
#                 filepath = os.path.join(folder, filename)

#                 with open(filepath, "wb") as f:
#                     f.write(response.content)

#                 saved_paths.append(filepath)
#                 print(f"✅ Saved fax {fax_id} at {filepath}")
#             else:
#                 print(f"❌ Unexpected content for fax {fax_id}: {response.text[:100]}")

#         except Exception as e:
#             print(f"❌ Error fetching fax {fax_id}: {e}")

#     return saved_paths

# def extract_fax_ids(response_text):
#     """
#     Extracts fax IDs from listfax plain text response.
#     Format:
#     575497833 2022-09-02 06:06:30 (415)800-6052 (727)655-9881
#     """
#     fax_ids = []
#     for line in response_text.strip().splitlines():
#         parts = line.strip().split()
#         if parts and parts[0].isdigit():
#             fax_ids.append(parts[0])
#     return fax_ids

""" Last working for single file """
# def fetch_faxes_from_faxage(provider):
#     credentials = {
#         "username": provider.username,
#         "company": provider.company_number,
#         "password": provider.password,
#     }
#     print("credentials:",credentials)

#     try:
#         # ✅ Fetch only unread faxes
#         list_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "listfax",
#             "faxbox": "in",
#             # "unhandled": "1"  # Only fetch unread faxes
#         })
#         if list_response.status_code != 200:
#             print(f"❌ Failed to list faxes: {list_response.text}")
#             return []

#         fax_ids = extract_fax_ids(list_response.text)
#         if not fax_ids:
#             print("ℹ️ No unread faxes found.")
#             return []

#         print(f"📥 Found {len(fax_ids)} unread faxes.")
#     except Exception as e:
#         print(f"❌ Error during listfax request: {e}")
#         return []

#     saved_paths = []

#     # ✅ Only process the first unread fax
#     first_fax_id = fax_ids[0]
#     try:
#         # Download the fax
#         response = requests.post("https://api.faxage.com/httpsfax.php", data={
#             **credentials,
#             "operation": "getfax",
#             "faxid": first_fax_id,
#             "informat": "pdf"
#         })

#         if "pdf" in response.headers.get("Content-Type", "") or response.content.startswith(b"%PDF"):
#             folder = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
#             os.makedirs(folder, exist_ok=True)

#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             filename = f"fax_{first_fax_id}_{timestamp}.pdf"
#             filepath = os.path.join(folder, filename)

#             with open(filepath, "wb") as f:
#                 f.write(response.content)

#             saved_paths.append(filepath)
#             print(f"✅ Saved fax {first_fax_id} at {filepath}")

#             # ✅ Mark as read
#             handled_response = requests.post("https://api.faxage.com/httpsfax.php", data={
#                 **credentials,
#                 "operation": "handled",
#                 "recvid": first_fax_id,
#                 "handled": "1"
#             })

#             if handled_response.status_code == 200 and "marked handled" in handled_response.text.lower():
#                 print(f"📬 Marked fax {first_fax_id} as READ")
#             else:
#                 print(f"⚠️ Failed to mark fax {first_fax_id} as read: {handled_response.text[:100]}")

#         else:
#             print(f"❌ Unexpected content for fax {first_fax_id}: {response.text[:100]}")

#     except Exception as e:
#         print(f"❌ Error fetching fax {first_fax_id}: {e}")

#     return saved_paths


# def extract_fax_ids(response_text):
#     fax_ids = []
#     for line in response_text.strip().splitlines():
#         parts = line.strip().split()
#         if parts and parts[0].isdigit():
#             fax_ids.append(parts[0])
#     return fax_ids

