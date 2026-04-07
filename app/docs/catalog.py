from __future__ import annotations

from pathlib import Path


DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs"


def list_docs() -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        relative_path = path.relative_to(DOCS_ROOT).as_posix()
        title = relative_path.replace("/", " / ").replace(".md", "")
        documents.append({"path": relative_path, "title": title})
    return documents


def read_doc(relative_path: str) -> str:
    target = (DOCS_ROOT / relative_path).resolve()
    if not str(target).startswith(str(DOCS_ROOT.resolve())) or not target.exists():
        raise FileNotFoundError(relative_path)
    return target.read_text(encoding="utf-8")
