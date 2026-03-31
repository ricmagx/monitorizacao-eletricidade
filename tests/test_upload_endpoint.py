"""Testes de integracao para endpoint POST /upload/pdf (UPLD-03, UPLD-04)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from src.db.schema import metadata


# Bytes minimos de um PDF valido (header PDF + EOF)
MINIMAL_PDF_BYTES = b"%PDF-1.0\n1 0 obj<</Type /Catalog>>endobj\nxref\n0 1\n0000000000 65535 f \ntrailer<</Size 1/Root 1 0 R>>\nstartxref\n9\n%%EOF"


@pytest.fixture
def web_client_pdf(tmp_path, sample_config_json):
    """FastAPI TestClient com db_engine in-memory — necessario para /upload/pdf."""
    from src.web.app import app

    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)

    app.state.config_path = sample_config_json
    app.state.project_root = tmp_path
    app.state.db_engine = test_engine

    return TestClient(app)


def test_upload_pdf_returns_200(web_client_pdf):
    """UPLD-03: POST /upload/pdf com PDF sintetico retorna HTTP 200.

    Se pdfplumber nao conseguir extrair texto, o endpoint retorna 200 com
    mensagem de erro (nao 500 — nao deve crashar).
    """
    # Mockar ingerir_pdf para devolver erro de formato (evita dependencia de pdfplumber)
    with patch("src.web.routes.upload.ingerir_pdf", return_value={
        "erro": "Formato de fatura nao reconhecido. Formatos suportados: Meo Energia, Endesa.",
        "formato": None,
        "location_id": None,
        "location_name": None,
        "cpe": None,
        "year_month": None,
        "custo_eur": None,
        "inserido": False,
    }):
        response = web_client_pdf.post(
            "/upload/pdf",
            files={"ficheiro": ("fatura.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
        )
    assert response.status_code == 200


def test_upload_pdf_erro_formato(web_client_pdf):
    """UPLD-03: POST /upload/pdf com PDF sem formato reconhecido retorna 200 com erro no HTML.

    Mockamos ingerir_pdf para simular PDF sem keywords reconhecidas (Meo Energia / Endesa).
    """
    with patch("src.web.routes.upload.ingerir_pdf", return_value={
        "erro": "Formato de fatura nao reconhecido. Formatos suportados: Meo Energia, Endesa.",
        "formato": None,
        "location_id": None,
        "location_name": None,
        "cpe": None,
        "year_month": None,
        "custo_eur": None,
        "inserido": False,
    }):
        response = web_client_pdf.post(
            "/upload/pdf",
            files={"ficheiro": ("fatura.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
        )

    assert response.status_code == 200
    # Deve conter mensagem de erro (sem crash)
    assert "Formato de fatura nao reconhecido" in response.text or "Erro" in response.text


def test_upload_pdf_renders_confirmacao(web_client_pdf):
    """UPLD-04: POST /upload/pdf com mock de sucesso mostra confirmacao com dados extraidos."""
    resultado_mock = {
        "erro": None,
        "formato": "meo_energia",
        "location_id": "casa",
        "location_name": "Casa",
        "cpe": "PT0002000084968079SX",
        "year_month": "2026-01",
        "custo_eur": 45.32,
        "inserido": True,
    }

    with patch("src.web.routes.upload.ingerir_pdf", return_value=resultado_mock), \
         patch("src.web.routes.upload.save_custo_real") as mock_save:
        response = web_client_pdf.post(
            "/upload/pdf",
            files={"ficheiro": ("fatura.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
        )

    assert response.status_code == 200
    assert "Fatura importada com sucesso" in response.text
    assert "45.32" in response.text
    # Confirmar que save_custo_real foi chamado com os parametros correctos
    mock_save.assert_called_once()
    call_args = mock_save.call_args
    assert call_args[0][1] == "2026-01"  # year_month
    assert call_args[0][2] == 45.32      # custo_eur
