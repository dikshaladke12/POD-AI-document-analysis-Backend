import fitz  # PyMuPDF
import base64
import json
import io
import pytesseract
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from FAX_POD import settings
import requests
from PIL import Image
import os

def free_ocr(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (if text-based) or Tesseract (if scanned)."""
    try:
        doc = fitz.open(file_path)
        text_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Try extracting text directly
            text = page.get_text().strip()
            if text:
                text_content.append(text)
            else:
                # If no text, fall back to OCR on page image
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                text_content.append(ocr_text.strip())

        return "\n".join([t for t in text_content if t]).strip()

    except Exception as e:
        return f"❌ Free OCR failed: {str(e)}"

def paid_ocr(filedata_b64: str, azure_key: str, azure_endpoint: str) -> str:
    """Extract text using Azure Document Intelligence OCR (paid)."""
    try:
        document_client = DocumentAnalysisClient(
            endpoint=azure_endpoint,
            credential=AzureKeyCredential(azure_key)
        )

        file_bytes = base64.b64decode(filedata_b64)

        poller = document_client.begin_analyze_document(
            "prebuilt-read",
            document=file_bytes
        )
        result = poller.result()

        text_content = []
        for page in result.pages:
            for line in page.lines:
                text_content.append(line.content)

        return "\n".join(text_content).strip()
    except Exception as e:
        return f"❌ Azure OCR failed: {str(e)}"


def call_azure_openai(prompt: str) -> str:
    """Call Azure OpenAI for structured JSON output."""
    url = f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_KEY
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for medical document extraction. Return only valid JSON."},
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
        return f"❌ Azure OpenAI API error: {str(e)}"


def process_document_from_blob(file_path, filename, filedata, ocr_type="free",
                               azure_key=None, azure_endpoint=None,
                               user_id=None, json_input=None):
    """
    Process document with free/paid OCR + Azure OpenAI for structured output.
    """

    raw_text = ""

    if ocr_type == "free":
        raw_text = free_ocr(file_path)

    elif ocr_type == "paid":
        raw_text = paid_ocr(filedata, azure_key, azure_endpoint)

    else:
        raw_text = "❌ Invalid OCR type provided."

    structured_output = None
    if raw_text and json_input:
        prompt = f"""
        You are a medical document extraction assistant.
        Extract information from the following text according to this JSON schema:

        Schema:
        {json_input}

        Document Text:
        {raw_text}
        """
        structured_output = call_azure_openai(prompt)

    return {
        "filename": filename,
        "ocr_type": ocr_type,
        "raw_text": raw_text,
        "structured_output": structured_output
    }

# import os
# import base64
# import fitz  # PyMuPDF
# import requests
# from azure.ai.formrecognizer import DocumentAnalysisClient
# from azure.core.credentials import AzureKeyCredential
# from FAX_POD import settings
# import json


# # ----------------------------
# # FREE OCR (PyMuPDF)
# # ----------------------------
# def extract_text_free(file_path: str) -> str:
#     try:
#         doc = fitz.open(file_path)
#         text_content = []
#         for page_num in range(len(doc)):
#             page = doc[page_num]
#             text_content.append(page.get_text())
#         return "\n".join(text_content)
#     except Exception as e:
#         return f"❌ Free OCR failed: {str(e)}"


# # ----------------------------
# # PAID OCR (Azure Document Intelligence)
# # ----------------------------
# def extract_text_paid(filedata: str, azure_key: str, azure_endpoint: str) -> str:
#     try:
#         if not azure_key or not azure_endpoint:
#             return "❌ Azure OCR requires azureKey and azureEndpoint"

#         document_client = DocumentAnalysisClient(
#             endpoint=azure_endpoint,
#             credential=AzureKeyCredential(azure_key)
#         )

#         file_bytes = base64.b64decode(filedata)

#         poller = document_client.begin_analyze_document(
#             "prebuilt-read",  # OCR model
#             document=file_bytes
#         )
#         result = poller.result()

#         text_content = []
#         for page in result.pages:
#             for line in page.lines:
#                 text_content.append(line.content)

#         return "\n".join(text_content)

#     except Exception as e:
#         return f"❌ Azure OCR failed: {str(e)}"


# # ----------------------------
# # CALL AZURE OPENAI
# # ----------------------------
# def call_azure_openai(prompt: str):
#     url = f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"

#     headers = {
#         "Content-Type": "application/json",
#         "api-key": settings.AZURE_OPENAI_KEY
#     }

#     payload = {
#         "messages": [
#             {"role": "system", "content": "You are a helpful assistant for medical document extraction."},
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0.2,
#         "max_tokens": 2500
#     }

#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         response.raise_for_status()
#         return response.json()['choices'][0]['message']['content']
#     except requests.RequestException as e:
#         return f"❌ Azure OpenAI API error: {str(e)}"
#     except Exception as e:
#         return f"❌ Unexpected LLM error: {str(e)}"


# # ----------------------------
# # MAIN FUNCTION
# # ----------------------------
# def process_document_from_blob(file_path, filename, filedata,
#                                ocr_type="free",
#                                azure_key=None, azure_endpoint=None,
#                                schema: dict = None, user_id=None):
#     """
#     Runs OCR (free/paid), then optionally uses Azure OpenAI to structure data.
#     """
#     # Step 1: OCR
#     if ocr_type == "free":
#         extracted_text = extract_text_free(file_path)
#     elif ocr_type == "paid":
#         extracted_text = extract_text_paid(filedata, azure_key, azure_endpoint)
#     else:
#         extracted_text = "❌ Invalid OCR type provided."

#     # Step 2: Ask LLM for structured JSON (if schema provided)
#     structured_data = {}
#     if schema:
#         prompt = f"""
#         You are an information extractor.
#         Extract the following fields from the OCR text into JSON format.

#         Schema:
#         {json.dumps(schema, indent=2)}

#         OCR Text:
#         {extracted_text}

#         Return ONLY valid JSON.
#         """
#         structured_output = call_azure_openai(prompt)

#         # Try parsing JSON
#         try:
#             structured_data = json.loads(structured_output)
#         except Exception:
#             structured_data = {"raw": structured_output, "error": "⚠️ Could not parse JSON properly."}

#     return {
#         "filename": filename,
#         "extracted_text": extracted_text,
#         "structured_data": structured_data,
#         "ocr_type": ocr_type
#     }


# # import fitz  # PyMuPDF for free OCR (PDF text extraction)
# # import base64
# # import os
# # from azure.ai.formrecognizer import DocumentAnalysisClient
# # from azure.core.credentials import AzureKeyCredential


# # def process_document_from_blob(file_path, filename, filedata, ocr_type="free",
# #                                azure_key=None, azure_endpoint=None, user_id=None):
# #     """
# #     Processes PDF file either with free OCR (PyMuPDF) or paid OCR (Azure).
# #     """

# #     extracted_text = ""

# #     # ---- FREE OCR (PyMuPDF) ----
# #     if ocr_type == "free":
# #         try:
# #             doc = fitz.open(file_path)
# #             text_content = []
# #             for page_num in range(len(doc)):
# #                 page = doc[page_num]
# #                 text_content.append(page.get_text())
# #             extracted_text = "\n".join(text_content)
# #         except Exception as e:
# #             extracted_text = f"❌ Free OCR failed: {str(e)}"

# #     # ---- PAID OCR (Azure) ----
# #     elif ocr_type == "paid":
# #         if not azure_key or not azure_endpoint:
# #             return {
# #                 "filename": filename,
# #                 "extracted_text": "",
# #                 "error": "Azure OCR requires azureKey and azureEndpoint"
# #             }

# #         try:
# #             # Init Azure client
# #             document_client = DocumentAnalysisClient(
# #                 endpoint=azure_endpoint,
# #                 credential=AzureKeyCredential(azure_key)
# #             )

# #             # Convert file back to binary (Azure needs bytes)
# #             file_bytes = base64.b64decode(filedata)

# #             poller = document_client.begin_analyze_document(
# #                 "prebuilt-read",  # OCR model
# #                 document=file_bytes
# #             )
# #             result = poller.result()

# #             text_content = []
# #             for page in result.pages:
# #                 for line in page.lines:
# #                     text_content.append(line.content)

# #             extracted_text = "\n".join(text_content)

# #         except Exception as e:
# #             extracted_text = f"❌ Azure OCR failed: {str(e)}"

# #     else:
# #         extracted_text = "❌ Invalid OCR type provided."

# #     return {
# #         "filename": filename,
# #         "extracted_text": extracted_text,
# #         "ocr_type": ocr_type
# #     }


# # # import pytesseract
# # # from pdf2image import convert_from_path

# # # def process_document_from_blob(
# # #     file_path,
# # #     filename,
# # #     filedata,
# # #     ocr_type="free",
# # #     azure_key=None,
# # #     azure_endpoint=None,
# # #     user_id=None,
# # # ):
# # #     extracted_text = ""

# # #     if ocr_type == "free":
# # #         try:
# # #             # ✅ Convert PDF pages to images
# # #             pages = convert_from_path(file_path, dpi=300)
# # #             text_pages = []
# # #             for page_num, page in enumerate(pages, start=1):
# # #                 text = pytesseract.image_to_string(page)
# # #                 text_pages.append(text)
# # #                 print(f"[OCR] Page {page_num} -> {len(text)} chars extracted")

# # #             extracted_text = "\n".join(text_pages)

# # #         except Exception as e:
# # #             print("❌ Free OCR failed:", str(e))
# # #             extracted_text = ""

# # #     elif ocr_type == "paid":
# # #         # 👉 Stub for Azure OCR (replace later)
# # #         extracted_text = "Azure OCR extracted text here..."

# # #     else:
# # #         extracted_text = "Invalid OCR type provided."

# # #     return {
# # #         "filename": filename,
# # #         "extracted_text": extracted_text,
# # #     }


# # # # import requests
# # # # import textract
# # # # import json, re
# # # # from io import BytesIO
# # # # from PyPDF2 import PdfReader
# # # # from pdf2image import convert_from_bytes
# # # # import pytesseract
# # # # from azure.ai.formrecognizer import DocumentAnalysisClient
# # # # from azure.core.credentials import AzureKeyCredential
# # # # from FAX_POD import settings
# # # # import os   # 👈 add this

# # # # # ---------------- Azure OpenAI Call ----------------
# # # # def call_azure_openai(prompt: str) -> str | None:
# # # #     url = f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"
# # # #     headers = {"Content-Type": "application/json", "api-key": settings.AZURE_OPENAI_KEY}

# # # #     payload = {
# # # #         "messages": [
# # # #             {"role": "system", "content": "You are a helpful assistant for document extraction. Extract ONLY the required fields into valid JSON."},
# # # #             {"role": "user", "content": prompt}
# # # #         ],
# # # #         "temperature": 0.2,
# # # #         "max_tokens": 2000
# # # #     }

# # # #     try:
# # # #         response = requests.post(url, headers=headers, json=payload)
# # # #         response.raise_for_status()
# # # #         return response.json()["choices"][0]["message"]["content"]
# # # #     except Exception as e:
# # # #         print("Azure OpenAI API error:", str(e))
# # # #         return None


# # # # # ---------------- PDF Utilities ----------------
# # # # def is_scanned_pdf(file_bytes: bytes) -> bool:
# # # #     """Check if a PDF has native text or is image-based (scanned)."""
# # # #     try:
# # # #         reader = PdfReader(BytesIO(file_bytes))
# # # #         for page in reader.pages:
# # # #             text = page.extract_text()
# # # #             if text and text.strip():
# # # #                 return False
# # # #         return True
# # # #     except Exception:
# # # #         return True


# # # # # ---------------- OCR Handlers ----------------
# # # # def extract_text_with_tesseract(file_bytes: bytes) -> str:
# # # #     """Free OCR using Tesseract."""
# # # #     try:
# # # #         images = convert_from_bytes(file_bytes)
# # # #         extracted_text = ""
# # # #         for i, image in enumerate(images):
# # # #             page_text = pytesseract.image_to_string(image)
# # # #             extracted_text += f"\n--- Page {i+1} ---\n{page_text}"
# # # #         return extracted_text.strip()
# # # #     except Exception as e:
# # # #         print(f"[ERROR] Tesseract OCR failed: {e}")
# # # #         return ""


# # # # def extract_text_with_azure(file_bytes: bytes, azure_key: str, azure_endpoint: str) -> str:
# # # #     """Paid OCR using Azure Document Intelligence."""
# # # #     if not azure_key or not azure_endpoint:
# # # #         print("⚠️ Azure OCR credentials not found, falling back to Tesseract.")
# # # #         return extract_text_with_tesseract(file_bytes)

# # # #     try:
# # # #         client = DocumentAnalysisClient(
# # # #             endpoint=azure_endpoint,
# # # #             credential=AzureKeyCredential(azure_key)
# # # #         )
# # # #         poller = client.begin_analyze_document(
# # # #             model_id="prebuilt-read",
# # # #             document=BytesIO(file_bytes),
# # # #         )
# # # #         result = poller.result()

# # # #         extracted_text = ""
# # # #         for page_idx, page in enumerate(result.pages):
# # # #             lines = [line.content for line in page.lines]
# # # #             extracted_text += f"\n--- Page {page_idx+1} ---\n" + "\n".join(lines)
# # # #         return extracted_text.strip()
# # # #     except Exception as e:
# # # #         print(f"[ERROR] Azure OCR failed: {e}")
# # # #         return extract_text_with_tesseract(file_bytes)


# # # # # ---------------- Extraction Pipeline ----------------
# # # # def extract_text_from_pdf(file_bytes: bytes, ocr_type: str, azure_key: str = None, azure_endpoint: str = None) -> str:
# # # #     """Auto choose between OCR vs native text extraction."""
# # # #     try:
# # # #         if is_scanned_pdf(file_bytes):
# # # #             if ocr_type == "paid":
# # # #                 return extract_text_with_azure(file_bytes, azure_key, azure_endpoint)
# # # #             return extract_text_with_tesseract(file_bytes)
# # # #         return textract.process(None, input_data=file_bytes).decode("utf-8", errors="ignore")
# # # #     except Exception as e:
# # # #         print(f"[ERROR] extract_text_from_pdf: {e}")
# # # #         return ""


# # # # def extract_structured_data(extracted_text: str, json_schema: str) -> dict:
# # # #     """Send extracted text to Azure OpenAI and get structured JSON."""
# # # #     try:
# # # #         prompt = f"""
# # # # Extract the following information from the text and return only valid JSON strictly in this format:

# # # # Schema:
# # # # {json_schema}

# # # # Text:
# # # # {extracted_text}
# # # # """
# # # #         response_text = call_azure_openai(prompt)
# # # #         if not response_text:
# # # #             raise ValueError("No response from OpenAI")

# # # #         # Clean up markdown fences
# # # #         cleaned_output = re.sub(r"^```(?:json)?|```$", "", response_text.strip()).strip()

# # # #         try:
# # # #             return json.loads(cleaned_output)
# # # #         except json.JSONDecodeError:
# # # #             match = re.search(r"\{.*\}", cleaned_output, re.DOTALL)
# # # #             return json.loads(match.group()) if match else {"raw_text": extracted_text}
# # # #     except Exception as e:
# # # #         return {"error": str(e), "raw_text": extracted_text[:500]}


# # # # def process_document_from_blob(
# # # #     filename=None,
# # # #     file_path=None,
# # # #     filedata=None,
# # # #     json_schema=None,
# # # #     ocr_type="free",
# # # #     azure_key=None,
# # # #     azure_endpoint=None,
# # # #     user_id=None,
# # # # ):
# # # #     """
# # # #     Process a PDF document (from local file or base64).
# # # #     - Free OCR: PyPDF2 / pytesseract
# # # #     - Paid OCR: Azure Document Intelligence
# # # #     - Extract fields with LLM based on json_schema
# # # #     """

# # # #     # ✅ Load PDF bytes
# # # #     if file_path and os.path.exists(file_path):
# # # #         with open(file_path, "rb") as f:
# # # #             pdf_bytes = f.read()
# # # #     elif filedata:
# # # #         pdf_bytes = base64.b64decode(filedata)
# # # #     else:
# # # #         raise ValueError("No file_path or filedata provided for processing")

# # # #     text_content = ""

# # # #     if ocr_type == "free":
# # # #         # Example using PyPDF2
# # # #         from PyPDF2 import PdfReader
# # # #         reader = PdfReader(file_path)
# # # #         for page in reader.pages:
# # # #             text_content += page.extract_text() or ""

# # # #     elif ocr_type == "paid":
# # # #         if not azure_key or not azure_endpoint:
# # # #             raise ValueError("Azure key/endpoint required for paid OCR")
# # # #         # TODO: call Azure OCR API with pdf_bytes
# # # #         text_content = "Azure OCR result text here"

# # # #     else:
# # # #         raise ValueError("Invalid OCR type")

# # # #     # TODO: Use your LLM here to map `text_content` → json_schema
# # # #     # For now just mock response
# # # #     parsed_output = {
# # # #         "filename": filename,
# # # #         "extracted_text": text_content[:500],  # preview
# # # #         "structured_data": {"mock": "values based on schema"}
# # # #     }

# # # #     return parsed_output
