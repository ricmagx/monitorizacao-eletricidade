"""Testes para routes da dashboard web."""
import pytest
from fastapi.testclient import TestClient


def test_homepage_ok(web_client):
    """GET / retorna 200 com <select e referencia a htmx.min.js."""
    response = web_client.get("/")
    assert response.status_code == 200
    assert "<select" in response.text
    assert "htmx.min.js" in response.text


def test_homepage_contains_local_selector(web_client):
    """GET / tem o selector de local com opcoes."""
    response = web_client.get("/")
    assert response.status_code == 200
    # Deve conter pelo menos um <option com o id do local
    assert "casa" in response.text
    assert "apartamento" in response.text


def test_local_dashboard_swap(web_client):
    """GET /local/casa/dashboard retorna 200 com id='consumo-chart'."""
    response = web_client.get("/local/casa/dashboard")
    assert response.status_code == 200
    assert 'id="consumo-chart"' in response.text


def test_local_dashboard_apartamento(web_client):
    """GET /local/apartamento/dashboard retorna 200."""
    response = web_client.get("/local/apartamento/dashboard")
    assert response.status_code == 200


def test_local_dashboard_invalid(web_client):
    """GET /local/inexistente/dashboard retorna 404."""
    response = web_client.get("/local/inexistente/dashboard")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Testes para locais SQLite-only (Phase 9)
# ---------------------------------------------------------------------------


def test_sqlite_only_local_shows_consumo(web_client_sqlite):
    """GET /local/teste-sqlite/dashboard retorna 200 com canvas consumo-chart."""
    response = web_client_sqlite.get("/local/teste-sqlite/dashboard")
    assert response.status_code == 200
    assert 'id="consumo-chart"' in response.text


def test_sqlite_only_local_shows_ranking(web_client_sqlite):
    """GET /local/teste-sqlite/dashboard retorna ranking com fornecedores."""
    response = web_client_sqlite.get("/local/teste-sqlite/dashboard")
    assert response.status_code == 200
    # Deve conter pelo menos um fornecedor do seed data
    assert "Luzboa" in response.text or "EDP" in response.text or "Meo Energia" in response.text


def test_sqlite_only_local_shows_custo_chart(web_client_sqlite):
    """GET /local/teste-sqlite/dashboard contem canvas custo-chart."""
    response = web_client_sqlite.get("/local/teste-sqlite/dashboard")
    assert response.status_code == 200
    assert 'id="custo-chart"' in response.text


def test_pipeline_local_still_works(web_client_sqlite):
    """GET /local/casa/dashboard continua a retornar 200 (retrocompatibilidade)."""
    response = web_client_sqlite.get("/local/casa/dashboard")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Testes UI-SPEC: alinhamento visual (Phase 9 Plan 02)
# ---------------------------------------------------------------------------


def test_custo_chart_uses_bar_type(web_client):
    """GET /local/casa/dashboard contem dois datasets type bar e nao type line."""
    response = web_client.get("/local/casa/dashboard")
    assert response.status_code == 200
    text = response.text
    # Dois datasets bar (conta pelo menos 2 ocorrencias)
    assert text.count("type: 'bar'") >= 2
    # Nao deve conter type line
    assert "type: 'line'" not in text


def test_ranking_has_poupanca_column(web_client_sqlite):
    """GET /local/teste-sqlite/dashboard contem coluna Poupanca Potencial."""
    response = web_client_sqlite.get("/local/teste-sqlite/dashboard")
    assert response.status_code == 200
    assert "Poupanca Potencial" in response.text


def test_dashboard_has_upload_pdf(web_client):
    """GET / contem referencia a upload PDF."""
    response = web_client.get("/")
    assert response.status_code == 200
    assert "Importar Fatura PDF" in response.text or "upload_pdf" in response.text


def test_dashboard_no_custo_form(web_client):
    """GET / nao contem o formulario manual de custo (removido em Phase 9 Plan 02)."""
    response = web_client.get("/")
    assert response.status_code == 200
    assert "custo_form" not in response.text
