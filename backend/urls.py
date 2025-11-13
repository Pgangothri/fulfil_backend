from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    path("products/", RedirectView.as_view(url="/", permanent=False)),
]
