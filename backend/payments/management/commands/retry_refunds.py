from django.core.management.base import BaseCommand

from payments.refunds import retry_refunds


class Command(BaseCommand):
    help = "Send failed or unsent refunds to Razorpay again, and check pending ones. Safe to run any time."

    def handle(self, *args, **options):
        counts = retry_refunds()
        self.stdout.write(
            f"Refunds: {counts['sent']} sent, {counts['still_failing']} still failing, {counts['checked']} checked."
        )
