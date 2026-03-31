"""Routes de gestao de locais."""
import re
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from src.web.services.locais_service import (
    create_local,
    delete_local,
    get_all_locais,
    get_local_by_id,
    update_fornecedor,
    update_local,
)

router = APIRouter()


def _slugify(name: str) -> str:
    """Gera slug a partir do nome (ex: 'Escritorio Porto' -> 'escritorio-porto')."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@router.get("/locais", response_class=HTMLResponse)
async def locais_page(request: Request):
    """Pagina de gestao de locais. Full page ou partial (HTMX)."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    all_locais = get_all_locais(engine)
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "partials/locais_form.html" if is_htmx else "locais.html"
    return templates.TemplateResponse(
        request=request,
        name=template,
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


@router.get("/locais/{local_id}/editar", response_class=HTMLResponse)
async def editar_local_form(request: Request, local_id: str):
    """Mostra a pagina de locais com o local em modo de edicao."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine
    all_locais = get_all_locais(engine)
    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={"locais": all_locais, "erro": None, "sucesso": None, "editing_id": local_id},
    )


@router.post("/locais/{local_id}", response_class=HTMLResponse)
async def guardar_local(
    request: Request,
    local_id: str,
    name: str = Form(...),
    cpe: str = Form(...),
):
    """Actualiza nome e CPE de um local existente."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    try:
        result = update_local(local_id, name.strip(), cpe.strip(), engine)
    except ValueError as e:
        all_locais = get_all_locais(engine)
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": str(e), "sucesso": None, "editing_id": local_id},
        )

    if result is None:
        all_locais = get_all_locais(engine)
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": f"Local '{local_id}' nao encontrado.", "sucesso": None},
        )

    all_locais = get_all_locais(engine)
    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={
            "locais": all_locais,
            "erro": None,
            "sucesso": f"Local '{result['name']}' actualizado com sucesso.",
        },
    )


@router.post("/locais/{local_id}/apagar", response_class=HTMLResponse)
async def apagar_local(request: Request, local_id: str):
    """Apaga um local."""
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    apagado = delete_local(local_id, engine)
    all_locais = get_all_locais(engine)

    if not apagado:
        return templates.TemplateResponse(
            request=request,
            name="partials/locais_form.html",
            context={"locais": all_locais, "erro": f"Local '{local_id}' nao encontrado.", "sucesso": None},
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/locais_form.html",
        context={"locais": all_locais, "erro": None, "sucesso": "Local apagado com sucesso."},
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
