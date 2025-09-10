from django.contrib import admin
from django.urls import path, include
from FAX_POD import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


urlpatterns = [
   path('admin/', admin.site.urls),
   path('provider/',include("provider.urls")),
   # path('auth/',include("authentication.urls")),
   # path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # Swagger UI
]


# Serve static files
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



