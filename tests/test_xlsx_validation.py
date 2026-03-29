"""Testes de bounds check para o parser XLSX (RES-02)."""
import pytest
from pathlib import Path
from openpyxl import Workbook


def _create_test_xlsx(tmp_path: Path, rows: list[list], filename: str = "test.xlsx") -> Path:
    """Cria um XLSX de teste com formato E-REDES simplificado.

    O formato minimo que convert_xlsx_to_monthly_csv aceita:
    - Sheet 'Consumos'
    - Header row: Data | Hora | (col2) | Potencia(col3) | ... | ... | ... | Registada(col7)
    - Data rows: YYYY/MM/DD | HH:MM | ... | ... | ... | ... | ... | power_kw
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Consumos"
    # Header row que detect_data_start_row() vai encontrar
    ws.append(["Data", "Hora", "Ativa", "Potencia", "", "", "", "Registada"])
    for row in rows:
        ws.append(row)
    xlsx_path = tmp_path / filename
    wb.save(xlsx_path)
    return xlsx_path


def _make_rows_for_month(year_month: str, total_kwh: float, n_intervals: int = 4) -> list[list]:
    """Gera n_intervals linhas para um mes, distribuindo total_kwh igualmente.

    Cada intervalo = 15 min (0.25h), power_kw = kwh / 0.25.
    """
    kwh_per_interval = total_kwh / n_intervals
    power_kw = kwh_per_interval / 0.25  # power_kw * 0.25 = kwh_per_interval
    year, month = year_month.split("-")
    rows = []
    for i in range(n_intervals):
        hour = str(i).zfill(2)
        rows.append([f"{year}/{month}/15", f"{hour}:00", None, None, None, None, None, power_kw])
    return rows


def test_bounds_check_rejects_zero_kwh(tmp_path):
    """RES-02: XLSX com mes de consumo 0 kWh deve lancar ValueError antes de escrever CSV."""
    from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
    rows = _make_rows_for_month("2025-01", 0.0)
    xlsx = _create_test_xlsx(tmp_path, rows)
    output_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="fora dos limites"):
        convert_xlsx_to_monthly_csv(xlsx, output_csv)
    assert not output_csv.exists(), "CSV nao deve ser criado quando bounds check falha"


def test_bounds_check_rejects_above_max(tmp_path):
    """RES-02: XLSX com mes de consumo > 5000 kWh deve lancar ValueError."""
    from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
    rows = _make_rows_for_month("2025-01", 6000.0)
    xlsx = _create_test_xlsx(tmp_path, rows)
    output_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="fora dos limites"):
        convert_xlsx_to_monthly_csv(xlsx, output_csv)
    assert not output_csv.exists(), "CSV nao deve ser criado quando bounds check falha"


def test_bounds_check_rejects_below_min(tmp_path):
    """RES-02: XLSX com mes de consumo < 30 kWh deve lancar ValueError."""
    from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
    rows = _make_rows_for_month("2025-01", 10.0)
    xlsx = _create_test_xlsx(tmp_path, rows)
    output_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="fora dos limites"):
        convert_xlsx_to_monthly_csv(xlsx, output_csv)
    assert not output_csv.exists()


def test_bounds_check_accepts_normal_values(tmp_path):
    """RES-02: XLSX com valores normais e processado sem erros."""
    from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
    rows = _make_rows_for_month("2025-01", 800.0) + _make_rows_for_month("2025-02", 1200.0)
    xlsx = _create_test_xlsx(tmp_path, rows)
    output_csv = tmp_path / "out.csv"
    result = convert_xlsx_to_monthly_csv(xlsx, output_csv)
    assert output_csv.exists(), "CSV deve ser criado para valores normais"
    content = output_csv.read_text(encoding="utf-8")
    assert "2025-01" in content
    assert "2025-02" in content


def test_bounds_check_message_includes_year_month(tmp_path):
    """RES-02: Mensagem de erro inclui o year_month do mes problematico."""
    from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
    rows = _make_rows_for_month("2025-06", 0.0)
    xlsx = _create_test_xlsx(tmp_path, rows)
    output_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="2025-06"):
        convert_xlsx_to_monthly_csv(xlsx, output_csv)
