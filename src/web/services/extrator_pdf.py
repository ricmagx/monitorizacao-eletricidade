"""Servico de extraccao de dados de faturas PDF de eletricidade.

Suporta dois formatos de fatura:
- Meo Energia: texto com "Total a pagar" e periodo "DD-MM-YYYY a DD-MM-YYYY"
- Endesa: texto com "Total Eletricidade" e periodo "DD/MM/YYYY a DD/MM/YYYY"

O gas (presente nas faturas Endesa multi-energia) e explicitamente ignorado.
O CPE e extraido do texto e normalizado (sem espacos) para lookup na tabela locais.

pdfplumber e importado de forma lazy dentro de extrair_texto_pdf() para que
outros modulos possam importar extrator_pdf sem causar ImportError caso
pdfplumber nao esteja instalado no ambiente.
"""
import re
from io import BytesIO

from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db.schema import custos_reais
from src.web.services.locais_service import get_local_by_cpe


# ---------------------------------------------------------------------------
# Constantes regex
# ---------------------------------------------------------------------------

# CPE — tolerante a espacos no meio (ex: "PT000200003982208 2NT")
# Formato: PT seguido de digitos e espacos, terminando com 2 letras maiusculas
# Funciona para: PT0002000084968079SX (sem espaco) e PT000200003982208 2NT (com espaco)
CPE_PATTERN = re.compile(r"(PT[\d ]+[A-Z]{2})\b")

# Meo Energia — total pago
TOTAL_MEO_PATTERNS = [
    re.compile(r"Total\s+a\s+pagar[:\s]+(\d+[,\.]\d{2})\s*(?:EUR|€)", re.IGNORECASE),
    re.compile(r"Total[:\s]+(\d+[,\.]\d{2})\s*(?:EUR|€)", re.IGNORECASE),
]

# Meo Energia — periodo (DD-MM-YYYY a DD-MM-YYYY)
PERIODO_MEO_PATTERNS = [
    re.compile(r"(\d{2}-\d{2}-\d{4})\s+a\s+(\d{2}-\d{2}-\d{4})"),
    re.compile(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})"),
]

# Endesa — total ELETRICIDADE (nunca "Total Fatura" nem "Total Gas")
TOTAL_ENDESA_PATTERNS = [
    re.compile(r"Total\s+Ele[ct]ricidade[:\s]+(\d+[,\.]\d{2})\s*(?:EUR|€)", re.IGNORECASE),
]

# Endesa — periodo de consumo
PERIODO_ENDESA_PATTERNS = [
    re.compile(r"Per[ií]odo\s+de\s+Consumo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
    re.compile(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})"),
]


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

def _normalizar_texto(texto: str) -> str:
    """Normaliza whitespace para lidar com quebras de linha no meio de valores."""
    return re.sub(r"\s+", " ", texto)


def _extrair_com_patterns(texto: str, patterns: list) -> re.Match | None:
    """Itera sobre lista de regex e retorna o primeiro match."""
    for pattern in patterns:
        m = pattern.search(texto)
        if m:
            return m
    return None


def _parse_valor_eur(valor_str: str) -> float:
    """Converte '45,32' ou '45.32' para float 45.32."""
    return float(valor_str.replace(",", "."))


def _parse_periodo_para_year_month(data_inicio: str) -> str:
    """Converte 'DD-MM-YYYY' ou 'DD/MM/YYYY' para 'YYYY-MM'.

    Exemplos:
        '01-01-2026' -> '2026-01'
        '01/03/2026' -> '2026-03'
    """
    # Separador pode ser '-' ou '/'
    partes = re.split(r"[-/]", data_inicio)
    # partes = [DD, MM, YYYY]
    dia, mes, ano = partes[0], partes[1], partes[2]
    return f"{ano}-{mes}"


# ---------------------------------------------------------------------------
# Funcao principal de extraccao (aceita texto ja extraido)
# ---------------------------------------------------------------------------

def extrair_fatura(texto: str) -> dict:
    """Extrai dados estruturados de texto de fatura de eletricidade.

    A funcao aceita texto ja extraido (output do pdfplumber ou texto sintetico
    para testes) — a leitura do PDF com pdfplumber e responsabilidade de
    extrair_texto_pdf() ou da camada de upload.

    Args:
        texto: Texto da fatura como string.

    Returns:
        Dict com chaves:
            erro (str | None): Mensagem de erro ou None se OK.
            formato (str | None): 'meo_energia' | 'endesa' | None.
            cpe (str | None): CPE normalizado (sem espacos).
            year_month (str | None): Periodo no formato 'YYYY-MM'.
            custo_eur (float | None): Total pago em EUR (so eletricidade).
    """
    texto_norm = _normalizar_texto(texto)

    # Extrair CPE (tolerante a espacos, normalizar removendo-os)
    cpe_match = CPE_PATTERN.search(texto_norm)
    cpe = cpe_match.group(1).replace(" ", "") if cpe_match else None

    # Detectar formato por keywords no texto
    if "Meo Energia" in texto_norm:
        formato = "meo_energia"
    elif "Endesa" in texto_norm:
        formato = "endesa"
    else:
        return {
            "erro": "Formato de fatura nao reconhecido. Formatos suportados: Meo Energia, Endesa.",
            "formato": None,
            "cpe": cpe,
            "year_month": None,
            "custo_eur": None,
        }

    # Seleccionar patterns conforme formato
    if formato == "meo_energia":
        total_patterns = TOTAL_MEO_PATTERNS
        periodo_patterns = PERIODO_MEO_PATTERNS
    else:
        total_patterns = TOTAL_ENDESA_PATTERNS
        periodo_patterns = PERIODO_ENDESA_PATTERNS

    # Extrair total
    total_match = _extrair_com_patterns(texto_norm, total_patterns)
    if not total_match:
        return {
            "erro": f"Total nao encontrado na fatura {formato}.",
            "formato": formato,
            "cpe": cpe,
            "year_month": None,
            "custo_eur": None,
        }
    custo_eur = _parse_valor_eur(total_match.group(1))

    # Extrair periodo
    periodo_match = _extrair_com_patterns(texto_norm, periodo_patterns)
    if not periodo_match:
        return {
            "erro": f"Periodo nao encontrado na fatura {formato}.",
            "formato": formato,
            "cpe": cpe,
            "year_month": None,
            "custo_eur": custo_eur,
        }
    year_month = _parse_periodo_para_year_month(periodo_match.group(1))

    return {
        "erro": None,
        "formato": formato,
        "cpe": cpe,
        "year_month": year_month,
        "custo_eur": custo_eur,
    }


# ---------------------------------------------------------------------------
# Extraccao de texto de PDF com pdfplumber (lazy import)
# ---------------------------------------------------------------------------

def extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de todas as paginas de um PDF e normaliza whitespace.

    Usa pdfplumber com BytesIO (sem ficheiro temporario).

    NOTE: pdfplumber e importado de forma lazy (dentro desta funcao) para
    evitar ImportError ao carregar o modulo noutros contextos onde pdfplumber
    nao esta instalado.

    Args:
        pdf_bytes: Conteudo do PDF em bytes.

    Returns:
        Texto concatenado de todas as paginas, com whitespace normalizado.
    """
    import pdfplumber  # lazy import — so necessario quando ha PDF real
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        partes = [page.extract_text() or "" for page in pdf.pages]
    texto = "\n".join(partes)
    return _normalizar_texto(texto)


# ---------------------------------------------------------------------------
# Funcao de ingestao completa (PDF bytes -> custos_reais SQLite)
# ---------------------------------------------------------------------------

def ingerir_pdf(pdf_bytes: bytes, engine: Engine) -> dict:
    """Extrai dados de fatura PDF e persiste em custos_reais (idempotente).

    Fluxo:
        1. Extrai texto do PDF com pdfplumber (BytesIO)
        2. Extrai dados estruturados com extrair_fatura()
        3. Resolve location_id via CPE lookup em locais
        4. Escreve em custos_reais com on_conflict_do_nothing

    Args:
        pdf_bytes: Conteudo do PDF em bytes.
        engine: SQLAlchemy engine com schema inicializado.

    Returns:
        Dict com chaves: erro, formato, location_id, location_name,
        cpe, year_month, custo_eur, inserido (bool).
    """
    # 1. Extrair texto
    texto = extrair_texto_pdf(pdf_bytes)

    # 2. Extrair dados estruturados
    dados = extrair_fatura(texto)
    if dados["erro"]:
        return dados

    cpe = dados["cpe"]
    if not cpe:
        return {
            **dados,
            "erro": "CPE nao encontrado no PDF.",
            "location_id": None,
            "location_name": None,
            "inserido": False,
        }

    # 3. Resolver local pelo CPE
    local = get_local_by_cpe(cpe, engine)
    if not local:
        return {
            **dados,
            "erro": f"CPE {cpe} nao corresponde a nenhum local configurado.",
            "location_id": None,
            "location_name": None,
            "inserido": False,
        }

    # 4. Escrever em custos_reais (idempotente)
    with engine.begin() as conn:
        stmt = sqlite_insert(custos_reais).values(
            location_id=local["id"],
            year_month=dados["year_month"],
            custo_eur=dados["custo_eur"],
            source="pdf_upload",
        ).on_conflict_do_nothing(index_elements=["location_id", "year_month"])
        result = conn.execute(stmt)
        inserido = result.rowcount > 0

    return {
        "erro": None,
        "formato": dados["formato"],
        "location_id": local["id"],
        "location_name": local["name"],
        "cpe": cpe,
        "year_month": dados["year_month"],
        "custo_eur": dados["custo_eur"],
        "inserido": inserido,
    }
