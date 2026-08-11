import datetime
from typing import Dict, Optional

from .parameters import UtilityCategory, BillParseParameters, BillSection

from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def extract_sections(
        self, args: BillParseParameters
    ) -> Optional[Dict[UtilityCategory, BillSection]]:
        raise NotImplementedError

    @abstractmethod
    def extract_date(self, args: BillParseParameters) -> Optional[datetime.date]:
        raise NotImplementedError
