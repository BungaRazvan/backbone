import pytest
import datetime

from mytools.services.parse_bill.edf_energy import EdfParser
from mytools.services.parse_bill.parameters import BillParseParameters, UtilityCategory

EDF_PAGE_2_TEXT = """
    Electricity tariff name Simply Fixed Jul26v14
    Supply address: 
    Rota Disconnections Alpha Identifier:
    Payment method 
    Simply Fixed Jul26v14 (26 May 2026 - 25 June 2026)
    Unit rate 50.756p/kWh
    Electricity charges for meter  Standing charge 47.133p/day
    (£1172.04/year)
    26 May 2026 1 Smart meter reading
    Price guaranteed until 1 Aug. 2026
    26 Jun 2026 1 Smart meter reading
    Early exit fee £50.00
    Electricity used 100.0 kWh @ £2
    50.756p/kWh Estimated annual usage 1 kWh
    Standing charge 31 days @ 47.133p/day £14.61 Scan this code when comparing tariffs
    Subtotal of charges before VAT £10.50
    VAT @ 5% £0.90
    Total electricity charges for this period £10.50
    For comparison, we estimated you used 1 kWh in the
    same period the previous year.
    About your tariff
    Electricity Supply 
    S Prices do not include VAT unless otherwise noted
    number
    1
    Electricity tariff name Export 12m
    Supply address: 
    Rota Disconnections Alpha Identifier:
    Payment method 
    Export 12m (26 May 2026 - 25 June 2026)
    Unit rate 15.000p/kWh
    Electricity charges for meter  Standing charge 0.000p/day
    (£0.00/year)
    26 May 2026 1 Smart meter reading
    Price guaranteed until 24 March 2027
    26 Jun 2026 1 Smart meter reading
    Early exit fee None
    Electricity used 24.2200 kWh @ -£33.63
    15.000p/kWh Estimated annual usage 1 kWh
    Standing charge 31 days @ 0.000p/day £0.00 Scan this code when comparing tariffs
    Subtotal of charges before VAT -£33.63
    VAT @ 0% £0.00
    Total electricity charges for this period -£33.63
    We are unable to compare the consumption for this period in
    the previous year            
"""

EDF_PAGE_3_TEXT = """
    About your tariff
    Gas Meter point reference 
    Prices do not include VAT unless otherwise noted
    Supply address: 
    Gas tariff name Simply Fixed Jul26v14
    Simply Fixed Jul26v14 (26 May 2026 - 25 June 2026) Product type Fixed
    Payment method 
    Gas charges for meter 
    Unit rate 5.573p/kWh
    26 May 2026 1 Smart meter reading
    Standing charge 21.935p/day
    26 Jun 2026 1 Smart meter reading
    (£280.06/year)
    3
    Consumption 13.7130 Units (m )
    Price guaranteed until 1 August 2026
    Energy used* 1154.6500 kWh @ £8.62
    Early exit fee £50.00
    5.573p/kWh
    Estimated annual usage* 
    Standing charge 31 days @ 21.935p/day £6.80
    Energy use calculation
    Subtotal of charges before VAT £15.42
    * Your energy usage is calculated from your gas consumption using a
    standard industry formula:
    VAT @ 5% £0.77 Unit consumed (cubic metres)
    × Volume correction (for temperature & pressure)
    Total gas charges for this period £15.42 × Calorific value (energy in each m3 of gas)
    ÷ 3.6 (convert from joules)
    For comparison, we estimated you used 
    same period the previous year. †Average calorific value shown to one decimal place
    Scan this code when comparing tariffs
"""


def test_parse_gas_electric_bill_sections(media_pdf_setup, mock_edf_pdfplumber):
    _, pdf_path = media_pdf_setup

    with mock_edf_pdfplumber(page_2_text=EDF_PAGE_2_TEXT, page_3_text=EDF_PAGE_3_TEXT):
        sections = EdfParser().extract_sections(BillParseParameters(file_path=pdf_path))

    assert len(sections) == 3

    elec = sections[UtilityCategory.ELECTRICITY]
    gas = sections[UtilityCategory.GAS]
    seg = sections[UtilityCategory.SEG]

    assert len(elec) == 1
    assert len(gas) == 1
    assert len(seg) == 1

    assert elec[0].category == "electricity"
    assert elec[0].kwh_used == pytest.approx(100.0, 0.2)
    assert elec[0].total_cost == pytest.approx(10.50, 0.2)
    assert seg[0].category == "seg"
    assert seg[0].kwh_used == pytest.approx(24.22, 0.2)
    assert seg[0].total_cost == pytest.approx(-33.63, 0.2)
    assert gas[0].category == "gas"
    assert gas[0].kwh_used == pytest.approx(1154.6500, 0.2)
    assert gas[0].total_cost == pytest.approx(15.42, 0.2)


def test_extract_date(media_pdf_setup, mock_edf_pdfplumber):
    _, pdf_path = media_pdf_setup
    page_1_text = """
        Bill reference: 000000 (1 June 2026)
        Account number:
    """

    with mock_edf_pdfplumber(page_1_text=page_1_text):
        date = EdfParser().extract_date(BillParseParameters(file_path=pdf_path))

    assert date == datetime.date(2026, 6, 1)
