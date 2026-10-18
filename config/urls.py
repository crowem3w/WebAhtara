from django.contrib import admin
from django.urls import path

admin.site.site_header = "Ahtara listings admin"

urlpatterns = [path("admin/", admin.site.urls)]
