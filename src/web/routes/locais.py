"""Routes de gestao de locais."""
import re
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from src.web.services.locais_service import (
    create_local,
    get_all_locais,
    get_local_by_id,
    update_fornecedor,
)

router = APIRouter()


def _slugify(name: str) -> str:
    """Gera slug a partir do nome (ex: 'Escritorio Porto' -> 'escritorio-porto')."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@router.get("/locais", response_class=HTMLResponse)
async def locais_page(request: Request):
    """Pagina de gestao de locais: formulario + lista."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    all_locais = get_all_locais(engine)
    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={"locais": all_locais, "erro": None, "sucesso": None},
    )


@router.post("/locais", response_class=HTMLResponse)
async def criar_local(
    request: Request,
    name: str = Form(...),
    cpe: str = Form(...),
):
    """Cria novo local via formulario HTMX."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    local_id = _slugify(name)
    if not local_id:
        all_locais = get_all_locais(engine)
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": "Nome invalido.", "sucesso": None},
        )

    try:
        novo = create_local(local_id, name, cpe.strip(), engine)
    except ValueError as e:
        all_locais = get_all_locais(engine)
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": str(e), "sucesso": None},
        )

    all_locais = get_all_locais(engine)
    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={
            "locais": all_locais,
            "erro": None,
            "sucesso": f"Local '{novo['name']}' criado com sucesso.",
        },
    )


@router.post("/locais/{local_id}/fornecedor", response_class=HTMLResponse)
async def editar_fornecedor(
    request: Request,
    local_id: str,
    supplier: str = Form(...),
    plan_contains: str = Form(""),
):
    """Actualiza fornecedor actual de um local."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    result = update_fornecedor(local_id, supplier.strip(), plan_contains.strip() or None, engine)
    all_locais = get_all_locais(engine)

    if result is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": f"Local '{local_id}' nao encontrado.", "sucesso": None},
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={
            "locais": all_locais,
            "erro": None,
            "sucesso": f"Fornecedor de '{result['name']}' actualizado para '{supplier}'.",
        },
    )
