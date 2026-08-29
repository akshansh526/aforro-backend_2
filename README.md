# Aforro Backend

A backend API project built with **Django and Django REST Framework**.

The project provides APIs for products, stores, inventory, orders, search, and background task processing.

---

## What This Project Does

This backend mainly handles:

- Products
- Stores
- Store inventory
- Orders
- Product search
- Search suggestions
- Stock checking
- Order creation
- Order status
- Background tasks using Celery
- Redis caching
- API documentation using Swagger

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Django | Backend web framework |
| Django REST Framework | Creating REST APIs |
| MySQL / SQLite | Database |
| Redis | Cache and Celery message broker |
| Celery | Running background tasks |
| drf-spectacular | Swagger / OpenAPI documentation |
| Docker | Running services such as Redis |

---

## Project Structure

```text
aforro_backend_2/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── __init__.py
│
├── products/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── stores/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── orders/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── tasks.py
│   └── urls.py
│
├── search/
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
│
├── manage.py
├── schema.yml
└── README.md
```

---

# Main Features

## 1. Product API

The product API is used to work with products.

A product can contain information such as:

- Product ID
- Product title
- Price
- Category

Products are also used by the inventory and order APIs.

---

## 2. Store API

Stores are connected with inventory and orders.

Each store can have:

- Different products
- Different stock quantities
- Different orders

---

## 3. Inventory API

Inventory tells us how many products are available in a store.

Example:

```text
Store 7
Product: Advanced cohesive frame
Available quantity: 1
```

The inventory API can return the products available in a particular store.

Example endpoint:

```text
GET /api/stores/7/inventory/
```

---

# 4. Order API

The order API is one of the main parts of this project.

To create an order, we send:

```json
{
  "store_id": 7,
  "items": [
    {
      "product_id": 790,
      "quantity_requested": 1
    }
  ]
}
```

The backend checks the requested product and its available stock.

---

## Order Flow

The basic order flow is:

```text
Client
   |
   v
Order API
   |
   v
Validate Request
   |
   v
Check Store
   |
   v
Check Product
   |
   v
Check Inventory
   |
   +---- Not enough stock ----> REJECTED
   |
   |
   +---- Enough stock ---------> Deduct Stock
                                      |
                                      v
                                  CONFIRMED
                                      |
                                      v
                                  Create Order
```

---

# 5. Stock Checking

Before creating a confirmed order, the backend checks inventory.

For example:

```text
Requested quantity = 25
Available quantity = 1
```

The order will be rejected.

Response:

```json
{
  "message": "Order rejected due to insufficient stock.",
  "status": "REJECTED"
}
```

The stock is **not deducted** when the order is rejected.

---

## Successful Order

If:

```text
Requested quantity = 1
Available quantity = 5
```

then:

```text
5 - 1 = 4
```

The inventory becomes:

```text
Available quantity = 4
```

and the order status becomes:

```text
CONFIRMED
```

---

# 6. Database Transactions

The order creation code uses:

```python
@transaction.atomic
```

This is important because order creation and stock deduction should work as one database operation.

If something goes wrong during the transaction, Django can roll back the database changes.

The inventory rows are also locked using:

```python
select_for_update()
```

This helps prevent two requests from changing the same stock at the same time.

---

# 7. Order Models

The project uses three main models for orders.

### Order

Stores the main order information.

```text
Order
 ├── store
 ├── status
 └── created_at
```

Possible statuses:

```text
PENDING
CONFIRMED
REJECTED
```

### OrderItem

Stores the products inside an order.

```text
OrderItem
 ├── order
 ├── product
 └── quantity_requested
```

### Inventory

Stores the stock of a product for a store.

```text
Inventory
 ├── store
 ├── product
 └── quantity
```

---

# 8. Serializers

Django REST Framework serializers are used to convert data between:

```text
Python / Django objects
        |
        v
       JSON
```

They also validate incoming data.

For example:

```python
quantity_requested = serializers.IntegerField(min_value=1)
```

This means the requested quantity cannot be zero or negative.

The serializers also check:

- Store exists
- Product exists
- At least one item is provided
- Duplicate products are not allowed

---

# 9. Order List API

Orders for a particular store can be viewed using:

```text
GET /api/stores/{store_id}/orders/
```

Example:

```text
GET /api/stores/7/orders/
```

The API returns the orders of store 7.

The newest orders are shown first.

---

# 10. Search API

The project also contains a product search system.

The search API can search products using a query.

Example:

```text
GET /api/search/?q=phone
```

There is also a suggestion API:

```text
GET /api/search/suggest/?q=pho
```

The suggestion API can return matching product titles.

Example:

```json
[
  {
    "id": 790,
    "title": "Advanced cohesive frame"
  }
]
```

---

# 11. Redis

Redis is used in the project mainly for caching.

Caching means keeping frequently requested data in memory so that the application does not have to perform the same database operation every time.

The basic flow is:

```text
Search Request
      |
      v
Check Redis Cache
      |
   +--+--+
   |     |
 Found  Not Found
   |     |
   v     v
Return  Database
Result     |
           v
       Save in Redis
           |
           v
       Return Result
```

Redis is also used as the message broker for Celery.

---

# 12. Celery

Celery is used to run background tasks.

Instead of making the user wait for a task to finish, Django can send the task to Celery.

Example:

```text
Django
   |
   | Send task
   v
Redis
   |
   | Task message
   v
Celery Worker
   |
   v
Background Task
```

The project contains a task:

```python
process_order_created
```

It receives the order ID and processes the order in the background.

---

# 13. Celery and Order Creation

After an order is created, the project can send a Celery task after the database transaction is successfully committed.

Example:

```python
transaction.on_commit(
    lambda: process_order_created.delay(order.id)
)
```

This is useful because the Celery task should only be sent after the order has successfully been saved in the database.

---

# 14. Swagger API Documentation

The project uses:

```text
drf-spectacular
```

for OpenAPI and Swagger documentation.

Swagger provides a web interface where APIs can be viewed and tested.

Open:

```text
/api/docs/
```

For example:

```text
http://127.0.0.1:8000/api/docs/
```

Swagger allows us to:

- See available APIs
- See HTTP methods
- See request parameters
- See request body
- Execute API requests
- See API responses
- Test APIs without Postman

---

# 15. OpenAPI Schema

The project also provides an OpenAPI schema.

Example:

```text
/api/schema/
```

The schema describes the API structure in a machine-readable format.

Swagger UI uses this schema to display the API documentation.

---

# 16. API Testing Example

### Create Order

Request:

```http
POST /api/orders/
```

Body:

```json
{
  "store_id": 7,
  "items": [
    {
      "product_id": 790,
      "quantity_requested": 1
    }
  ]
}
```

Successful response:

```json
{
  "message": "Order created successfully.",
  "status": "CONFIRMED",
  "order": {
    "id": 13,
    "store": 7,
    "status": "CONFIRMED"
  }
}
```

---

# 17. Rejected Order Example

If the requested quantity is greater than available stock:

```json
{
  "store_id": 7,
  "items": [
    {
      "product_id": 790,
      "quantity_requested": 25
    }
  ]
}
```

and available stock is:

```text
1
```

the API returns:

```json
{
  "message": "Order rejected due to insufficient stock.",
  "status": "REJECTED",
  "insufficient_stock": [
    {
      "product_id": 790,
      "requested": 25,
      "available": 1
    }
  ]
}
```

---

# 18. Complete Project Flow

The complete backend flow can be understood like this:

```text
                 CLIENT
                    |
                    v
              Django REST API
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
    Products     Stores      Orders
                                |
                                v
                           Validation
                                |
                                v
                           Inventory
                                |
                    +-----------+-----------+
                    |                       |
               Stock OK                Stock Low
                    |                       |
                    v                       v
             Deduct Stock               REJECTED
                    |
                    v
              Create Order
                    |
                    v
               Database
                    |
                    v
             Celery Task
                    |
                    v
                  Redis
```

---

# 19. Important Libraries and Why They Are Used

### Django

Used to build the main backend application.

### Django REST Framework

Used to create REST APIs and serializers.

### drf-spectacular

Used to generate OpenAPI schema and Swagger documentation.

### Redis

Used for caching and as a Celery message broker.

### Celery

Used for background processing.

### Docker

Used to run services such as Redis in containers.

### Django ORM

Used to communicate with the database using Python code instead of writing SQL for every operation.

---

# 20. Running the Project

First activate the virtual environment.

Windows:

```powershell
.venv\Scripts\activate
```

Then run Django:

```powershell
python manage.py runserver
```

The server normally runs at:

```text
http://127.0.0.1:8000/
```

---

# 21. Running Celery

Make sure Redis is running.

Then start the Celery worker:

```powershell
celery -A config worker -l info --pool=solo
```

A successful worker will show something similar to:

```text
celery@Machine ready.
```

The registered tasks should also appear in the worker.

---

# 22. Testing the System

A simple testing process is:

### Step 1

Open Swagger:

```text
/api/docs/
```

### Step 2

Test the inventory API:

```text
GET /api/stores/{store_id}/inventory/
```

### Step 3

Check available stock.

### Step 4

Create an order using:

```text
POST /api/orders/
```

### Step 5

Check whether the response is:

```text
CONFIRMED
```

or:

```text
REJECTED
```

### Step 6

Check inventory again.

If the order was confirmed, the quantity should decrease.

### Step 7

Check the orders API:

```text
GET /api/stores/{store_id}/orders/
```

### Step 8

Check the Celery worker terminal to see whether the background task was received and completed.

---

# 23. Error Handling During Development

Some common issues faced while setting up this project were:

### Redis connection error

```text
Error 10061 connecting to 127.0.0.1:6379
```

This means Redis was not running or was not reachable.

Solution:

```text
Start Redis / Docker Redis container
```

---

### Celery unregistered task

```text
Received unregistered task
```

This means the Celery worker did not load the task.

The task module must be available to Celery and the worker should be restarted after changes.

---

### Serializer warning in Swagger

```text
unable to guess serializer
```

For APIView-based views, drf-spectacular may not automatically know the serializer.

This can be fixed by explicitly defining the request and response serializers with:

```python
@extend_schema(...)
```

---

# 24. Why This Project Uses `transaction.on_commit`

Suppose Django creates an order and immediately sends a Celery task.

If the database transaction later fails, the Celery task may still run.

Using:

```python
transaction.on_commit(...)
```

means:

```text
Database transaction
       |
       v
   Successful?
       |
      YES
       |
       v
Send Celery task
```

This makes the process safer.

---

# 25. Simple Explanation for Someone Else

If I had to explain this project to someone in simple words:

> This is a Django backend for managing stores, products, inventory, and orders.
>
> A store has products and stock. When a customer creates an order, the backend checks whether enough stock is available.
>
> If there is enough stock, the backend reduces the inventory and creates a confirmed order.
>
> If there is not enough stock, the order is rejected and the stock is not changed.
>
> Django REST Framework is used to create the APIs.
>
> Swagger is used to document and test the APIs.
>
> Redis is used for caching and as the message broker.
>
> Celery is used to run background tasks without blocking the API request.
>
> Database transactions and row locking are used to keep stock updates safe.

---

# 26. Future Improvements

Possible future improvements include:

- User authentication
- JWT authentication
- Pagination
- Better API error responses
- Order cancellation
- Payment integration
- Advanced product search
- More Redis caching
- Celery scheduled tasks
- Unit tests
- API integration tests
- Docker Compose for the complete application
- Production deployment
- PostgreSQL/MySQL production database
- CI/CD pipeline

---

# 27. Summary

This project demonstrates a practical Django REST backend with:

```text
Django
   +
Django REST Framework
   +
Database
   +
Redis
   +
Celery
   +
Swagger
```

The main business logic is based around:

```text
Products
   ↓
Stores
   ↓
Inventory
   ↓
Orders
   ↓
Stock Validation
   ↓
Confirmed / Rejected Order
   ↓
Background Processing
```

The project is designed to show how a real backend can handle API requests, database relationships, stock management, caching, background processing, and API documentation.
