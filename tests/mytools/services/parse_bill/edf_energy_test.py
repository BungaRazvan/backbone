import os
from django.conf import settings

from mytools.services.parse_bill.edf_energy import parse_bill


def test_a():
    a = parse_bill(
        os.path.join(settings.MEDIA_ROOT, "edf_bills", "A-9E9122D9-106875387-1.pdf")
    )
    print(a)
    assert False
