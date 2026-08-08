import pytest

from unittest.mock import MagicMock, patch


@pytest.fixture
def media_pdf_setup(tmp_path):
    """Fixture to set up temporary media directory structure and a dummy PDF file."""

    media_root = tmp_path / "media"
    bills_dir = media_root / "edf_bills"
    bills_dir.mkdir(parents=True)
    pdf_path = bills_dir / "invoice.pdf"
    pdf_path.write_bytes(b"dummy-pdf")

    return media_root, pdf_path


@pytest.fixture
def mock_edf_pdfplumber():
    """Fixture to mock pdfplumber.open for EDF bills returning predefined text."""

    def _setup_mock(page_1_text="", page_2_text="", page_3_text=""):
        mock_pdf = MagicMock()
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None

        mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()]
        mock_pdf.pages[0].extract_text.return_value = page_1_text
        mock_pdf.pages[1].extract_text.return_value = page_2_text
        mock_pdf.pages[2].extract_text.return_value = page_3_text

        return patch(
            "mytools.services.parse_bill.edf_energy.pdfplumber.open",
            return_value=mock_pdf,
        )

    return _setup_mock
