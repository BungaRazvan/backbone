from mytools.services.parse_bill.service import BillParseService


def test_bill_parse_service_is_available_from_service_module():
    assert BillParseService is not None
