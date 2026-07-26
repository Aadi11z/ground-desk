from fastapi import APIRouter
import json
from app.core.config import settings

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/summary")
def benchmark_summary():
    """Return public summaries of reviewed retrieval benchmark artifacts."""
    reports_dir = settings.benchmark_report_path.parent
    report_paths = sorted(reports_dir.glob("*.json")) if reports_dir.exists() else []
    if not report_paths:
        return {"available": False}
    summaries = []
    for path in report_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        summaries.append(
            {
                "created_at": report.get("created_at"),
                "dataset": report.get("dataset", {}),
                "index": report.get("index", {}),
                "runs": [
                    {
                        "strategy": run.get("strategy"),
                        "num_queries": run.get("num_queries"),
                        "metrics": run.get("metrics", {}),
                    }
                    for run in report.get("runs", [])
                ],
            }
        )
    return {"available": bool(summaries), "reports": summaries}
