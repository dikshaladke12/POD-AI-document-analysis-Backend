import os
import pytesseract
from pdf2image import convert_from_bytes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from PIL import Image
from django.conf import settings

class OCRUploadAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        ext = os.path.splitext(file.name)[-1].lower()

        images = []
        if ext == ".pdf":
            images = convert_from_bytes(file.read(), fmt="jpeg")
        else:
            img = Image.open(file)
            images.append(img)

        result_text = ""
        for img in images:
            text = pytesseract.image_to_string(img)
            result_text += text + "\n---\n"

        print("result_text : ",result_text)
        return Response({"text": result_text})
