from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from recruitment.health import health_check

urlpatterns = [
    path('healthz/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('recruitment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
