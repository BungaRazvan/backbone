import re
import pdfplumber

from typing import Union, Dict, Optional
from os import PathLike

from common.utils import parse_uk_date_to_object

from .parameters import BaseParser, BillParseParameters, UtilityCategory, BillResult


def match_periods(text: str):
    return re.search(
        r"\(\s*(\d{1,2}\s+[A-Za-z]+)\s+(\d{4})\s*-\s*(\d{1,2}\s+[A-Za-z]+)\s+(\d{4})\s*\)",
        text,
    )


def extract_usage(text: str, word: str):
    pattern = rf"{word}\s+used\*?\s+([\d.]+)\s*kWh"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return float(match.group(1))

    return None


def parse_bill(
    pdf_path: Union[str, PathLike],
) -> Optional[Dict[UtilityCategory, BillResult]]:
    extracted_data: Dict[UtilityCategory, BillResult] = {
        UtilityCategory.ELECTRICITY: BillResult(category=UtilityCategory.ELECTRICITY),
        UtilityCategory.SEG: BillResult(category=UtilityCategory.SEG),
        UtilityCategory.GAS: BillResult(category=UtilityCategory.GAS),
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
        UtilityCategory.ELECTRICITY: (electricity_block, "Electricity"),
        UtilityCategory.SEG: (export_block, "Electricity"),
        UtilityCategory.GAS: (gas_block, "Energy"),
    }

    for category, (block_text, usage_word) in blocks.items():

        if not block_text.strip():
            continue

        period_match = match_periods(block_text)
        result = extracted_data[category]

        if period_match:
            raw_from_date = f"{period_match.group(1)} {period_match.group(2)}"
            raw_to_date = f"{period_match.group(3)} {period_match.group(4)}"
            result.from_date = parse_uk_date_to_object(raw_from_date)
            result.to_date = parse_uk_date_to_object(raw_to_date)

        unit_match = re.search(r"([\d.]+)p/kWh", block_text, re.IGNORECASE)

        if unit_match:
            result.unit_rate = float(unit_match.group(1)) / 100

        standing_total_match = re.search(
            r"Standing charge.*?£([\d.]+)", block_text, re.IGNORECASE
        )

        if standing_total_match:
            result.standing_charge_total = float(standing_total_match.group(1))

        standing_rate_match = re.search(
            r"Standing charge.*?@\s+([\d.]+)p/day", block_text, re.IGNORECASE
        )

        if standing_rate_match:
            result.standing_charge_rate = float(standing_rate_match.group(1)) / 100

        subtotal_match = re.search(r"Subtotal.*?(-?£[\d.]+)", block_text, re.IGNORECASE)

        if subtotal_match:
            result.subtotal_before_vat = float(subtotal_match.group(1).replace("£", ""))

        vat_match = re.search(r"VAT.*?£([\d.]+)", block_text, re.IGNORECASE)

        if vat_match:
            result.vat_amount = float(vat_match.group(1))

        section_total_match = re.search(
            r"Total (?:electricity|gas).*?(-?£[\d.]+)", block_text, re.IGNORECASE
        )

        if section_total_match:
            result.total_cost = float(section_total_match.group(1).replace("£", ""))

        usage_kwh = extract_usage(block_text, usage_word)

        if usage_kwh:
            result.kwh_used = usage_kwh

    final_output = {
        cat: res
        for cat, res in extracted_data.items()
        if res.total_cost is not None
        or res.kwh_used is not None
        or res.from_date is not None
    }

    return final_output


class EdfParser(BaseParser):
    def extract_details(
        self, args: BillParseParameters
    ) -> Dict[UtilityCategory, BillResult]:

        return parse_bill(args.file_path)
