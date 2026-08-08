import enum


import dataclasses
import datetime


from typing import Union, Optional

from mytools.models import Seg, Electricity, Gas


class UtilityCategory(str, enum.Enum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    SEG = "seg"


@dataclasses.dataclass
class BillParseParameters:
    file_path: str


@dataclasses.dataclass
class BillSection:
    from_date: Optional[datetime.date] = None
    to_date: Optional[datetime.date] = None

    kwh_used: Optional[float] = None
    standing_charge_total: Optional[float] = None
    standing_charge_rate: Optional[float] = None
    unit_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    subtotal_before_vat: Optional[float] = None
    total_cost: Optional[float] = None

    category: Optional[UtilityCategory] = None

    def model_mappings(self):
        mappings = {
            UtilityCategory.SEG: (Seg, "s_"),
            UtilityCategory.ELECTRICITY: (Electricity, "e_"),
            UtilityCategory.GAS: (Gas, "g_"),
        }

        return mappings.get(self.category.value)

    def to_model(self) -> Optional[Union[Electricity, Gas, Seg]]:
        model_class, prefix = self.model_mappings()

        if prefix is None:
            return None

        if model_class is None:
            return None

        instance = model_class()

        for field in dataclasses.fields(self):
            if field.name == "category":
                continue

            setattr(instance, prefix + field.name, getattr(self, field.name))

        return instance
