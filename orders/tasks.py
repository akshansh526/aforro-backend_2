from celery import shared_task
from django.db import transaction

from .models import Order


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_order_created(self, order_id):
    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .prefetch_related("items__product")
            .get(id=order_id)
        )

        print(f"Processing order #{order.id}")
        print(f"Current status: {order.status}")

        # Order has already been validated and inventory
        # has already been handled by OrderCreateView.
        if order.status == Order.Status.CONFIRMED:
            print(f"Order #{order.id} confirmed successfully.")

        elif order.status == Order.Status.REJECTED:
            print(f"Order #{order.id} was rejected.")

        return {
            "order_id": order.id,
            "status": order.status,
            "message": f"Order #{order.id} processed successfully",
        }


@shared_task
def test_celery_task():
    print("Celery task executed successfully!")
    return "Task completed"