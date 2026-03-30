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
