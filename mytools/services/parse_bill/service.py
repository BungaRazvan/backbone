from dataclasses import asdict
from typing import Union, Dict

from mytools.models.bill import EnergyProvider

from .edf_energy import EdfParser
from .parameters import BillParseParameters

from rest_framework_dataclasses.serializers import DataclassSerializer

SERVICE_MAP = {EnergyProvider.EDF: EdfParser}


class BillParseService:
    def get_parser(self, provider: str):
        parser = SERVICE_MAP.get(provider)

        if not parser:
            raise Exception(f"Unknow provider: {provider}")

        return parser

    def extract_sections(self, provider: str, args: Union[BillParseParameters, Dict]):

        if isinstance(args, BillParseParameters):
            args = asdict(args)

        serializer = DataclassSerializer(data=args, dataclass=BillParseParameters)
        serializer.is_valid(raise_exception=True)

        return self.get_parser(provider)().extract_sections(serializer.validated_data)

    # TODO less boilerplate better interface
    def extract_date(self, provider: str, args: Union[BillParseParameters, Dict]):

        if isinstance(args, BillParseParameters):
            args = asdict(args)

        serializer = DataclassSerializer(data=args, dataclass=BillParseParameters)
        serializer.is_valid(raise_exception=True)

        return self.get_parser(provider)().extract_date(serializer.validated_data)
