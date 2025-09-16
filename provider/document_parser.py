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


def call_gemini(prompt: str) -> str:
    """Call Google Gemini for structured JSON output."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "You are a helpful assistant for medical document extraction. Return only valid JSON."},
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2500
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        # Gemini output is inside candidates -> content -> parts -> text
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except requests.RequestException as e:
        return f"❌ Gemini API error: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"❌ Unexpected Gemini response: {str(e)}"


def process_document_from_blob(file_path, filename, filedata, ocr_type="free",
                               azure_key=None, azure_endpoint=None,
                               user_id=None, json_input=None):
    """
    Process document with free/paid OCR + Gemini for structured output.
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
        structured_output = call_gemini(prompt)

    return {
        "filename": filename,
        "ocr_type": ocr_type,
        "raw_text": raw_text,
        "structured_output": structured_output
    }
