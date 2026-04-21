from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4


def _project_root() -> Path:
    # app/core/image_store.py -> app/core -> app -> project root
    return Path(__file__).resolve().parents[2]


def ensure_image_dir(kind: str) -> Path:
    base = _project_root() / "data" / "images" / kind
    base.mkdir(parents=True, exist_ok=True)
    return base


def store_image(src_path: str, kind: str) -> str:
    """
    Copy image into project-local folder and return relative path (POSIX style).
    kind: "services" | "service_types" (or other future buckets)
    """
    if not src_path:
        return ""

    src = Path(src_path)
    if not src.exists() or not src.is_file():
        return ""

    dst_dir = ensure_image_dir(kind)
    ext = src.suffix.lower() or ".png"
    filename = f"{uuid4().hex}{ext}"
    dst = dst_dir / filename
    shutil.copy2(src, dst)

    rel = dst.relative_to(_project_root())
    return rel.as_posix()


def resolve_image_path(rel_path: str) -> str:
    if not rel_path:
        return ""
    p = Path(rel_path)
    if p.is_absolute():
        return str(p)
    return str((_project_root() / p).resolve())


def is_image_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

