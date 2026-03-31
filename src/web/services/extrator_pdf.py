"""Servico de extraccao de dados de faturas PDF de eletricidade.

Suporta dois formatos de fatura:
- Meo Energia: periodo "DD/MM/YYYY a DD/MM/YYYY", total "Total a pagar: € NNN,NN"
- Endesa: periodo com nomes de mes PT ("23 dez 2025 a 22 jan 2026"),
  total de eletricidade "A LUZ NNN,NN €"

Para cada fatura extrai tambem o detalhe de linhas (energia, potencia, impostos)
e calcula o custo real por kWh com todos os custos fixos e impostos incluidos.

O gas (presente nas faturas Endesa multi-energia) e explicitamente ignorado.
O CPE e extraido do texto e normalizado (sem espacos) para lookup na tabela locais.

pdfplumber e importado de forma lazy dentro de extrair_texto_pdf() para que
outros modulos possam importar extrator_pdf sem causar ImportError caso
pdfplumber nao esteja instalado no ambiente.
"""
import json
import re
from io import BytesIO

from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db.schema import custos_reais
from src.web.services.locais_service import get_local_by_cpe


# ---------------------------------------------------------------------------
# Helpers de parsing numerico
# ---------------------------------------------------------------------------

def _parse_num(s: str) -> float:
    """Converte numero PT para float.

    Trata espaco como separador de milhares e virgula como decimal.
    Exemplos:
        '540,00'   -> 540.0
        '1 161,00' -> 1161.0  (espaco = separador de milhares)
        '0,1999'   -> 0.1999
        '-10,00'   -> -10.0
    """
    return float(s.replace(" ", "").replace(",", "."))


def _parse_valor_eur(valor_str: str) -> float:
    """Alias publico para compatibilidade com codigo existente."""
    return _parse_num(valor_str)


# ---------------------------------------------------------------------------
# Regex — identificacao de formato e totais
# ---------------------------------------------------------------------------

CPE_PATTERN = re.compile(r"(PT[\d ]+[A-Z]{2})\b")

# Meo — total pago (formato real: "Total a pagar: € 343,92")
TOTAL_MEO_PATTERNS = [
    re.compile(r"Total\s+a\s+pagar[:\s]+(?:EUR|€)?\s*(\d+[,\.]\d{2})", re.IGNORECASE),
    re.compile(r"Total[:\s]+(?:EUR|€)?\s*(\d+[,\.]\d{2})\s*(?:EUR|€)?", re.IGNORECASE),
]

# Meo — periodo de faturacao
PERIODO_MEO_PATTERNS = [
    re.compile(r"Per[ií]odo\s+de\s+fatura[çc][aã]o[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
    re.compile(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})"),
    re.compile(r"(\d{2}-\d{2}-\d{4})\s+a\s+(\d{2}-\d{2}-\d{4})"),
]

# Endesa — total de eletricidade (nunca "TOTAL A DEBITAR" que inclui gas)
TOTAL_ENDESA_PATTERNS = [
    re.compile(r"\bA\s+LUZ\s+(\d+[,\.]\d{2})\s*€", re.IGNORECASE),
    re.compile(r"Total\s+Ele[ct]ricidade[:\s]+(?:EUR|€)?\s*(\d+[,\.]\d{2})", re.IGNORECASE),
    re.compile(r"TOTAL\s+Luz\s+\([^)]+\)\s+([\d]+[,\.][\d]{2})\s*€", re.IGNORECASE),
    re.compile(r"(?<!\bGÁS\s)\bLUZ\s+([\d]+[,\.][\d]{2})\s*€", re.IGNORECASE),
]

# Endesa — periodo com nomes de mes PT
_MESES_PT = {
    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
    "set": "09", "out": "10", "nov": "11", "dez": "12",
}
PERIODO_ENDESA_PT_PATTERN = re.compile(
    r"Per[ií]odo\s+de\s+Fatura[çc][aã]o[:\s]+"
    r"(\d{1,2})\s+([a-z]{3})\s+(\d{4})\s+a\s+(\d{1,2})\s+([a-z]{3})\s+(\d{4})",
    re.IGNORECASE,
)
PERIODO_ENDESA_PATTERNS = [
    re.compile(r"Per[ií]odo\s+de\s+[Cc]onsumo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
    re.compile(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})"),
]


# ---------------------------------------------------------------------------
# Regex — linhas detalhadas Meo Energia
# Formato normalizado: [DESC] DD/MM/YYYY DD/MM/YYYY QTY (UNIT) € UNIT_PRICE € TOTAL IVA%
# ---------------------------------------------------------------------------

_D = r"\d{2}/\d{2}/\d{4}"   # data
_N = r"[\d][\d ,]*[,\.]\d+" # numero PT (com possivel espaco de milhares)
_P = r"[\d,\.]+"             # preco simples

# Energia bi-horaria
_MEO_FORA_VAZIO = re.compile(
    rf"Fora\s+Vazio\s+{_D}\s+{_D}\s+({_N})\s+\(kWh\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)
_MEO_VAZIO = re.compile(
    rf"Vazio\s+Normal\s+{_D}\s+{_D}\s+({_N})\s+\(kWh\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)
# Potencia (o texto antes das datas inclui "kVA - Potência Contratada")
_MEO_POTENCIA = re.compile(
    rf"Pot[êe]ncia\s+Contratada\s+{_D}\s+{_D}\s+({_P})\s+\(Dias\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)
# CAV — texto antes das datas inclui "2,85 € x 12 meses / 365,25 dias"
_MEO_CAV = re.compile(
    rf"AudioVisual.*?({_D})\s+{_D}\s+({_P})\s+\(Dias\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)
# IEC
_MEO_IEC = re.compile(
    rf"Imposto\s+Especial\s+de\s+Consumo\s+Eletricidade\s+{_D}\s+{_D}\s+({_N})\s+\(kWh\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)
# DGEG
_MEO_DGEG = re.compile(
    rf"Explora[çc][aã]o\s+DGEG\s+{_D}\s+{_D}\s+({_P})\s+\(UN\)\s+€\s+({_P})\s+€\s+({_P})\s+(\d+)%"
)


# ---------------------------------------------------------------------------
# Regex — linhas detalhadas Endesa LUZ
# Formato: [DESC] QTY unit PRICE€/unit [DISC_PRICE€/unit] BASE€ DISC€ LIQ€ IVA%
# Sub-periodos: mesma descricao aparece varias vezes (dez + jan)
# ---------------------------------------------------------------------------

_ENDESA_ENERGIA = re.compile(
    r"Termo\s+de\s+Energia\s+\(Real\)\s+(\d+)\s+kWh\s+([\d,\.]+)€/kWh\s+\[([\d,\.]+)€/kWh\]"
    r"\s+([\d,\.]+)\s+€\s+(-?[\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)
_ENDESA_POTENCIA = re.compile(
    r"Termo\s+de\s+Pot[êe]ncia\s+\([^)]+\)\s+(\d+)\s+dias\s+([\d,\.]+)€/dia\s+\[([\d,\.]+)€/dia\]"
    r"\s+([\d,\.]+)\s+€\s+(-?[\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)
_ENDESA_FIXO = re.compile(
    r"Termo\s+Fixo\s+Acesso\s+[aà]s\s+Redes\s+(\d+)\s+dias\s+([\d,\.]+)€/dia\s+\[([\d,\.]+)€/dia\]"
    r"\s+([\d,\.]+)\s+€\s+(-?[\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)
# Desconto de boas-vindas: "1,00 -10,000000€ -10,00 € -10,00 € 23%"
_ENDESA_DESCONTO_BV = re.compile(
    r"Desconto\s+de\s+boas-vindas\s+[\d,\.]+\s+(-[\d,\.]+)€\s+(-[\d,\.]+)\s+€\s+(-[\d,\.]+)\s+€\s+(\d+)%"
)
# CAV / Audiovisual (sem desconto): "1,0192 meses 2,850000€/meses 2,90 € 2,90 € 6%"
_ENDESA_CAV = re.compile(
    r"[Aa]udiovisual\s+([\d,\.]+)\s+meses\s+([\d,\.]+)€/meses\s+([\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)
# DGEG (sem desconto): "Taxa Exploração DGEG (DL-4/93) 1,0192 meses 0,070000€/meses 0,07 € 0,07 € 23%"
# Nota: uso .*? (lazy) porque o texto contem "(DL-4/93)" com digitos antes da quantidade
_ENDESA_DGEG = re.compile(
    r"Explora[çc][aã]o\s+DGEG.*?([\d,\.]+)\s+meses\s+([\d,\.]+)€/meses\s+([\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)
# IEC (sem desconto): "Imposto Especial Consumo (Real) 28 kWh 0,001000€/kWh 0,03 € 0,03 € 23%"
_ENDESA_IEC = re.compile(
    r"Imposto\s+Especial\s+Consumo\s+\(Real\)\s+(\d+)\s+kWh\s+([\d,\.]+)€/kWh\s+([\d,\.]+)\s+€\s+([\d,\.]+)\s+€\s+(\d+)%"
)


# ---------------------------------------------------------------------------
# Extraccao de linhas detalhadas
# ---------------------------------------------------------------------------

def _extrair_linhas_meo(texto_norm: str) -> list[dict]:
    """Extrai linhas de detalhe de uma fatura Meo Energia.

    Cada dict tem: tipo, kwh (se energia), qty/unidade (se fixo),
    preco_base, valor_liquido, iva_pct.
    """
    linhas = []

    m = _MEO_FORA_VAZIO.search(texto_norm)
    if m:
        linhas.append({
            "tipo": "energia_fv",
            "kwh": _parse_num(m.group(1)),
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(3)),
            "iva_pct": int(m.group(4)),
        })

    m = _MEO_VAZIO.search(texto_norm)
    if m:
        linhas.append({
            "tipo": "energia_vn",
            "kwh": _parse_num(m.group(1)),
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(3)),
            "iva_pct": int(m.group(4)),
        })

    m = _MEO_POTENCIA.search(texto_norm)
    if m:
        linhas.append({
            "tipo": "potencia",
            "qty": _parse_num(m.group(1)),
            "unidade": "dias",
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(3)),
            "iva_pct": int(m.group(4)),
        })

    m = _MEO_CAV.search(texto_norm)
    if m:
        # grupos: (data_inicio), qty, preco, valor, iva
        linhas.append({
            "tipo": "cav",
            "qty": _parse_num(m.group(2)),
            "unidade": "dias",
            "preco_base": _parse_num(m.group(3)),
            "valor_liquido": _parse_num(m.group(4)),
            "iva_pct": int(m.group(5)),
        })

    m = _MEO_IEC.search(texto_norm)
    if m:
        linhas.append({
            "tipo": "iec",
            "kwh": _parse_num(m.group(1)),
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(3)),
            "iva_pct": int(m.group(4)),
        })

    m = _MEO_DGEG.search(texto_norm)
    if m:
        linhas.append({
            "tipo": "dgeg",
            "qty": _parse_num(m.group(1)),
            "unidade": "UN",
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(3)),
            "iva_pct": int(m.group(4)),
        })

    return linhas


def _agregar_subperiodos(matches, tipo: str, unidade_qty: str) -> dict | None:
    """Agrega multiplos sub-periodos Endesa numa unica linha.

    Args:
        matches: lista de re.Match com grupos (qty, preco_base, preco_desconto,
                 valor_base, desconto, valor_liquido, iva_pct)
        tipo: tipo da linha (ex: 'energia', 'potencia')
        unidade_qty: 'kWh' | 'dias'

    Returns dict agregado ou None se lista vazia.
    """
    if not matches:
        return None

    qty_total = sum(_parse_num(m.group(1)) for m in matches)
    valor_base_total = sum(_parse_num(m.group(4)) for m in matches)
    desconto_total = sum(_parse_num(m.group(5)) for m in matches)
    valor_liq_total = sum(_parse_num(m.group(6)) for m in matches)
    iva_pct = int(matches[0].group(7))

    # Preco base medio ponderado por quantidade
    preco_base_medio = (
        sum(_parse_num(m.group(2)) * _parse_num(m.group(1)) for m in matches) / qty_total
        if qty_total else 0
    )
    preco_desc_medio = (
        sum(_parse_num(m.group(3)) * _parse_num(m.group(1)) for m in matches) / qty_total
        if qty_total else 0
    )
    desconto_pct = round((1 - preco_desc_medio / preco_base_medio) * 100, 1) if preco_base_medio else 0

    result = {
        "tipo": tipo,
        "preco_base": round(preco_base_medio, 6),
        "preco_com_desconto": round(preco_desc_medio, 6),
        "desconto_pct": desconto_pct,
        "valor_base": round(valor_base_total, 2),
        "desconto_eur": round(desconto_total, 2),
        "valor_liquido": round(valor_liq_total, 2),
        "iva_pct": iva_pct,
        "subperiodos": len(matches),
    }
    if unidade_qty == "kWh":
        result["kwh"] = qty_total
    else:
        result["qty"] = qty_total
        result["unidade"] = unidade_qty
    return result


def _secao_luz_endesa(texto_norm: str) -> str:
    """Extrai apenas a seccao LUZ de uma fatura Endesa combinada LUZ+GAS.

    A seccao LUZ comeca em 'LUZ Fatura:' e termina em 'GAS Fatura:'
    (ou no fim do texto se nao houver GAS).
    Sem este isolamento, os patterns casariam com linhas da seccao GAS.
    """
    # Marcador de inicio da seccao LUZ detalhada (pagina 2)
    ini = re.search(r"\bLUZ\s+Fatura\s*:", texto_norm, re.IGNORECASE)
    # Marcador de inicio da seccao GAS detalhada
    fim = re.search(r"\bG[AÁ]S\s+Fatura\s*:", texto_norm, re.IGNORECASE)
    start = ini.start() if ini else 0
    end = fim.start() if fim else len(texto_norm)
    return texto_norm[start:end]


def _extrair_linhas_endesa(texto_norm: str) -> list[dict]:
    """Extrai linhas de detalhe de uma fatura Endesa LUZ.

    Sub-periodos (ex: dez 2025 + jan 2026) sao agregados por tipo.
    Gas e ignorado — extraccao restrita a seccao LUZ do texto.
    """
    # Isolar seccao LUZ para evitar casamentos com linhas de GAS
    texto_luz = _secao_luz_endesa(texto_norm)

    linhas = []

    energia_matches = list(_ENDESA_ENERGIA.finditer(texto_luz))
    linha = _agregar_subperiodos(energia_matches, "energia", "kWh")
    if linha:
        linhas.append(linha)

    potencia_matches = list(_ENDESA_POTENCIA.finditer(texto_luz))
    linha = _agregar_subperiodos(potencia_matches, "potencia", "dias")
    if linha:
        linhas.append(linha)

    fixo_matches = list(_ENDESA_FIXO.finditer(texto_luz))
    linha = _agregar_subperiodos(fixo_matches, "termo_fixo_redes", "dias")
    if linha:
        linhas.append(linha)

    m = _ENDESA_DESCONTO_BV.search(texto_luz)
    if m:
        linhas.append({
            "tipo": "desconto_bv",
            "valor_liquido": _parse_num(m.group(3)),  # negativo
            "iva_pct": int(m.group(4)),
        })

    m = _ENDESA_CAV.search(texto_luz)
    if m:
        linhas.append({
            "tipo": "cav",
            "qty": _parse_num(m.group(1)),
            "unidade": "meses",
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(4)),
            "iva_pct": int(m.group(5)),
        })

    m = _ENDESA_DGEG.search(texto_luz)
    if m:
        linhas.append({
            "tipo": "dgeg",
            "qty": _parse_num(m.group(1)),
            "unidade": "meses",
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(4)),
            "iva_pct": int(m.group(5)),
        })

    m = _ENDESA_IEC.search(texto_luz)
    if m:
        linhas.append({
            "tipo": "iec",
            "kwh": _parse_num(m.group(1)),
            "preco_base": _parse_num(m.group(2)),
            "valor_liquido": _parse_num(m.group(4)),
            "iva_pct": int(m.group(5)),
        })

    return linhas


# ---------------------------------------------------------------------------
# Calculo de custo real por kWh
# ---------------------------------------------------------------------------

def _calcular_custos_meo(linhas: list[dict]) -> dict:
    """Calcula custo real por kWh para Meo Energia (tarifa bi-horaria).

    Distribui custos fixos (potencia, CAV, DGEG) e IEC proporcionalmente
    entre Fora Vazio e Vazio Normal. IVA incluido em todos os valores.

    Returns dict com custo_real_kwh_fv, custo_real_kwh_vn.
    """
    by_tipo = {l["tipo"]: l for l in linhas}

    fv = by_tipo.get("energia_fv")
    vn = by_tipo.get("energia_vn")
    if not fv or not vn:
        return {"custo_real_kwh_fv": None, "custo_real_kwh_vn": None, "custo_real_kwh": None}

    kwh_fv = fv["kwh"]
    kwh_vn = vn["kwh"]
    kwh_total = kwh_fv + kwh_vn

    # Custos de energia com IVA
    cost_fv = fv["valor_liquido"] * (1 + fv["iva_pct"] / 100)
    cost_vn = vn["valor_liquido"] * (1 + vn["iva_pct"] / 100)

    # Custos fixos (potencia + CAV + DGEG) com IVA — distribuir pro-rata kWh
    fixed_com_iva = sum(
        l["valor_liquido"] * (1 + l["iva_pct"] / 100)
        for tipo, l in by_tipo.items()
        if tipo in ("potencia", "cav", "dgeg")
    )

    # IEC (variavel por kWh)
    iec = by_tipo.get("iec")
    iec_por_kwh = (iec["preco_base"] * (1 + iec["iva_pct"] / 100)) if iec else 0

    ratio_fv = kwh_fv / kwh_total
    ratio_vn = kwh_vn / kwh_total

    total_fv = cost_fv + fixed_com_iva * ratio_fv + iec_por_kwh * kwh_fv
    total_vn = cost_vn + fixed_com_iva * ratio_vn + iec_por_kwh * kwh_vn

    return {
        "custo_real_kwh_fv": round(total_fv / kwh_fv, 6) if kwh_fv else None,
        "custo_real_kwh_vn": round(total_vn / kwh_vn, 6) if kwh_vn else None,
        "custo_real_kwh": None,
    }


def _calcular_custos_endesa(linhas: list[dict]) -> dict:
    """Calcula custo real por kWh para Endesa (tarifa simples).

    Soma todos os custos LUZ com IVA e divide pelos kWh consumidos.
    Inclui descontos (que reduzem o custo real).

    Returns dict com custo_real_kwh.
    """
    kwh_total = sum(l.get("kwh", 0) for l in linhas if l["tipo"] == "energia")
    if not kwh_total:
        return {"custo_real_kwh_fv": None, "custo_real_kwh_vn": None, "custo_real_kwh": None}

    total_com_iva = sum(
        l["valor_liquido"] * (1 + l.get("iva_pct", 0) / 100)
        for l in linhas
    )
    return {
        "custo_real_kwh_fv": None,
        "custo_real_kwh_vn": None,
        "custo_real_kwh": round(total_com_iva / kwh_total, 6),
    }


# ---------------------------------------------------------------------------
# Funcoes auxiliares de parsing de periodo e texto
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


def _parse_periodo_para_year_month(data_inicio: str) -> str:
    """Converte 'DD-MM-YYYY' ou 'DD/MM/YYYY' para 'YYYY-MM'."""
    partes = re.split(r"[-/]", data_inicio)
    dia, mes, ano = partes[0], partes[1], partes[2]
    return f"{ano}-{mes}"


def _parse_periodo_endesa_pt(texto_norm: str) -> tuple[str | None, str | None, str | None]:
    """Extrai (year_month, periodo_inicio, periodo_fim) do periodo Endesa em formato PT.

    Formato: 'Período de Faturação: 23 dez 2025 a 22 jan 2026'
    Usa a data de fim para determinar o mes de faturacao.
    """
    m = PERIODO_ENDESA_PT_PATTERN.search(texto_norm)
    if not m:
        return None, None, None
    dia_ini, mes_ini_str, ano_ini = m.group(1), m.group(2).lower()[:3], m.group(3)
    dia_fim, mes_fim_str, ano_fim = m.group(4), m.group(5).lower()[:3], m.group(6)
    mes_ini = _MESES_PT.get(mes_ini_str)
    mes_fim = _MESES_PT.get(mes_fim_str)
    if not mes_fim:
        return None, None, None
    year_month = f"{ano_fim}-{mes_fim}"
    periodo_inicio = f"{ano_ini}-{mes_ini}-{dia_ini.zfill(2)}" if mes_ini else None
    periodo_fim = f"{ano_fim}-{mes_fim}-{dia_fim.zfill(2)}"
    return year_month, periodo_inicio, periodo_fim


# ---------------------------------------------------------------------------
# Funcao principal de extraccao
# ---------------------------------------------------------------------------

def extrair_fatura(texto: str) -> dict:
    """Extrai dados estruturados de texto de fatura de eletricidade.

    Args:
        texto: Texto da fatura (output pdfplumber ou texto sintetico para testes).

    Returns:
        Dict com chaves:
            erro (str | None)
            formato (str | None): 'meo_energia' | 'endesa'
            cpe (str | None): CPE normalizado sem espacos
            year_month (str | None): 'YYYY-MM'
            custo_eur (float | None): total pago (so eletricidade)
            detalhe (dict | None): linhas detalhadas + custo real por kWh
    """
    texto_norm = _normalizar_texto(texto)

    cpe_match = CPE_PATTERN.search(texto_norm)
    cpe = cpe_match.group(1).replace(" ", "") if cpe_match else None

    texto_lower = texto_norm.lower()
    if "meo energia" in texto_lower or "meoenergia" in texto_lower:
        formato = "meo_energia"
    elif "endesa" in texto_lower:
        formato = "endesa"
    else:
        return {
            "erro": "Formato de fatura nao reconhecido. Formatos suportados: Meo Energia, Endesa.",
            "formato": None, "cpe": cpe, "year_month": None, "custo_eur": None, "detalhe": None,
        }

    # Extrair total
    total_patterns = TOTAL_MEO_PATTERNS if formato == "meo_energia" else TOTAL_ENDESA_PATTERNS
    total_match = _extrair_com_patterns(texto_norm, total_patterns)
    if not total_match:
        return {
            "erro": f"Total nao encontrado na fatura {formato}.",
            "formato": formato, "cpe": cpe, "year_month": None, "custo_eur": None, "detalhe": None,
        }
    custo_eur = _parse_valor_eur(total_match.group(1))

    # Extrair periodo
    year_month = None
    periodo_inicio = periodo_fim = None

    if formato == "endesa":
        year_month, periodo_inicio, periodo_fim = _parse_periodo_endesa_pt(texto_norm)

    if not year_month:
        periodo_patterns = PERIODO_MEO_PATTERNS if formato == "meo_energia" else PERIODO_ENDESA_PATTERNS
        periodo_match = _extrair_com_patterns(texto_norm, periodo_patterns)
        if not periodo_match:
            return {
                "erro": f"Periodo nao encontrado na fatura {formato}.",
                "formato": formato, "cpe": cpe, "year_month": None,
                "custo_eur": custo_eur, "detalhe": None,
            }
        year_month = _parse_periodo_para_year_month(periodo_match.group(1))
        periodo_inicio = periodo_match.group(1)
        periodo_fim = periodo_match.group(2) if len(periodo_match.groups()) >= 2 else None

    # Extrair linhas detalhadas (graceful — nao falha a extraccao principal)
    detalhe = None
    try:
        if formato == "meo_energia":
            linhas = _extrair_linhas_meo(texto_norm)
            custos_kwh = _calcular_custos_meo(linhas)
        else:
            linhas = _extrair_linhas_endesa(texto_norm)
            custos_kwh = _calcular_custos_endesa(linhas)

        if linhas:
            detalhe = {
                "periodo_inicio": periodo_inicio,
                "periodo_fim": periodo_fim,
                "linhas": linhas,
                **custos_kwh,
            }
    except Exception:
        pass  # detalhe fica None — nao compromete a ingestao

    return {
        "erro": None,
        "formato": formato,
        "cpe": cpe,
        "year_month": year_month,
        "custo_eur": custo_eur,
        "detalhe": detalhe,
    }


# ---------------------------------------------------------------------------
# Extraccao de texto de PDF com pdfplumber (lazy import)
# ---------------------------------------------------------------------------

def extrair_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de todas as paginas de um PDF e normaliza whitespace."""
    import pdfplumber  # lazy import
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        partes = [page.extract_text() or "" for page in pdf.pages]
    texto = "\n".join(partes)
    return _normalizar_texto(texto)


# ---------------------------------------------------------------------------
# Ingestao completa (PDF bytes -> custos_reais SQLite)
# ---------------------------------------------------------------------------

def ingerir_pdf(pdf_bytes: bytes, engine: Engine) -> dict:
    """Extrai dados de fatura PDF e persiste em custos_reais (idempotente).

    Returns dict com: erro, formato, location_id, location_name,
    cpe, year_month, custo_eur, detalhe, inserido (bool).
    """
    texto = extrair_texto_pdf(pdf_bytes)
    dados = extrair_fatura(texto)
    if dados["erro"]:
        return dados

    cpe = dados["cpe"]
    if not cpe:
        return {**dados, "erro": "CPE nao encontrado no PDF.",
                "location_id": None, "location_name": None, "inserido": False}

    local = get_local_by_cpe(cpe, engine)
    if not local:
        return {**dados, "erro": f"CPE {cpe} nao corresponde a nenhum local configurado.",
                "location_id": None, "location_name": None, "inserido": False}

    detalhe_json = json.dumps(dados["detalhe"], ensure_ascii=False) if dados["detalhe"] else None

    with engine.begin() as conn:
        stmt = sqlite_insert(custos_reais).values(
            location_id=local["id"],
            year_month=dados["year_month"],
            custo_eur=dados["custo_eur"],
            source="pdf_upload",
            detalhe_json=detalhe_json,
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
        "detalhe": dados["detalhe"],
        "inserido": inserido,
    }
