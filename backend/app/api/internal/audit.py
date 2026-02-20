import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/audit/logs")
async def get_audit_logs(
    request: Request,
    limit: int = Query(default=50, le=500),
    risk_level: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    audit_required: Optional[bool] = Query(default=None),
):
    """
    Return the latest audit log entries from the JSONL file, newest first.
    Supports filtering by risk_level, department, audit_required.
    """
    audit_logger = request.app.state.audit_logger
    log_path = Path(audit_logger._path)

    if not log_path.exists():
        return {"entries": [], "total": 0, "filtered": 0}

    # Read all lines — JSONL is append-only so read tail efficiently
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Apply filters
        if risk_level and entry.get("risk_level") != risk_level:
            continue
        if department and entry.get("department") != department:
            continue
        if audit_required is not None and entry.get("audit_required") != audit_required:
            continue

        entries.append(entry)
        if len(entries) >= limit:
            break

    return {
        "entries": entries,
        "total": len(lines),
        "filtered": len(entries),
        "log_path": str(log_path),
    }
