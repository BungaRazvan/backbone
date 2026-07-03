import re
import pdfplumber

from datetime import datetime


def match_periods(text: str):
    return re.search(
        r"\(\s*(\d{1,2}\s+[A-Za-z]+)\s+(\d{4})\s*-\s*(\d{1,2}\s+[A-Za-z]+)\s+(\d{4})\s*\)",
        text,
    )


def parse_date_to_object(date_str):
    """Converts varying UK date text string formats into a Python datetime object."""
    if not date_str:
        return None

    clean_str = date_str.strip().replace(".", "")

    try:
        return datetime.strptime(clean_str, "%d %B %Y").date()
    except ValueError:
        pass

    try:
        return datetime.strptime(clean_str, "%d %b %Y").date()
    except ValueError:
        return None


def extract_usage(text: str, word: str):
    pattern = rf"{word}\s+used\*?\s+([\d.]+)\s*kWh"

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return None


def parse_bill(pdf_path):
    extracted_data = {
        "electricity": {
            "from_date": None,
            "to_date": None,
            "unit_rate_p_kwh": None,
            "standing_charge_total": None,
            "subtotal_before_vat": None,
            "vat_amount": None,
            "section_total": None,
        },
        "export_seg": {
            "from_date": None,
            "to_date": None,
            "unit_rate_p_kwh": None,
            "standing_charge_total": None,
            "subtotal_before_vat": None,
            "vat_amount": None,
            "section_total": None,
        },
        "gas": {
            "from_date": None,
            "to_date": None,
            "unit_rate_p_kwh": None,
            "standing_charge_total": None,
            "subtotal_before_vat": None,
            "vat_amount": None,
            "section_total": None,
        },
    }

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""

        for page in pdf.pages[1:]:
            full_text += page.extract_text()

    if not full_text:
        return None

    elec_anchors = [
        m.start() for m in re.finditer(r"About your tariff", full_text, re.IGNORECASE)
    ]

    gas_match = re.search(r"Gas Meter point|Gas charges", full_text, re.IGNORECASE)
    gas_start = gas_match.start() if gas_match else len(full_text)

    electricity_block = ""
    export_block = ""
    gas_block = full_text[gas_start:] if gas_match else ""

    if len(elec_anchors) >= 2:
        electricity_block = full_text[elec_anchors[0] : elec_anchors[1]]
        export_block = full_text[elec_anchors[1] : gas_start]
    elif len(elec_anchors) == 1:
        electricity_block = full_text[elec_anchors[0] : gas_start]

    blocks = {
        "electricity": (electricity_block, "Electricity"),
        "export_seg": (export_block, "Electricity"),
        "gas": (gas_block, "Energy"),
    }

    for category, _items in blocks.items():
        block_text, usage_word = _items

        if not block_text.strip():
            continue

        period_match = match_periods(block_text)

        if period_match:
            raw_from_date = f"{period_match.group(1)} {period_match.group(2)}"
            raw_to_date = f"{period_match.group(3)} {period_match.group(4)}"
            extracted_data[category]["from_date"] = parse_date_to_object(raw_from_date)
            extracted_data[category]["to_date"] = parse_date_to_object(raw_to_date)

        unit_match = re.search(r"([\d.]+)p/kWh", block_text, re.IGNORECASE)

        if unit_match:
            extracted_data[category]["unit_rate_p_kwh"] = (
                float(unit_match.group(1)) / 100
            )

        standing_total_match = re.search(
            r"Standing charge.*?£([\d.]+)", block_text, re.IGNORECASE
        )

        if standing_total_match:
            extracted_data[category]["standing_charge_total"] = float(
                standing_total_match.group(1)
            )

        standing_rate_match = re.search(
            r"Standing charge.*?@\s+([\d.]+)p/day", block_text, re.IGNORECASE
        )

        if standing_rate_match:
            extracted_data[category]["standing_charge_rate"] = (
                float(standing_total_match.group(1)) / 100
            )

        subtotal_match = re.search(r"Subtotal.*?(-?£[\d.]+)", block_text, re.IGNORECASE)
        if subtotal_match:
            extracted_data[category]["subtotal_before_vat"] = float(
                subtotal_match.group(1).replace("£", "")
            )

        vat_match = re.search(r"VAT.*?£([\d.]+)", block_text, re.IGNORECASE)
        if vat_match:
            extracted_data[category]["vat_amount"] = float(vat_match.group(1))

        section_total_match = re.search(
            r"Total (?:electricity|gas).*?(-?£[\d.]+)", block_text, re.IGNORECASE
        )
        if section_total_match:
            extracted_data[category]["section_total"] = float(
                section_total_match.group(1).replace("£", "")
            )

        usage_kwh = extract_usage(block_text, usage_word)

        if usage_kwh:
            extracted_data[category]["usage_kwh"] = usage_kwh

    net_total = sum(
        extracted_data[cat]["section_total"]
        for cat in ["electricity", "gas"]
        if extracted_data[cat]["section_total"] is not None
    )
    extracted_data["net_total_amount_due"] = round(net_total, 2)

    return extracted_data
