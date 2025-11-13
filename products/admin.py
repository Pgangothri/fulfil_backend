from django.contrib import admin
from .models import Product, ImportJob, Webhook


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "active", "created_at")
    search_fields = ("sku", "name")
    list_filter = ("active",)


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "status",
        "total_records",
        "processed_records",
        "created_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("file_name",)


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("url", "event_type", "is_active", "created_at")
    list_filter = ("event_type", "is_active")
