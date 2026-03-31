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

# Formato real MEO Energia: "MEO Energia" (caps), "€ NNN,NN", linhas detalhadas bi-horaria
TEXTO_MEO_ENERGIA_REAL = """
.A.S ,aigrenE ed oãçazilaicremoC - aigrenE OEM
Pág. 1 de 3
Fatura: FA ME26/615 053 de 24/03/2026
Período de faturação: 07/02/2026 a 20/03/2026
CPE (Código Ponto de Entrega): PT0002000084968079SX
Tarifa: MEO + MEO Energia FIXA MB PAPEL M4 09.25
Total a pagar: € 343,92
Pág. 2 de 3
Potência Contratada 07/02/2026 20/03/2026 42,00 (Dias) € 0,6500 € 27,30 23%
Consumo medido em Fora Vazio 07/02/2026 20/03/2026 540,00 (kWh) € 0,1999 € 107,95 23%
Consumo medido em Vazio Normal 07/02/2026 20/03/2026 1 161,00 (kWh) € 0,1199 € 139,20 23%
CAV Contribuição AudioVisual 2,85 € x 12 meses / 365,25 dias 07/02/2026 20/03/2026 42,00 (Dias) € 0,0936 € 3,93 6%
IEC Imposto Especial de Consumo Eletricidade 07/02/2026 20/03/2026 1 701,00 (kWh) € 0,0010 € 1,70 23%
Taxa de Exploração DGEG 07/02/2026 20/03/2026 1,00 (UN) € 0,0700 € 0,07 23%
meoenergia.pt
"""

# Formato real Endesa: "A LUZ NNN,NN €", periodo PT, secao LUZ com sub-periodos e descontos
TEXTO_ENDESA_REAL = """
K Luz e Gás Nº Documento: 26010310165507399
TOTAL A DEBITAR 41,46 €
A LUZ 16,25 €
B GÁS 28,54 €
A CPE (Código Ponto Entrega) PT 0002 0000 3982 2082 NT
Endesa poupa todos os meses!
LUZ Fatura: FAC 0280312026/0077051163 Data: 29 jan 2026 Período de Faturação: 23 dez 2025 a 22 jan 2026
Termo de Energia (Real) 8 kWh 0,171050€/kWh [0,136840€/kWh] 1,37 € -0,27 € 1,10 € 6% (b)
Termo de Energia (Real) 20 kWh 0,174553€/kWh [0,139642€/kWh] 3,49 € -0,68 € 2,81 € 6% (b)
Termo de Potência (3.45 kVA) 9 dias 0,322000€/dia [0,257600€/dia] 2,90 € -0,59 € 2,31 € 23% (c)
Termo de Potência (3.45 kVA) 22 dias 0,332913€/dia [0,266330€/dia] 7,32 € -1,47 € 5,85 € 23% (c)
Termo Fixo Acesso às Redes 9 dias 0,158700€/dia [0,126960€/dia] 1,43 € -0,27 € 1,16 € 6% (b)
Termo Fixo Acesso às Redes 22 dias 0,171800€/dia [0,137440€/dia] 3,78 € -0,76 € 3,02 € 6% (b)
Desconto de boas-vindas 1,00 -10,000000€ -10,00 € -10,00 € 23% (c)
Contribuição Audiovisual 1,0192 meses 2,850000€/meses 2,90 € 2,90 € 6% (b)
Taxa Exploração DGEG (DL-4/93) 1,0192 meses 0,070000€/meses 0,07 € 0,07 € 23% (c)
Imposto Especial Consumo (Real) 28 kWh 0,001000€/kWh 0,03 € 0,03 € 23% (c)
GÁS Fatura: FAC 0280312026/0077051888
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


def test_detalhe_meo_energia():
    """Meo Energia: detalhe com 6 linhas e custo real por kWh para bi-horaria."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_MEO_ENERGIA_REAL)

    d = resultado["detalhe"]
    assert d is not None

    tipos = {l["tipo"] for l in d["linhas"]}
    assert "energia_fv" in tipos
    assert "energia_vn" in tipos
    assert "potencia" in tipos
    assert "cav" in tipos
    assert "iec" in tipos
    assert "dgeg" in tipos

    fv = next(l for l in d["linhas"] if l["tipo"] == "energia_fv")
    assert fv["kwh"] == pytest.approx(540.0)
    assert fv["preco_base"] == pytest.approx(0.1999)

    # Custo real por kWh: FV mais caro que VN (inclui custos fixos distribuidos)
    assert d["custo_real_kwh_fv"] is not None
    assert d["custo_real_kwh_vn"] is not None
    assert d["custo_real_kwh_fv"] > d["custo_real_kwh_vn"]
    # Valores calculados validados contra fatura real
    assert d["custo_real_kwh_fv"] == pytest.approx(0.2694, abs=0.001)
    assert d["custo_real_kwh_vn"] == pytest.approx(0.1709, abs=0.001)


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


def test_detalhe_endesa():
    """Endesa: detalhe com 7 linhas (inclui desconto BV) e custo real por kWh."""
    from src.web.services.extrator_pdf import extrair_fatura

    resultado = extrair_fatura(TEXTO_ENDESA_REAL)

    d = resultado["detalhe"]
    assert d is not None

    tipos = {l["tipo"] for l in d["linhas"]}
    assert "energia" in tipos
    assert "potencia" in tipos
    assert "termo_fixo_redes" in tipos
    assert "desconto_bv" in tipos
    assert "cav" in tipos
    assert "dgeg" in tipos
    assert "iec" in tipos

    energia = next(l for l in d["linhas"] if l["tipo"] == "energia")
    assert energia["kwh"] == pytest.approx(28.0)
    assert energia["subperiodos"] == 2
    assert energia["desconto_pct"] == pytest.approx(20.0, abs=0.5)

    # Desconto BV e negativo
    bv = next(l for l in d["linhas"] if l["tipo"] == "desconto_bv")
    assert bv["valor_liquido"] < 0

    # Custo real inclui todos os componentes
    assert d["custo_real_kwh"] is not None
    assert d["custo_real_kwh"] > 0
    assert d["custo_real_kwh_fv"] is None  # tarifa simples, sem bi-horaria


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
