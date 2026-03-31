"""Routes de upload de ficheiros XLSX E-REDES e PDF de faturas."""
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from src.web.services.ingestao_xlsx import ingerir_xlsx
from src.web.services.extrator_pdf import ingerir_pdf
from src.web.services.data_loader import save_custo_real

router = APIRouter()


def _consultar_tiagofelicia_bg(location_id: str, engine):
    """Background task: consulta tiagofelicia.pt e guarda resultado em comparacoes.

    Funcao sincrona (nao async def) — FastAPI corre automaticamente em thread pool.
    Se playwright nao estiver disponivel, loga aviso e retorna sem erro.
    Insere com ON CONFLICT DO NOTHING para idempotencia (UniqueConstraint uq_comparacao_loc_month).
    """
    import json
    import logging
    from datetime import datetime, timezone
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from src.db.schema import comparacoes, consumo_mensal
    from sqlalchemy import select

    logger = logging.getLogger("upload")

    try:
        from src.backend.tiagofelicia_compare import analyse_with_tiago
    except ImportError:
        logger.warning("playwright nao disponivel — consulta tiagofelicia.pt ignorada")
        return

    # Ler ultimo mes de consumo para este local
    with engine.connect() as conn:
        row = conn.execute(
            select(consumo_mensal)
            .where(consumo_mensal.c.location_id == location_id)
            .order_by(consumo_mensal.c.year_month.desc())
            .limit(1)
        ).fetchone()

    if not row:
        logger.warning(f"Sem dados de consumo para {location_id} — tiagofelicia ignorado")
        return

    try:
        result = analyse_with_tiago(
            total_kwh=row.total_kwh,
            vazio_kwh=row.vazio_kwh,
            fora_vazio_kwh=row.fora_vazio_kwh,
        )
        with engine.begin() as conn:
            stmt = sqlite_insert(comparacoes).values(
                location_id=location_id,
                year_month=row.year_month,
                top_3_json=json.dumps(result.get("top_3", []), ensure_ascii=False),
                current_supplier_result_json=json.dumps(
                    result.get("current_supplier_result"), ensure_ascii=False
                ),
                generated_at=result.get("generated_at", ""),
                cached_at=datetime.now(timezone.utc),
            ).on_conflict_do_nothing(
                index_elements=["location_id", "year_month"]
            )
            conn.execute(stmt)
        logger.info(f"tiagofelicia.pt consultado com sucesso para {location_id}")
    except Exception:
        logger.exception(f"Erro ao consultar tiagofelicia.pt para {location_id}")


@router.post("/upload/xlsx", response_class=HTMLResponse)
async def upload_xlsx(
    request: Request,
    background_tasks: BackgroundTasks,
    ficheiro: UploadFile = File(...),
):
    """Recebe XLSX E-REDES, ingere em SQLite, lanca tiagofelicia em background."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    # Guardar temporariamente (openpyxl requer ficheiro no disco)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        content = await ficheiro.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        resultado = ingerir_xlsx(tmp_path, ficheiro.filename, engine)
    finally:
        os.unlink(tmp_path)

    if resultado["erro"]:
        return templates.TemplateResponse(
            request=request,
            name="partials/upload_confirmacao.html",
            context={"erro": resultado["erro"], "resultado": None},
        )

    # Lancar consulta tiagofelicia em background (nao bloqueia resposta)
    background_tasks.add_task(_consultar_tiagofelicia_bg, resultado["location_id"], engine)

    return templates.TemplateResponse(
        request=request,
        name="partials/upload_confirmacao.html",
        context={"erro": None, "resultado": resultado},
    )


@router.post("/upload/pdf", response_class=HTMLResponse)
async def upload_pdf(
    request: Request,
    ficheiro: UploadFile = File(...),
):
    """Recebe PDF de fatura, extrai total pago e periodo, grava em custos_reais."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    content = await ficheiro.read()  # BytesIO — sem ficheiro temporario

    resultado = ingerir_pdf(content, engine)

    if resultado["erro"]:
        return templates.TemplateResponse(
            request=request,
            name="partials/upload_pdf_confirmacao.html",
            context={"erro": resultado["erro"], "resultado": None},
        )

    # Escrever tambem no custos_reais.json para que o dashboard mostre o valor.
    # O dashboard le de data/{local_id}/custos_reais.json, nao da tabela SQLite.
    project_root = request.app.state.project_root
    custos_path = project_root / "data" / resultado["location_id"] / "custos_reais.json"
    save_custo_real(custos_path, resultado["year_month"], resultado["custo_eur"])

    return templates.TemplateResponse(
        request=request,
        name="partials/upload_pdf_confirmacao.html",
        context={"erro": None, "resultado": resultado},
    )
