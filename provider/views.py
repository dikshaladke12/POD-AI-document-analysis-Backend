import os   # 👈 add this
from datetime import datetime
from rest_framework import generics, filters
from FAX_POD import settings, utils
from FAX_POD.utils import (decode_base64_to_inmemory_file,
                           generate_unique_filename,
                           upload_file_to_azure_blob
                          )
from rest_framework.generics import UpdateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from provider.models import DocumentHistory, FaxProvider 
import textract
import tempfile
from provider.document_parser import process_document_from_blob

import json
import re
from provider.serializers import DocumentHistorySerializer, FaxProviderSerializer
from provider.pagination import DocumentPagination
import base64
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import requests
from provider.utils.fax_processing import process_user_providers_faxes





def fetch_pdf_from_url(blob_url):
    response = requests.get(blob_url)
    response.raise_for_status()
    return response.content

class InspectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_id = request.user.id

            total_fax_providers = FaxProvider.objects.filter(user_id=user_id, is_deleted=False).count()
            fetched_faxes = DocumentHistory.objects.filter(userId=user_id, uploaded=False, is_deleted=False).count()
            uploaded_documents = DocumentHistory.objects.filter(userId=user_id, uploaded=True, is_deleted=False).count()

            return utils.success_response(
                message="User-specific fax stats fetched successfully.",
                data={
                    "total_fax_providers": total_fax_providers,
                    "fetched_faxes": fetched_faxes,
                    "uploaded_documents": uploaded_documents
                },
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch fax stats.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                api_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UploadPDFs(APIView):
    permission_classes = [IsAuthenticated]  

    def post(self, request):
        try:
            file_b64 = request.data.get("file")
            ocr_type = request.data.get("ocrType", "free")
            azure_key = request.data.get("azureKey")
            azure_endpoint = request.data.get("azureEndpoint")
            schema = request.data.get("schema")  # JSON schema string if provided

            if not file_b64:
                return utils.error_response(
                    "Missing fields",
                    "file is required",
                    400,
                    400
                )

            # Parse schema if provided
            schema_dict = None
            if schema:
                import json
                try:
                    schema_dict = json.loads(schema)
                except Exception:
                    schema_dict = None

            # Step 1: Decode file
            inmemory_file = decode_base64_to_inmemory_file(file_b64, "uploaded.pdf", "application/pdf")
            unique_filename = generate_unique_filename(inmemory_file.name)
            inmemory_file.name = unique_filename

            # Step 2: Save to media/uploads
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploaded_files")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, unique_filename)

            with open(file_path, "wb") as f:
                for chunk in inmemory_file.chunks():
                    f.write(chunk)

            print("✅ File saved at:", file_path)

            # Step 3: Process document (OCR + optional LLM)
            result = process_document_from_blob(
                file_path=file_path,
                filename=unique_filename,
                filedata=file_b64,
                ocr_type=ocr_type,
                azure_key=azure_key,
                azure_endpoint=azure_endpoint,
                user_id=request.user.id if request.user else None,
                json_input=request.data.get("jsonInput")   # 🔑 NEW
            )

            return utils.success_response(
                message="Upload & processing successful.",
                data=result,
                status_code=200
            )

        except Exception as e:
            return utils.error_response("Unexpected error", str(e), 500, 500)


def fetch_pdf_from_url(blob_url):
    response = requests.get(blob_url)
    response.raise_for_status()
    return BytesIO(response.content)
