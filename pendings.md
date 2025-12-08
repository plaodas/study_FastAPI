# リファクタ案

* ModuleNotFoundError: No module named 'app' 対応
docker compose exec backend sh -c "export PYTHONPATH=/app; pytest -q /app/tests -q"でPYTHONPATH=/appをデフォルトで設定したい
