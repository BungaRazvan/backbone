import glob
import os

from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.forms.models import model_to_dict

from mytools.models import Bill, Seg
from mytools.services.parse_bill import BillParseService, BillParseParameters


@shared_task
def process_bills(provider: str):
    pattern = "*.pdf"
    files = glob.glob(
        os.path.join(settings.MEDIA_ROOT, provider.lower() + "_bills", pattern)
    )
    service = BillParseService()

    for file in files:
        args = BillParseParameters(file_path=file)
        sections = service.extract_sections(provider.upper(), args)
        bill = Bill.objects.create(b_provider=provider.upper())

        if not sections.values():
            continue

        gross_cost = Decimal("0.00")
        total_cost = Decimal("0.00")
        items = [result for sections in sections.values() for result in sections]

        for result in items:
            model = result.to_model()

            if model is None:
                continue

            model_class, prefix = result.model_mappings()
            bill_attr = f"{prefix}bill"

            instance_as_dict = model_to_dict(model)
            instance_as_dict.pop(bill_attr, None)
            model_class.objects.update_or_create(
                **{bill_attr: bill}, defaults=instance_as_dict
            )

            total_cost += Decimal(result.total_cost)

            if not isinstance(model, Seg):
                gross_cost += Decimal(result.total_cost)

        bill.b_gross_cost = gross_cost
        bill.b_total_cost = total_cost
        bill.b_date = service.extract_date(provider.upper(), args)
        bill.save()
        os.remove(file)
