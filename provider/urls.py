from django.urls import path
from .views import (
    UploadPDFs,
    )

urlpatterns = [
    path('upload/', UploadPDFs.as_view(), name='inspect'),
]
