from decimal import Decimal

from django.test import override_settings

from mytools.models import Bill, Electricity, Seg, Gas
from mytools.tasks import process_bills
from tests.mytools.services.parse_bill.edf_energy_test import (
    EDF_PAGE_2_TEXT,
    EDF_PAGE_3_TEXT,
)
from tests.mytools.services.parse_bill.conftest import (
    mock_edf_pdfplumber,
    media_pdf_setup,
)


def test_process_edf_gas_electric_bill_creates_related_models(
    db, media_pdf_setup, mock_edf_pdfplumber
):
    media_root, pdf_path = media_pdf_setup

    with mock_edf_pdfplumber(page_2_text=EDF_PAGE_2_TEXT, page_3_text=EDF_PAGE_3_TEXT):
        with override_settings(MEDIA_ROOT=str(media_root)):
            process_bills("EDF")

    bill = Bill.objects.get(b_provider="EDF")
    assert bill.b_gross_cost == Decimal("25.92")
    assert bill.b_net_cost == Decimal("-7.71")

    electricity = Electricity.objects.get(e_bill=bill)
    assert electricity.e_kwh_used == Decimal("100.0")
    assert electricity.e_total_cost == Decimal("10.50")

    seg = Seg.objects.get(s_bill=bill)
    assert seg.s_total_cost == Decimal("-33.63")
    assert not pdf_path.exists()

    gas = Gas.objects.get(g_bill=bill)
    assert gas.g_kwh_used == Decimal("1154.6500")
    assert gas.g_total_cost == Decimal("15.42")


def test_process_edf_gas_electric_bill_empty_sections(
    db,
    media_pdf_setup,
    mock_edf_pdfplumber,
):
    media_root, pdf_path = media_pdf_setup

    with mock_edf_pdfplumber(page_2_text="", page_3_text=""):
        with override_settings(MEDIA_ROOT=str(media_root)):
            process_bills("EDF")

    bill = Bill.objects.get(b_provider="EDF")
    assert bill.b_gross_cost is None
    assert bill.b_net_cost is None
    assert bill.b_date is None
    assert Electricity.objects.count() == 0
    assert Seg.objects.count() == 0
    assert Gas.objects.count() == 0
    assert not pdf_path.exists()
