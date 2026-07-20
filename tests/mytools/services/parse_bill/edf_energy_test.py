import os

from django.conf import settings

from mytools.services.parse_bill import EdfParser, BillParseParameters
from mytools.services.parse_bill.parameters import (
    UtilityCategory,
)


def test():
    data = EdfParser().extract_sections(
        BillParseParameters(os.path.join(settings.MEDIA_ROOT, "edf_bills", "a.pdf"))
    )

    assert False
