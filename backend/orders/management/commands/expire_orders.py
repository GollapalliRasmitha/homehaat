from django.conf import settings
from django.core.management.base import BaseCommand

from orders.services import expire_unpaid_orders


class Command(BaseCommand):
    help = "Fail orders unpaid for longer than ORDER_HOLD_MINUTES and put their stock back. Safe to run any time."

    def handle(self, *args, **options):
        count = expire_unpaid_orders()
        self.stdout.write(
            self.style.SUCCESS(f"{count} unpaid order(s) older than {settings.ORDER_HOLD_MINUTES} minutes released.")
        )
