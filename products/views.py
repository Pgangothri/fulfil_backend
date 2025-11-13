import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from celery.result import AsyncResult

from .models import Product, ImportJob, Webhook
from .tasks import import_products, bulk_delete_products, trigger_webhook


# ✅ Base class to disable CSRF globally for API endpoints only
@method_decorator(csrf_exempt, name="dispatch")
class CsrfExemptView(View):
    pass


# ========== FRONTEND AUTH VIEWS ==========


def signup_view(request):
    """Render signup page and handle registration."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "All fields are required.")
            return render(request, "products/Signup.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "products/Signup.html")

        User.objects.create_user(username=username, password=password)
        messages.success(request, "Signup successful! Please login.")
        return redirect("Login")

    return render(request, "products/Signup.html")


def login_view(request):
    """Render login page and authenticate user."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "products/Login.html")


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("Login")
    return render(request, "products/logout.html")


def home(request):
    """Dashboard page (requires login)."""
    if not request.user.is_authenticated:
        return redirect("Login")
    return render(request, "products/home.html")


# ========== PRODUCT IMPORTER API ==========


class ProductUploadView(CsrfExemptView):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        return render(request, "products/upload.html")

    def post(self, request):
        try:
            if "file" not in request.FILES:
                return JsonResponse({"error": "No file provided"}, status=400)

            csv_file = request.FILES["file"]

            if not csv_file.name.endswith(".csv"):
                return JsonResponse({"error": "File must be a CSV"}, status=400)

            file_content = csv_file.read().decode("utf-8")

            job = ImportJob.objects.create(file_name=csv_file.name, status="pending")
            task = import_products.delay(job.id, file_content)
            job.task_id = task.id
            job.save()

            return JsonResponse(
                {"job_id": job.id, "task_id": task.id, "status": "Upload started"}
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ProductListView(CsrfExemptView):
    def get(self, request):
        sku_filter = request.GET.get("sku", "")
        name_filter = request.GET.get("name", "")
        active_filter = request.GET.get("active", "")

        products = Product.objects.all()

        if sku_filter:
            products = products.filter(sku__icontains=sku_filter)
        if name_filter:
            products = products.filter(name__icontains=name_filter)
        if active_filter:
            if active_filter.lower() == "true":
                products = products.filter(active=True)
            elif active_filter.lower() == "false":
                products = products.filter(active=False)

        paginator = Paginator(products.order_by("sku"), 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        products_data = [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "active": p.active,
                "created_at": p.created_at.isoformat(),
            }
            for p in page_obj
        ]

        return JsonResponse(
            {
                "products": products_data,
                "total_pages": paginator.num_pages,
                "current_page": page_obj.number,
                "total_count": paginator.count,
            }
        )


class ProductDetailView(CsrfExemptView):
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        return JsonResponse(
            {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "active": product.active,
            }
        )

    def post(self, request, product_id=None):
        try:
            data = json.loads(request.body)

            if product_id:
                product = get_object_or_404(Product, id=product_id)
                created = False
            else:
                product = Product()
                created = True

            product.sku = data.get("sku", product.sku)
            product.name = data.get("name", product.name)
            product.description = data.get("description", product.description)
            product.active = data.get("active", True)
            product.save()

            event_type = "product.created" if created else "product.updated"
            trigger_webhook.delay(event_type, product.id)

            return JsonResponse({"status": "success", "product_id": product.id})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            product.delete()
            trigger_webhook.delay("product.deleted", product_id)
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class BulkDeleteView(CsrfExemptView):
    def post(self, request):
        try:
            task = bulk_delete_products.delay()
            return JsonResponse({"task_id": task.id, "status": "Deletion started"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class TaskStatusView(CsrfExemptView):
    def get(self, request, task_id):
        task = AsyncResult(task_id)
        response_data = {"task_id": task_id, "status": task.status}

        if task.status in ["PROGRESS", "SUCCESS"]:
            response_data.update(task.result or {})
        elif task.status == "FAILURE":
            response_data["error"] = str(task.result)

        return JsonResponse(response_data)


class WebhookView(CsrfExemptView):
    def get(self, request):
        webhooks = Webhook.objects.all()
        webhooks_data = [
            {
                "id": w.id,
                "url": w.url,
                "event_type": w.event_type,
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat(),
            }
            for w in webhooks
        ]
        return JsonResponse({"webhooks": webhooks_data})

    def post(self, request):
        try:
            data = json.loads(request.body)
            webhook = Webhook.objects.create(
                url=data["url"],
                event_type=data["event_type"],
                is_active=data.get("is_active", True),
            )
            return JsonResponse({"status": "created", "webhook_id": webhook.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, webhook_id):
        try:
            webhook = get_object_or_404(Webhook, id=webhook_id)
            webhook.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def put(self, request, webhook_id):
        try:
            webhook = get_object_or_404(Webhook, id=webhook_id)
            data = json.loads(request.body)
            if "url" in data:
                webhook.url = data["url"]
            if "event_type" in data:
                webhook.event_type = data["event_type"]
            if "is_active" in data:
                webhook.is_active = data["is_active"]
            webhook.save()
            return JsonResponse({"status": "updated", "webhook_id": webhook.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class WebhookTestView(CsrfExemptView):
    def post(self, request, webhook_id):
        try:
            webhook = get_object_or_404(Webhook, id=webhook_id)
            trigger_webhook.delay(webhook.event_type, "test")
            return JsonResponse({"status": "Test triggered"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
