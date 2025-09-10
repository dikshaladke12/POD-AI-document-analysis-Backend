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


# class UploadPDFs(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             files_data = request.data.get("files", [])
#             processed_files = []

#             for file_dict in files_data:
#                 filename = file_dict.get("filename")
#                 filedata = file_dict.get("filedata")
#                 fax_type = file_dict.get("order_type")
#                 mimetype = file_dict.get("mimetype", "application/pdf")

#                 if not filename or not filedata:
#                     continue

#                 try:
#                     # Step 1: Convert base64 to file
#                     inmemory_file = decode_base64_to_inmemory_file(filedata, filename, mimetype)
#                     # print("inmemory_file", inmemory_file)

#                     # Step 2: Generate unique name
#                     unique_filename = generate_unique_filename(inmemory_file.name)
#                     # print("unique_filename", unique_filename)

#                     # ✅ Set the file name directly
#                     inmemory_file.name = unique_filename

#                     # ✅ Now call upload WITHOUT prefix
#                     file_url = upload_file_to_azure_blob(inmemory_file)
#                     print("file_url", file_url)
#                     if not file_url:
#                         return utils.error_response(
#                             message="Upload failed.",
#                             errors="Azure Blob did not return a valid URL.",
#                             status_code=500,
#                             api_status_code=500
#                         )

#                     # Step 4: Process uploaded file
#                     result = process_document_from_blob(
#                         file_url=file_url,
#                         user_id=request.user.id,
#                         file_name=unique_filename,
#                         fax_type=fax_type
#                     )
#                     # print("result",result)
#                     if not result:
#                         return utils.error_response(
#                             message="Processing failed.",
#                             errors="Unable to parse document.",
#                             status_code=500,
#                             api_status_code=500
#                         )

#                     processed_files.append({
#                         "filename": unique_filename,
#                         "url": file_url,
#                         "id": result.get("id"),
#                         "structured_data": result.get("structured_data")
#                     })

#                 except Exception as inner_error:
#                     return utils.error_response("File processing error", str(inner_error), 500, 500)

#             return utils.success_response(
#                 message="Upload & processing successful.",
#                 data={"files": processed_files},
#                 status_code=200
#             )
#         except Exception as outer_error:
#             return utils.error_response("Unexpected error", str(outer_error), 500, 500)


# class UploadPDFs(APIView):

#     def post(self, request):
#         try:
#             file_b64 = request.data.get("file")
#             json_input = request.data.get("jsonInput")
#             ocr_type = request.data.get("ocrType", "free")   # free or paid
#             azure_key = request.data.get("azureKey")         # only for paid OCR
#             azure_endpoint = request.data.get("azureEndpoint")

#             if not file_b64 or not json_input:
#                 return utils.error_response(
#                     "Missing fields",
#                     "file and jsonInput are required",
#                     400,
#                     400
#                 )

#             # ✅ Step 1: Decode base64 → InMemory file
#             inmemory_file = decode_base64_to_inmemory_file(
#                 file_b64,
#                 "uploaded.pdf",
#                 "application/pdf"
#             )
#             unique_filename = generate_unique_filename(inmemory_file.name)
#             inmemory_file.name = unique_filename

#             # ✅ Step 2: Save locally under media/uploaded_files
#             upload_dir = os.path.join(settings.MEDIA_ROOT, "uploaded_files")
#             os.makedirs(upload_dir, exist_ok=True)
#             local_file_path = os.path.join(upload_dir, unique_filename)

#             with open(local_file_path, "wb") as f:
#                 for chunk in inmemory_file.chunks():
#                     f.write(chunk)

#             # ✅ Step 3: Process document (OCR + LLM) → returns structured JSON
#             result = process_document_from_blob(
#                 file_path=local_file_path,
#                 filedata=file_b64,
#                 filename=unique_filename,
#                 json_schema=json_input,
#                 ocr_type=ocr_type,
#                 azure_key=azure_key,
#                 azure_endpoint=azure_endpoint,
#                 user_id=request.user.id
#             )

#             # ✅ Step 4: Just return result (no DB save)
#             return utils.success_response(
#                 message="Upload & processing successful.",
#                 data=result,
#                 status_code=200
#             )

#         except Exception as e:
#             return utils.error_response("Unexpected error", str(e), 500, 500)


# class UploadPDFs(APIView):
#     permission_classes = []  # 👈 No authentication required

#     def post(self, request):
#         try:
#             file_b64 = request.data.get("file")
#             json_input = request.data.get("jsonInput")
#             ocr_type = request.data.get("ocrType", "free")
#             azure_key = request.data.get("azureKey")
#             azure_endpoint = request.data.get("azureEndpoint")

#             if not file_b64 or not json_input:
#                 return utils.error_response(
#                     "Missing fields",
#                     "file and jsonInput are required",
#                     400,
#                     400
#                 )

#             # Step 1: Decode base64 → InMemory file
#             inmemory_file = decode_base64_to_inmemory_file(
#                 file_b64, "uploaded.pdf", "application/pdf"
#             )
#             unique_filename = generate_unique_filename(inmemory_file.name)
#             inmemory_file.name = unique_filename

#             # Step 2: Save file to media/uploads
#             upload_dir = os.path.join(settings.MEDIA_ROOT, "uploaded_files")
#             os.makedirs(upload_dir, exist_ok=True)
#             file_path = os.path.join(upload_dir, unique_filename)

#             with open(file_path, "wb") as f:
#                 for chunk in inmemory_file.chunks():
#                     f.write(chunk)

#             print(f"✅ File saved at {file_path}")

#             # Step 3: Process document (OCR + LLM)
#             result = process_document_from_blob(
#                 filename=unique_filename,
#                 file_path=file_path,   # now supported
#                 filedata=file_b64,
#                 json_schema=json_input,
#                 ocr_type=ocr_type,
#                 azure_key=azure_key,
#                 azure_endpoint=azure_endpoint,
#                 user_id=request.user.id,
#             )

#             return utils.success_response(
#                 message="Upload & processing successful.",
#                 data=result,
#                 status_code=200
#             )

#         except Exception as e:
#             return utils.error_response("Unexpected error", str(e), 500, 500)

# class UploadPDFs(APIView):
#     # permission_classes = [IsAuthenticated]  # 🔴 Disabled auth for now

#     def post(self, request):
#         try:
#             file_b64 = request.data.get("file")
#             ocr_type = request.data.get("ocrType", "free")
#             azure_key = request.data.get("azureKey")
#             azure_endpoint = request.data.get("azureEndpoint")

#             if not file_b64:
#                 return utils.error_response(
#                     "Missing fields",
#                     "file is required",
#                     400,
#                     400
#                 )

#             # Step 1: Decode file
#             inmemory_file = decode_base64_to_inmemory_file(file_b64, "uploaded.pdf", "application/pdf")
#             unique_filename = generate_unique_filename(inmemory_file.name)
#             inmemory_file.name = unique_filename

#             # Step 2: Save to media/uploads
#             upload_dir = os.path.join(settings.MEDIA_ROOT, "uploaded_files")
#             os.makedirs(upload_dir, exist_ok=True)
#             file_path = os.path.join(upload_dir, unique_filename)

#             with open(file_path, "wb") as f:
#                 for chunk in inmemory_file.chunks():
#                     f.write(chunk)

#             print("✅ File saved at:", file_path)

#             # Step 3: Process document (OCR only)
#             result = process_document_from_blob(
#                 file_path=file_path,
#                 filename=unique_filename,
#                 filedata=file_b64,
#                 ocr_type=ocr_type,
#                 azure_key=azure_key,
#                 azure_endpoint=azure_endpoint,
#                 user_id=request.user.id if request.user else None
#             )

#             return utils.success_response(
#                 message="Upload & processing successful.",
#                 data=result,
#                 status_code=200
#             )

#         except Exception as e:
#             return utils.error_response("Unexpected error", str(e), 500, 500)


class UploadPDFs(APIView):
    # permission_classes = [IsAuthenticated]  # 🔴 Disabled auth for now

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



class SoftDeleteDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        try:
            doc = DocumentHistory.objects.get(id=doc_id, userId=request.user.id, is_deleted=False)
            doc.is_deleted = True
            doc.save()
            return utils.success_response(
                message="Document removed successfully.",
                data={"id": doc.id, "is_deleted": doc.is_deleted},
                status_code=status.HTTP_200_OK
            )
        except DocumentHistory.DoesNotExist:
            return utils.error_response(
                message="Document not found or already removed.",
                errors=f"No active document with ID {doc_id} for this user.",
                status_code=status.HTTP_404_NOT_FOUND,
                api_status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return utils.error_response(
                message="Internal Server Error.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                api_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentSearchListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = DocumentHistory.objects.filter(is_deleted=False)
    serializer_class = DocumentHistorySerializer
    pagination_class = DocumentPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'file_name', 'first_name', 'last_name', 'service_name', 'email'
    ]

    ordering_fields = ['uploaded_at', 'file_name', 'DOB']
    ordering = ['-uploaded_at']

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
            data = self.get_paginated_response(serializer.data).data if page is not None else serializer.data
            return utils.success_response(
                message="Documents fetched successfully.",
                data={"documents": data},
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch documents.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                api_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentDetailView(generics.RetrieveAPIView):
    queryset = DocumentHistory.objects.filter(is_deleted=False)
    serializer_class = DocumentHistorySerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            document = self.get_object()
            serializer = self.get_serializer(document)
            return utils.success_response(
                message="Fax document fetched successfully.",
                data={"fax": serializer.data},
                status_code=status.HTTP_200_OK
            )
        except DocumentHistory.DoesNotExist:
            return utils.error_response(
                message="Fax document not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to retrieve fax document.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class FaxProviderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            username = request.data.get("username", "").strip().lower()

            # ✅ Manually encrypt the username using the model field logic
            username_field = FaxProvider._meta.get_field("username")
            encrypted_username = username_field.encrypt(username)

            # ✅ Check if an active (not deleted) provider exists with same encrypted username
            if FaxProvider.objects.filter(
                user=request.user,
                username=encrypted_username,
                is_deleted=False
            ).exists():
                return utils.error_response(
                    message=f"Provider with username '{username}' already exists for your account.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # ✅ Save using serializer
            serializer = FaxProviderSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(user=request.user)
                return utils.success_response(
                    message="Fax provider added successfully.",
                    data={"provider": serializer.data},
                    status_code=status.HTTP_200_OK
                )

            return utils.error_response(
                message="Incorrect details inserted.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return utils.error_response(
                message="Failed to add fax provider.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FaxProviderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FaxProviderSerializer
    pagination_class = DocumentPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'company_number', 'provider']
    ordering_fields = ['created_at', 'username', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return FaxProvider.objects.filter(user=self.request.user, is_deleted=False)

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Optional: Print decrypted passwords for test (remove in production)
            # for item in queryset:
            #     print(f"[Decryption Test] Username: {item.username}, Password: {item.password}")

            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
            data = self.get_paginated_response(serializer.data).data if page is not None else serializer.data

            return utils.success_response(
                message="Fax providers fetched successfully.",
                data={"providers": data},
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch fax providers.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FaxProviderPartialUpdateView(UpdateAPIView):
    serializer_class = FaxProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FaxProvider.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            message = "Fax provider deleted successfully." if request.data.get('is_deleted') is True else "Fax provider updated successfully."

            return utils.success_response(
                message=message,
                data={"provider": serializer.data},
                status_code=status.HTTP_200_OK
            )

        except FaxProvider.DoesNotExist:
            return utils.error_response(
                message="Fax provider not found.",
                errors="No matching record for this user.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to update fax provider.",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )



class FaxProviderDetailView(RetrieveAPIView):
    serializer_class = FaxProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FaxProvider.objects.filter(user=self.request.user, is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return utils.success_response(
                message="Fax provider fetched successfully.",
                data={"provider": serializer.data},
                status_code=status.HTTP_200_OK
            )
        except FaxProvider.DoesNotExist:
            return utils.error_response(
                message="Fax provider not found.",
                errors="No matching record for this user.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch fax provider.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class FetchFaxesForUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            process_user_providers_faxes(request.user)
            return utils.success_response(
                message="Fax fetch process completed.",
                data={},
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return utils.error_response(
                message="Failed to fetch faxes.",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

