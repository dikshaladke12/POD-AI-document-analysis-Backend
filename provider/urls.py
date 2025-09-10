from django.urls import path
from .views import (
    UploadPDFs,
    )
from provider.image_ocr import OCRUploadAPIView

urlpatterns = [
    path('upload/', UploadPDFs.as_view(), name='inspect'),
]
