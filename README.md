# Large CSV Product Uploader (Django + Celery + Channels)

A scalable Django application for uploading very large product CSV files (up to 500,000 products) from the web UI, with:

- Modern async file upload interface
- Real-time progress updates using Django Channels (WebSockets)
- Background parsing/processing with Celery tasks
- SKU-based overwrite (case-insensitive), with enforced uniqueness
- Automatic webhooks for product creation, update, import completion, and deletion

---

## Features

- **Intuitive file upload UI:** Drag-and-drop or select CSV file
- **Real-time upload & import status:** Progress bar or status message
- **Handles huge CSVs:** Efficient batch import, optimized for responsiveness; runs in background
- **SKU overwrite:** Automatically updates products for duplicate/case-insensitive SKUs
- **Webhook management:** Configure, test, enable/disable webhooks for system events
- **Live status updates:** "Uploading...", "Parsing CSV...", "Import complete!"

---

## Tech Stack

- **Backend:** Django, Django REST Framework, Celery ,Redis, Django Channels
- **Frontend:** HTML,CSS,JavaScript
- **Database:** PostgreSQL
- **WebSockets:** Channels + Redis backend

---

## Quickstart

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (for Channels and Celery broker)

1. Clone the repository:
   ```bash
   git clone https://github.com/Pgangothri/fulfil_backend.git
   cd your-project
2. Create Virtual environment
   ```bash
   python m venv venv
3. Activate Virtual Environment
   ```bash
   For Windows venv/Scripts/activate
   For Linux   source venv/bin/activate
4. Install Requirements
   ```bash
   pip install -r requirements.txt
   
### Setup

1. **Configure PostgreSQL and Redis (update `settings.py`)**
2. **Run database migrations**
    ```
    python manage.py migrate
    ```
3. **Start Celery worker and Channels worker**  
   _Separate terminals:_
    ```
    celery -A yourproject worker -l info
   
### Run Server
```
 python manage.py runserver

- API Endpoints
| URL                              | Method | Description                     |
| -------------------------------- | ------ | ------------------------------- |
| /api/upload/                     | POST   | Upload CSV, returnsjob_id       |
| /api/products/                   | GET    | List products                   |
| /api/products/create/            | POST   | Create single product           |
| /api/products/<product_id>/      | GET    | Get product details             |
| /api/bulk-delete/                | POST   | Delete all products             |
| /api/tasks/<task_id>/            | GET    | Get import task status/progress |
| /api/webhooks/                   | GET    | List webhooks                   |
| /api/webhooks/create/            | POST   | Add webhook                     |
| /api/webhooks/<webhook_id>/      | GET    | Webhook details                 |
| /api/webhooks/<webhook_id>/test/ | POST   | Test webhook                    |
| /signup                          | POST   | Signup                          |
|/login                            |POST    | Login                           |
|/logout                           |POST    | Logout                          |
|/dashboard                        |GET     | Dashboard                       |
