import re
import pdfplumber


def parse_edf_bill(pdf_path):
    extracted_data = {
        "invoice_number": None,
        "billing_period": None,
        "total_amount_due": None,
        "electricity_usage_kwh": [],
        "standing_charge_total": None,
    }

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    print(full_text)
    # print(extracted_data)
    return extracted_data
