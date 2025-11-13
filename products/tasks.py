import csv
import io
from datetime import datetime
import requests
from celery import shared_task
from django.db import transaction, IntegrityError
from .models import Product, ImportJob, Webhook


@shared_task(bind=True)
def import_products(self, job_id, file_content):
    """
    Celery task to import products from CSV content.
    Handles large files in batches, updates job progress,
    and triggers webhooks for created/updated products.
    """
    try:
        # Fetch the import job and update status
        job = ImportJob.objects.get(id=job_id)
        job.status = "processing"
        job.save(update_fields=["status"])

        # Prepare file-like CSV reader
        file_like = io.StringIO(file_content)
        reader = csv.DictReader(file_like)
        rows = list(reader)

        total_records = len(rows)
        processed_records = 0
        errors = []

        job.total_records = total_records
        job.save(update_fields=["total_records"])

        batch_size = 1000

        # Process CSV rows in batches for better performance
        for i in range(0, total_records, batch_size):
            batch = rows[i : i + batch_size]

            with transaction.atomic():
                for row_num, row in enumerate(batch, start=i + 1):
                    try:
                        sku = row.get("sku", "").strip().lower()
                        name = row.get("name", "").strip()
                        description = row.get("description", "").strip()

                        if not sku:
                            errors.append(f"Row {row_num}: SKU is required")
                            continue

                        # Update or create product (case-insensitive SKU)
                        product, created = Product.objects.update_or_create(
                            sku__iexact=sku,
                            defaults={
                                "sku": sku,
                                "name": name,
                                "description": description,
                                "active": True,
                            },
                        )

                        processed_records += 1

                        # Send progress every 100 records
                        if processed_records % 100 == 0:
                            job.processed_records = processed_records
                            job.save(update_fields=["processed_records"])
                            self.update_state(
                                state="PROGRESS",
                                meta={
                                    "current": processed_records,
                                    "total": total_records,
                                    "status": f"Processed {processed_records}/{total_records}",
                                },
                            )

                        # Trigger webhook for created/updated product
                        event_type = "product.created" if created else "product.updated"
                        trigger_webhook.delay(event_type, product.id)

                    except IntegrityError:
                        errors.append(f"Row {row_num}: Duplicate SKU {sku}")
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")

        # Finalize job
        job.status = "completed"
        job.processed_records = processed_records
        job.errors = errors
        job.completed_at = datetime.now()
        job.save()

        # Trigger webhook for import completion
        trigger_webhook.delay("import.completed", job.id)

        return {
            "status": "completed",
            "processed": processed_records,
            "total": total_records,
            "errors": len(errors),
        }

    except Exception as e:
        job = ImportJob.objects.filter(id=job_id).first()
        if job:
            job.status = "failed"
            job.errors = [str(e)]
            job.save(update_fields=["status", "errors"])
        raise e


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=3,
)
def trigger_webhook(self, event_type, resource_id):
    """
    Trigger all active webhooks for a specific event.
    Includes retry logic for failed requests.
    """
    webhooks = Webhook.objects.filter(event_type=event_type, is_active=True)

    for webhook in webhooks:
        try:
            payload = {
                "event": event_type,
                "resource_id": resource_id,
                "timestamp": datetime.now().isoformat(),
            }

            response = requests.post(webhook.url, json=payload, timeout=10)
            print(f"✅ Webhook sent to {webhook.url} - Status {response.status_code}")

        except requests.RequestException as e:
            print(f"❌ Webhook failed for {webhook.url}: {e}")
            raise self.retry(exc=e)  # retry failed webhook


@shared_task
def bulk_delete_products():
    """
    Deletes all products and triggers a 'product.deleted' webhook.
    """
    try:
        count = Product.objects.count()
        Product.objects.all().delete()
        trigger_webhook.delay("product.deleted", "all")

        return {"deleted_count": count}

    except Exception as e:
        print(f"Bulk delete failed: {e}")
        raise e
