from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.docs.catalog import list_docs, read_doc
from app.services.bootstrap_service import BootstrapService

settings = get_settings()
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        BootstrapService().seed_default_users(db)
    except OperationalError:
        db.rollback()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", response_model=dict)
def root() -> dict[str, str]:
    return {
        "message": "NRI Plot Sentinel API is running",
        "docs": "/docs",
        "project_docs": "/project-docs",
    }


@app.get("/project-docs", response_class=HTMLResponse)
def project_docs() -> HTMLResponse:
    rendered = templates.get_template("project_docs.html").render(
        title=settings.app_name,
        docs=list_docs(),
    )
    return HTMLResponse(rendered)


@app.get("/project-docs/content/{doc_path:path}", response_class=HTMLResponse)
def project_doc_content(doc_path: str) -> HTMLResponse:
    content = read_doc(doc_path)
    safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"<html><body><pre>{safe_content}</pre></body></html>"
    return HTMLResponse(html)
