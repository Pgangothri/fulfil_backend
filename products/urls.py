from django.urls import path
from . import views

urlpatterns = [
    path("", views.signup_view, name="Signup"),
    path("login/", views.login_view, name="Login"),
    path("logout/", views.logout_view, name="Logout"),
    path("dashboard/", views.home, name="home"),
    path("api/upload/", views.ProductUploadView.as_view(), name="upload"),
    path("api/products/", views.ProductListView.as_view(), name="product-list"),
    path(
        "api/products/create/", views.ProductDetailView.as_view(), name="product-create"
    ),
    path(
        "api/products/<int:product_id>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path("api/bulk-delete/", views.BulkDeleteView.as_view(), name="bulk-delete"),
    path(
        "api/tasks/<str:task_id>/", views.TaskStatusView.as_view(), name="task-status"
    ),
    path("api/webhooks/", views.WebhookView.as_view(), name="webhook-list"),
    path("api/webhooks/create/", views.WebhookView.as_view(), name="webhook-create"),
    path(
        "api/webhooks/<int:webhook_id>/",
        views.WebhookView.as_view(),
        name="webhook-detail",
    ),
    path(
        "api/webhooks/<int:webhook_id>/test/",
        views.WebhookTestView.as_view(),
        name="webhook-test",
    ),
]
