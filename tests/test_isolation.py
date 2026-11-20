"""Ізоляція тестів від робочої БД data/app.db."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def test_importing_app_main_does_not_create_workdir_db(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    work_db = root / "data" / "app.db"
    sentinel = tmp_path / "must-not-touch.db"

    # Якщо робочий файл існував до імпорту — запам’ятаємо mtime; інакше перевіримо відсутність.
    existed = work_db.exists()
    mtime_before = work_db.stat().st_mtime_ns if existed else None

    # Переімпорт модуля з чистого стану.
    sys.modules.pop("app.main", None)
    import app.main as main_mod

    importlib.reload(main_mod)

    if existed:
        assert work_db.stat().st_mtime_ns == mtime_before
    else:
        assert not work_db.exists()

    # Фабрика з tmp_path створює лише тимчасову БД після входу в lifespan (TestClient).
    application = main_mod.create_app(db_path=sentinel)
    assert not sentinel.exists()
    with TestClient(application) as client:
        assert sentinel.exists()
        assert client.get("/health").status_code == 200
