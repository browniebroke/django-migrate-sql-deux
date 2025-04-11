from django.contrib import admin
from django.urls.conf import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
