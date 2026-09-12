import pytest
from mytools.models import Etf, EtfEvent, EtfShare


@pytest.fixture
def setup_test_data(db):
    etf_1 = Etf.objects.create(
        ef_name="Test ETF",
        ef_isin="TEST12345678",
        ef_symbol="TEST",
        ef_distribution="monthly",
        ef_pay_lag_days=5,
    )

    etf_2 = Etf.objects.create(
        ef_name="Another ETF",
        ef_isin="ANOTHER12345678",
        ef_symbol="ANOTHER",
        ef_distribution="quarterly",
        ef_pay_lag_days=10,
    )

    EtfEvent.objects.create(
        ee_etf=etf_1,
        ee_ex_date="2025-01-15",
        ee_pay_per_share=0.5,
        ee_payment_date="2025-01-20",
    )

    EtfEvent.objects.create(
        ee_etf=etf_2,
        ee_ex_date="2025-04-15",
        ee_pay_per_share=0.75,
        ee_payment_date="2025-04-20",
    )

    EtfShare.objects.create(
        efs_ef=etf_1,
        efs_purchase_date="2025-01-10",
        efs_amount=100,
        efs_total_price=1000.0,
        efs_funds=EtfShare.Funds.SALARY,
    )

    EtfShare.objects.create(
        efs_ef=etf_2,
        efs_purchase_date="2025-04-10",
        efs_amount=200,
        efs_total_price=2000.0,
        efs_funds=EtfShare.Funds.DIVIDENTS,
    )
