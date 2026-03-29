"""Tests for per-location reminder behavior (MULTI-05).

Verifica que reminder_job.py envia uma notificacao por local e escreve
o ficheiro de estado na directoria correcta por local.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import call

import pytest


def test_reminder_sends_notification_per_location(tmp_path, multi_location_config, monkeypatch):
    """notify_mac chamada uma vez por local com o nome do local no titulo."""
    from src.backend import reminder_job

    calls: list = []

    def mock_notify_mac(title: str, message: str) -> None:
        calls.append((title, message))

    def mock_open_browser(browser_app: str, url: str) -> None:
        pass

    monkeypatch.setattr(reminder_job, "notify_mac", mock_notify_mac)
    monkeypatch.setattr(reminder_job, "open_browser", mock_open_browser)

    reminder_job.run_reminder(multi_location_config)

    assert len(calls) == 2
    titles = [c[0] for c in calls]
    assert any("Casa" in t for t in titles), f"Titulo com 'Casa' nao encontrado em: {titles}"
    assert any("Apartamento" in t for t in titles), f"Titulo com 'Apartamento' nao encontrado em: {titles}"


def test_reminder_writes_status_per_location(tmp_path, multi_location_config, monkeypatch):
    """Status files escritos em state/casa/ e state/apartamento/."""
    from src.backend import reminder_job

    monkeypatch.setattr(reminder_job, "notify_mac", lambda *a: None)
    monkeypatch.setattr(reminder_job, "open_browser", lambda *a: None)

    reminder_job.run_reminder(multi_location_config)

    project_root = multi_location_config.parent.parent

    casa_status = project_root / "state" / "casa" / "monthly_status.json"
    apt_status = project_root / "state" / "apartamento" / "monthly_status.json"

    assert casa_status.exists(), f"Status file para casa nao encontrado: {casa_status}"
    assert apt_status.exists(), f"Status file para apartamento nao encontrado: {apt_status}"

    casa_data = json.loads(casa_status.read_text(encoding="utf-8"))
    apt_data = json.loads(apt_status.read_text(encoding="utf-8"))

    assert casa_data["location"] == "casa"
    assert apt_data["location"] == "apartamento"
    assert casa_data["status"] == "waiting_for_download"
    assert apt_data["status"] == "waiting_for_download"


def test_reminder_opens_browser_per_location(tmp_path, multi_location_config, monkeypatch):
    """open_browser chamado uma vez por local."""
    from src.backend import reminder_job

    browser_calls: list = []

    def mock_open_browser(browser_app: str, url: str) -> None:
        browser_calls.append((browser_app, url))

    monkeypatch.setattr(reminder_job, "notify_mac", lambda *a: None)
    monkeypatch.setattr(reminder_job, "open_browser", mock_open_browser)

    reminder_job.run_reminder(multi_location_config)

    assert len(browser_calls) == 2, f"Esperados 2 calls a open_browser, obtidos {len(browser_calls)}"


def test_reminder_notification_message_contains_location_name(tmp_path, multi_location_config, monkeypatch):
    """Corpo da mensagem contem o nome do local entre parenteses retos."""
    from src.backend import reminder_job

    notify_calls: list = []

    def mock_notify_mac(title: str, message: str) -> None:
        notify_calls.append((title, message))

    monkeypatch.setattr(reminder_job, "notify_mac", mock_notify_mac)
    monkeypatch.setattr(reminder_job, "open_browser", lambda *a: None)

    reminder_job.run_reminder(multi_location_config)

    messages = [c[1] for c in notify_calls]
    assert any("[Casa]" in m for m in messages), f"'[Casa]' nao encontrado nas mensagens: {messages}"
    assert any("[Apartamento]" in m for m in messages), f"'[Apartamento]' nao encontrado nas mensagens: {messages}"


def test_reminder_returns_list_of_results(tmp_path, multi_location_config, monkeypatch):
    """run_reminder devolve uma lista com um resultado por local."""
    from src.backend import reminder_job

    monkeypatch.setattr(reminder_job, "notify_mac", lambda *a: None)
    monkeypatch.setattr(reminder_job, "open_browser", lambda *a: None)

    results = reminder_job.run_reminder(multi_location_config)

    assert isinstance(results, list), f"Esperado list, obtido {type(results)}"
    assert len(results) == 2
    location_ids = [r["location"] for r in results]
    assert "casa" in location_ids
    assert "apartamento" in location_ids
