import datetime
import re
import pdfplumber
from collections import defaultdict


from typing import Union, Dict, Optional, List
from os import PathLike

from common.utils import parse_uk_date_to_object

from .parameters import BillParseParameters, UtilityCategory, BillSection
from .base import BaseParser


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
) -> Optional[Dict[UtilityCategory, List[BillSection]]]:

    extracted_data = defaultdict(list)

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages[1:]:
            extracted = page.extract_text()
            if extracted:
                full_text += extracted + "\n"

    if not full_text.strip():
        return None

    # 1. Find ALL section anchors in order of appearance
    anchors: List[tuple[int, UtilityCategory]] = []

    # Find Electricity anchors
    for m in re.finditer(r"Electricity tariff name", full_text, re.IGNORECASE):
        start_pos = m.start()

        # Peek at the next 300 characters to determine if this tariff is SEG or Electricity
        snippet = full_text[start_pos : start_pos + 300]

        if re.search(r"export|seg|generation|fit", snippet, re.IGNORECASE):
            anchors.append((start_pos, UtilityCategory.SEG))
        else:
            anchors.append((start_pos, UtilityCategory.ELECTRICITY))

    # Find Gas anchors
    for m in re.finditer(
        r"Gas tariff name",
        full_text,
        re.IGNORECASE,
    ):
        anchors.append((m.start(), UtilityCategory.GAS))

    if not anchors:
        return None

    # 2. Sort anchors chronologically by where they appear in full_text
    anchors.sort(key=lambda x: x[0])

    # 3. Process EACH block individually
    for i, (start_idx, category) in enumerate(anchors):
        end_idx = anchors[i + 1][0] if i + 1 < len(anchors) else len(full_text)
        block_text = full_text[start_idx:end_idx]

        if not block_text.strip():
            continue

        # Choose appropriate word to find usage in text
        usage_word = "Energy" if category == UtilityCategory.GAS else "Electricity"

        # Instantiate a individual section for THIS specific block
        result = BillSection(category=category)

        period_match = match_periods(block_text)
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
            r"Standing charge.*?@\s+([\d.]+)p/day",
            block_text,
            re.IGNORECASE,
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
            r"Total (?:electricity|gas|export|SEG).*?(-?£[\d.]+)",
            block_text,
            re.IGNORECASE,
        )
        if section_total_match:
            total_cost = float(section_total_match.group(1).replace("£", ""))

            # if total_cost < 0 and category == UtilityCategory.ELECTRICITY:
            #     category = UtilityCategory.SEG
            #     result.category = UtilityCategory.SEG

            result.total_cost = total_cost

        usage_kwh = extract_usage(block_text, usage_word)
        if usage_kwh:
            result.kwh_used = usage_kwh

        # print(result)
        # Append this individual parsed section to its category list
        extracted_data[category].append(result)

    # 4. Filter out incomplete section objects
    final_output = {}

    for cat, sections in extracted_data.items():
        valid_sections = [
            res
            for res in sections
            if res.total_cost is not None
            and res.kwh_used is not None
            and res.to_date is not None
            and res.from_date is not None
        ]

        if valid_sections:
            final_output[cat] = valid_sections

    return final_output


class EdfParser(BaseParser):
    def extract_sections(
        self, args: BillParseParameters
    ) -> Dict[UtilityCategory, List[BillSection]]:

        return parse_bill(args.file_path)

    def extract_date(self, args: BillParseParameters) -> Optional[datetime.date]:
        with pdfplumber.open(args.file_path) as pdf:
            text = pdf.pages[0].extract_text()

            if not text.strip():
                return None

        reference_match = re.search(
            r"Bill reference:.*?\(\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})\)",
            text,
            re.IGNORECASE,
        )

        if reference_match:
            return parse_uk_date_to_object(reference_match.group(1))

        return None
