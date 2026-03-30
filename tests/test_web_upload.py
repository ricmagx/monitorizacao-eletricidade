"""Tests para endpoint POST /upload/xlsx (UPLD-01, COMP-01)."""
import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementar em Plan 02")
def test_upload_xlsx_ok(web_client):
    """UPLD-01: Upload de ficheiro XLSX via POST /upload/xlsx retorna HTTP 200."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar em Plan 02")
def test_upload_xlsx_cpe_nao_detectado(web_client):
    """UPLD-05 fallback: Upload com ficheiro sem CPE no nome retorna erro."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar em Plan 02")
def test_background_task_registada(web_client):
    """COMP-01: Apos upload, BackgroundTask e registada (nao bloqueia response)."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar em Plan 02")
def test_upload_sem_playwright_retorna_200(web_client):
    """COMP-01 graceful degradation: Quando playwright nao esta disponivel (ImportError),
    upload retorna HTTP 200 sem erro — a background task loga aviso e retorna sem falhar."""
    pass
