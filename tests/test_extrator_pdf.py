"""Tests unitarios para servico de extraccao de faturas PDF (UPLD-03, UPLD-04).

Testa os parsers Meo Energia e Endesa, filtragem de gas, CPE normalizado,
escrita em custos_reais SQLite e idempotencia. Todos os testes usam texto
sintetico que simula o output do pdfplumber.extract_text().
"""
import pytest
from sqlalchemy import select

# ---------------------------------------------------------------------------
# Texto sintetico para fixtures
# ---------------------------------------------------------------------------

TEXTO_MEO_ENERGIA = """
Meo Energia
Fatura de Eletricidade
CPE: PT0002000084968079SX
Periodo de faturacao: 01-01-2026 a 31-01-2026
Consumo em vazio: 200.5 kWh
Consumo fora de vazio: 350.2 kWh
Total a pagar: 45,32 EUR
"""

TEXTO_ENDESA = """
Endesa Energia
Fatura Eletricidade + Gas
CPE: PT0002000084968079SX
Eletricidade
Periodo de Consumo: 01/02/2026 a 28/02/2026
Potencia contratada: 10.35 kVA
Total Eletricidade: 38,50 EUR
Gas Natural
Consumo: 150 m3
Total Gas: 22,10 EUR
Total Fatura: 60,60 EUR
"""

TEXTO_ENDESA_SO_ELETRICIDADE = """
Endesa Energia
CPE: PT0002000084968079SX
Eletricidade
Periodo de Consumo: 01/03/2026 a 31/03/2026
Total Eletricidade: 42,75 EUR
"""

TEXTO_DESCONHECIDO = """
Documento Qualquer
Sem formato reconhecido
Valor: 100.00 EUR
"""

# Formato real MEO Energia: "MEO Energia" (caps), "€ NNN,NN" (euro antes do numero)
TEXTO_MEO_ENERGIA_REAL = """
.A.S ,aigrenE ed oãçazilaicremoC - aigrenE OEM
Pág. 1 de 3
Fatura: FA ME26/615 053 de 24/03/2026
Período de faturação: 07/02/2026 a 20/03/2026
CPE (Código Ponto de Entrega): PT0002000084968079SX
Tarifa: MEO + MEO Energia FIXA MB PAPEL M4 09.25
Total a pagar: € 343,92
meoenergia.pt
"""

# Formato real Endesa: "A LUZ NNN,NN €", periodo com nomes de mes PT
TEXTO_ENDESA_REAL = """
K Luz e Gás Nº Documento: 26010310165507399
TOTAL A DEBITAR 41,46 €
A LUZ 16,25 €
B GÁS 28,54 €
A CPE (Código Ponto Entrega) PT 0002 0000 3982 2082 NT
Endesa poupa todos os meses!
Período de Faturação: 23 dez 2025 a 22 jan 2026
"""

TEXTO_CPE_COM_ESPACO = """
Endesa Energia
CPE: PT000200003982208 2NT
Eletricidade
Periodo de Consumo: 01/01/2026 a 31/01/2026
Total Eletricidade: 29,90 EUR
"""


# ---------------------------------------------------------------------------
# Testes de extraccao de texto (parsers)
# ---------------------------------------------------------------------------

def test_extrair_meo_energia():
    """Meo Energia: extrai total_eur, year_month e CPE do texto sintetico."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_MEO_ENERGIA)

    assert resultado["erro"] is None
    assert resultado["formato"] == "meo_energia"
    assert resultado["cpe"] == "PT0002000084968079SX"
    assert resultado["year_month"] == "2026-01"
    assert resultado["custo_eur"] == pytest.approx(45.32)


def test_extrair_endesa():
    """Endesa: extrai total eletricidade, year_month e CPE do texto sintetico."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_ENDESA_SO_ELETRICIDADE)

    assert resultado["erro"] is None
    assert resultado["formato"] == "endesa"
    assert resultado["cpe"] == "PT0002000084968079SX"
    assert resultado["year_month"] == "2026-03"
    assert resultado["custo_eur"] == pytest.approx(42.75)


def test_endesa_ignora_gas():
    """Endesa com eletricidade + gas: custo_eur e apenas o total de eletricidade."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_ENDESA)

    assert resultado["erro"] is None
    assert resultado["formato"] == "endesa"
    # Deve ser 38.50 (so eletricidade), nao 60.60 (total fatura) nem 22.10 (gas)
    assert resultado["custo_eur"] == pytest.approx(38.50)
    assert resultado["custo_eur"] != pytest.approx(60.60)
    assert resultado["custo_eur"] != pytest.approx(22.10)


def test_extrair_meo_energia_formato_real():
    """Meo Energia: formato real — 'MEO Energia' (caps) e '€ NNN,NN' (euro antes do numero)."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_MEO_ENERGIA_REAL)

    assert resultado["erro"] is None
    assert resultado["formato"] == "meo_energia"
    assert resultado["cpe"] == "PT0002000084968079SX"
    assert resultado["year_month"] == "2026-02"
    assert resultado["custo_eur"] == pytest.approx(343.92)


def test_extrair_endesa_formato_real():
    """Endesa: formato real — 'A LUZ NNN,NN €' e periodo com nomes de mes PT."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_ENDESA_REAL)

    assert resultado["erro"] is None
    assert resultado["formato"] == "endesa"
    assert resultado["cpe"] == "PT0002000039822082NT"
    # So eletricidade, nao total debito (41,46 inclui gas)
    assert resultado["custo_eur"] == pytest.approx(16.25)
    # Periodo: data de fim "22 jan 2026" -> 2026-01
    assert resultado["year_month"] == "2026-01"


def test_formato_desconhecido():
    """Texto sem keywords de Meo ou Endesa retorna erro claro."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_DESCONHECIDO)

    assert resultado["erro"] is not None
    assert "reconhecido" in resultado["erro"].lower() or "suportado" in resultado["erro"].lower()
    assert resultado["formato"] is None
    assert resultado["custo_eur"] is None
    assert resultado["year_month"] is None


def test_cpe_com_espaco():
    """CPE com espaco no texto e normalizado antes de retornar."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_CPE_COM_ESPACO)

    # CPE deve ser normalizado: sem espaco
    assert resultado["cpe"] == "PT000200003982208 2NT".replace(" ", "")
    assert " " not in resultado["cpe"]


# ---------------------------------------------------------------------------
# Teste de extraccao PDF real com pdfplumber + BytesIO
# ---------------------------------------------------------------------------

def test_extrair_texto_pdf_bytesio():
    """pdfplumber.open(BytesIO(bytes)) extrai texto nao-vazio de PDF minimo."""
    fpdf2 = pytest.importorskip("fpdf")
    import pdfplumber
    from io import BytesIO
    from fpdf import FPDF

    # Criar PDF minimo com texto
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Meo Energia Total a pagar: 45,32 EUR")
    pdf_bytes = pdf.output()

    with pdfplumber.open(BytesIO(pdf_bytes)) as doc:
        texto = "\n".join(page.extract_text() or "" for page in doc.pages)

    assert len(texto) > 0
    assert "EUR" in texto or "Meo" in texto or "pagar" in texto


# ---------------------------------------------------------------------------
# Testes de ingestao SQLite (usa fixture db_engine_test do conftest.py)
# ---------------------------------------------------------------------------

def test_ingestao_pdf_escreve_sqlite(db_engine_test):
    """Combina extrair_fatura + escrita em custos_reais; row inserida correctamente."""
    from sqlalchemy import insert
    from src.db.schema import locais, custos_reais
    from src.web.services.extrator_pdf import extrair_fatura

    engine = db_engine_test

    # Inserir local com CPE correspondente
    with engine.begin() as conn:
        conn.execute(insert(locais).values(
            id="casa",
            name="Casa",
            cpe="PT0002000084968079SX",
        ))

    # Extrair dados do texto sintetico
    resultado = extrair_fatura(TEXTO_MEO_ENERGIA)
    assert resultado["erro"] is None

    # Escrever em custos_reais
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    with engine.begin() as conn:
        stmt = sqlite_insert(custos_reais).values(
            location_id="casa",
            year_month=resultado["year_month"],
            custo_eur=resultado["custo_eur"],
            source="pdf_upload",
        ).on_conflict_do_nothing(index_elements=["location_id", "year_month"])
        conn.execute(stmt)

    # Verificar que a row foi inserida
    with engine.connect() as conn:
        rows = conn.execute(select(custos_reais)).fetchall()

    assert len(rows) == 1
    row = dict(rows[0]._mapping)
    assert row["location_id"] == "casa"
    assert row["year_month"] == "2026-01"
    assert row["custo_eur"] == pytest.approx(45.32)
    assert row["source"] == "pdf_upload"


def test_ingestao_pdf_idempotencia(db_engine_test):
    """Mesma fatura ingerida 2x: apenas 1 row em custos_reais."""
    from sqlalchemy import insert
    from src.db.schema import locais, custos_reais
    from src.web.services.extrator_pdf import extrair_fatura
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    engine = db_engine_test

    # Inserir local
    with engine.begin() as conn:
        conn.execute(insert(locais).values(
            id="casa",
            name="Casa",
            cpe="PT0002000084968079SX",
        ))

    resultado = extrair_fatura(TEXTO_MEO_ENERGIA)
    assert resultado["erro"] is None

    # Ingerir duas vezes
    for _ in range(2):
        with engine.begin() as conn:
            stmt = sqlite_insert(custos_reais).values(
                location_id="casa",
                year_month=resultado["year_month"],
                custo_eur=resultado["custo_eur"],
                source="pdf_upload",
            ).on_conflict_do_nothing(index_elements=["location_id", "year_month"])
            conn.execute(stmt)

    # Verificar que apenas 1 row existe
    with engine.connect() as conn:
        rows = conn.execute(select(custos_reais)).fetchall()

    assert len(rows) == 1
