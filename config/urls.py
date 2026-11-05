from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "RIS Demo - Administración"
admin.site.site_title = "RIS Demo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ris.urls")),
]
