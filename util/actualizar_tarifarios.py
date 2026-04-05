"""Actualiza config/tarifarios.json com dados do simulador da ERSE.

Fontes (sem API key, sem Playwright):
  Settings.json  →  URL actual do ZIP de preços
  Precos_ELEGN.csv  →  preços por fornecedor/plano/potência/contagem
  CondComerciais.csv  →  nome do plano, link directo, filtros

Os preços incluem: energia + TAR (tarifas de acesso às redes) + IVA.
São os mesmos valores que o simulador da ERSE usa internamente.

Uso:
  python util/actualizar_tarifarios.py
  python util/actualizar_tarifarios.py --potencia 6.9
  python util/actualizar_tarifarios.py --potencia 6.9 --sem-restricoes
  python util/actualizar_tarifarios.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

SETTINGS_URL = "https://simuladorprecos.erse.pt/config/Settings.json"
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "config" / "tarifarios.json"

# Mapeamento código ERSE → nome legível do fornecedor
COM_NAMES: dict[str, str] = {
    "GOLD": "Goldenergy",
    "LUZBOA": "Luzboa",
    "END": "Endesa",
    "GALP": "Galp",
    "EDP": "EDP",
    "IBERDROLA": "Iberdrola",
    "ALFAENERGIA": "Alfa Energia",
    "AUDAX": "Audax",
    "AXPO": "Axpo",
    "COOP": "Coopernico",
    "ELERGONE": "Elergone",
    "G9ENERGY": "G9 Energy",
    "IBD": "Iberdrola",
    "IBELECTRA": "Ibelectra",
    "JAFPLUS": "JAF Plus",
    "LOGICA": "Lógica",
    "LUZIGAS": "Luzigas",
    "DOUROGAS": "Douro Gás",
    "EZUENERGIA": "EZU Energia",
    "ENIPLENITUDINE": "Eni Plenitude",
    "ENIPLENITUDE": "Eni Plenitude",
}


def supplier_name(com: str, link_com: str = "") -> str:
    """Devolve nome legível do fornecedor a partir do código ERSE."""
    if com in COM_NAMES:
        return COM_NAMES[com]
    # Tenta extrair domínio do link
    if link_com:
        try:
            domain = link_com.split("//")[-1].split("/")[0]
            domain = domain.replace("www.", "").split(".")[0]
            return domain.capitalize()
        except Exception:
            pass
    return com


def fetch_zip_url() -> str:
    """Lê Settings.json da ERSE e extrai URL actual do ZIP de preços."""
    with urllib.request.urlopen(SETTINGS_URL, timeout=15) as resp:
        settings = json.load(resp)
    return settings["csvPath"]


def download_and_extract(zip_url: str) -> tuple[list[dict], list[dict]]:
    """Faz download do ZIP e devolve (precos_rows, cond_rows)."""
    zip_url_encoded = urllib.parse.quote(zip_url, safe=":/?=&")
    print(f"  A descarregar: {zip_url_encoded}")
    with urllib.request.urlopen(zip_url_encoded, timeout=30) as resp:
        zip_data = resp.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # Nomes dos ficheiros no ZIP usam backslash como separador
        precos_name = next(n for n in zf.namelist() if "Precos_ELEGN" in n)
        cond_name = next(n for n in zf.namelist() if "CondComerciais" in n)

        def read_csv(name: str) -> list[dict]:
            with zf.open(name) as f:
                text = f.read().decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(text), delimiter=";"))

        return read_csv(precos_name), read_csv(cond_name)


def parse_float(val: str) -> float | None:
    """Converte string com vírgula decimal para float. Devolve None se vazio."""
    val = val.strip()
    if not val:
        return None
    return float(val.replace(",", "."))


def build_cond_index(cond_rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Índice {(COM, COD_Proposta): row} para join rápido."""
    idx: dict[tuple[str, str], dict] = {}
    for row in cond_rows:
        key = (row["COM"], row["COD_Proposta"])
        if key not in idx:
            idx[key] = row
    return idx


def is_eligible(cond: dict, incluir_restricoes: bool) -> bool:
    """Verifica se um plano é elegível (doméstico, eletricidade, não indexado).

    FiltroTarifaSocial=S significa apenas que o plano *suporta* tarifa social —
    não é um filtro de exclusão. FiltroRestrições=S significa que o plano tem
    restrições de elegibilidade (ex: só para associados X) — excluído por omissão.
    """
    if cond.get("Segmento") != "Dom":
        return False
    if cond.get("Fornecimento") not in ("ELE",):
        return False
    if cond.get("FiltroPrecosIndex_ELE") == "S":
        return False
    if not incluir_restricoes and cond.get("FiltroRestrições") == "S":
        return False
    return True


def build_tariff_entry(
    preco: dict,
    cond: dict,
    pot_kva: float,
) -> dict | None:
    """Constrói uma entrada de tarifário a partir de uma linha Precos + CondComerciais."""
    contagem = preco["Contagem"].strip()
    if contagem == "1":
        tariff_type = "simples"
    elif contagem == "2":
        tariff_type = "bihorario"
    else:
        return None  # trihorário não suportado

    tf = parse_float(preco["TF"])
    tv_fv = parse_float(preco["TV|TVFV|TVP"])  # simples ou fora-de-vazio
    tvv = parse_float(preco["TVV|TVC"])         # vazio

    if tf is None or tv_fv is None:
        return None

    com = preco["COM"]
    cod = preco["COD_Proposta"]
    nome = cond.get("NomeProposta", "").strip()
    link_com = cond.get("LinkCOM", "").strip()
    link_oferta = cond.get("LinkOfertaCom", "").strip()

    supplier = supplier_name(com, link_com)
    plan_label = f"{nome} ({'Bi-horária' if tariff_type == 'bihorario' else 'Simples'})"

    data_ini = cond.get("Data ini", "").strip()
    data_fim = cond.get("Data fim", "").strip()
    valid_from = _parse_date(data_ini) or date.today().isoformat()
    valid_to = _parse_date(data_fim)

    entry: dict = {
        "id": f"{com.lower()}-{cod.lower()}-{tariff_type[:3]}",
        "supplier": supplier,
        "plan": plan_label,
        "type": tariff_type,
        "potencia_kva": pot_kva,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "prices_include_iva_tar": True,
    }

    if tariff_type == "simples":
        entry["energy"] = {"simples": round(tv_fv, 10)}
    else:
        if tvv is None:
            return None
        entry["energy"] = {
            "vazio": round(tvv, 10),
            "fora_vazio": round(tv_fv, 10),
        }

    entry["fixed_daily"] = {"power_contract": round(tf, 10)}
    entry["source_url"] = link_oferta or link_com or ""

    return entry


def _parse_date(val: str) -> str | None:
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'."""
    if not val:
        return None
    parts = val.split("/")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return None


def build_tarifarios(
    precos_rows: list[dict],
    cond_rows: list[dict],
    potencia: float,
    incluir_restricoes: bool = False,
) -> list[dict]:
    """Constrói lista de tarifários elegíveis para a potência dada."""
    cond_idx = build_cond_index(cond_rows)
    pot_str = str(potencia).replace(".", ",")

    # Ignorar comercializadores de último recurso (CUR*)
    skip_prefix = ("CUR", "TUR")

    entries: list[dict] = []
    seen_ids: set[str] = set()

    for row in precos_rows:
        com = row["COM"]
        if any(com.startswith(p) for p in skip_prefix):
            continue
        if row["Pot_Cont"] != pot_str:
            continue
        if row["Escalao"].strip():
            continue  # tarifas com escalões de consumo (gás, etc.)
        if row["TFGN"].strip():
            continue  # linhas de gás natural

        cod = row["COD_Proposta"]
        cond = cond_idx.get((com, cod))
        if cond is None:
            continue
        if not is_eligible(cond, incluir_restricoes):
            continue

        entry = build_tariff_entry(row, cond, potencia)
        if entry is None:
            continue

        entry_id = entry["id"]
        if entry_id in seen_ids:
            # ID duplicado: adiciona sufixo numérico
            n = 2
            while f"{entry_id}-{n}" in seen_ids:
                n += 1
            entry["id"] = f"{entry_id}-{n}"
        seen_ids.add(entry["id"])
        entries.append(entry)

    # Ordenar: bi-horário primeiro, depois simples; dentro de cada grupo por custo estimado
    entries.sort(key=lambda e: (
        0 if e["type"] == "bihorario" else 1,
        e["fixed_daily"]["power_contract"],
    ))

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--potencia", type=float, default=6.9,
                        help="Potência contratada em kVA (default: 6.9)")
    parser.add_argument("--incluir-restricoes", action="store_true",
                        help="Incluir planos com restrições (ex: só para associados X)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Ficheiro JSON de saída (default: config/tarifarios.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra resultado sem escrever ficheiro")
    args = parser.parse_args()

    print("1. A obter URL do ZIP de preços da ERSE...")
    try:
        zip_url = fetch_zip_url()
    except Exception as exc:
        print(f"ERRO ao aceder ao Settings.json: {exc}", file=sys.stderr)
        return 1

    print("2. A descarregar e extrair dados...")
    try:
        precos_rows, cond_rows = download_and_extract(zip_url)
    except Exception as exc:
        print(f"ERRO ao processar ZIP: {exc}", file=sys.stderr)
        return 1

    print(f"3. A filtrar tarifários para {args.potencia} kVA...")
    entries = build_tarifarios(precos_rows, cond_rows, args.potencia, args.incluir_restricoes)

    simples = sum(1 for e in entries if e["type"] == "simples")
    bihorario = sum(1 for e in entries if e["type"] == "bihorario")
    print(f"   {len(entries)} tarifários encontrados: {bihorario} bi-horários, {simples} simples")

    output = {
        "metadata": {
            "currency": "EUR",
            "country": "PT",
            "updated_at": date.today().isoformat(),
            "source": "ERSE simulador de preços",
            "source_url": "https://simuladorprecos.erse.pt/",
            "prices_include": "energia + TAR + IVA (preços totais estimados)",
            "potencia_kva": args.potencia,
        },
        "tariffs": entries,
    }

    result_json = json.dumps(output, ensure_ascii=False, indent=2)

    if args.dry_run:
        print("\n--- DRY RUN (primeiras 3 entradas) ---")
        preview = output.copy()
        preview["tariffs"] = entries[:3]
        print(json.dumps(preview, ensure_ascii=False, indent=2))
    else:
        args.output.write_text(result_json + "\n", encoding="utf-8")
        print(f"4. Ficheiro gravado: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
