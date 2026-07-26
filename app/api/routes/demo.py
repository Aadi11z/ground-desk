from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.interfaces.demo_product import demo_product_html

router = APIRouter(tags=["demo"])


@router.get("/", include_in_schema=False)
def product_demo() -> HTMLResponse:
    return HTMLResponse(demo_product_html())


@router.get("/app", include_in_schema=False)
def app_demo() -> HTMLResponse:
    return HTMLResponse(demo_product_html())
