import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)

USAGE_TABLE = "usage_logs"


def log_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    document_id: Optional[str] = None,
) -> None:
    try:
        db = get_supabase_client()
        db.table(USAGE_TABLE).insert({
            "document_id": document_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log usage: %s", e)


def _aggregate(rows: list) -> List[dict]:
    today = date.today().isoformat()
    one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
    aggregated: dict[str, dict] = {}
    for row in rows:
        model = row["model"]
        if model not in aggregated:
            aggregated[model] = {
                "model": model,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_requests": 0,
                "today_requests": 0,
                "last_minute_requests": 0,
            }
        aggregated[model]["total_input_tokens"] += row["input_tokens"]
        aggregated[model]["total_output_tokens"] += row["output_tokens"]
        aggregated[model]["total_requests"] += 1
        created_str = str(row.get("created_at", ""))
        if created_str[:10] == today:
            aggregated[model]["today_requests"] += 1
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created_dt > one_minute_ago:
                aggregated[model]["last_minute_requests"] += 1
        except Exception:
            pass
    return list(aggregated.values())


def get_overall_usage() -> List[dict]:
    try:
        db = get_supabase_client()
        result = db.table(USAGE_TABLE).select("model, input_tokens, output_tokens, created_at").execute()
        return _aggregate(result.data or [])
    except Exception as e:
        logger.warning("Failed to fetch overall usage: %s", e)
        return []


def get_document_usage(document_id: str) -> List[dict]:
    try:
        db = get_supabase_client()
        result = (
            db.table(USAGE_TABLE)
            .select("model, input_tokens, output_tokens, created_at")
            .eq("document_id", document_id)
            .execute()
        )
        return _aggregate(result.data or [])
    except Exception as e:
        logger.warning("Failed to fetch document usage: %s", e)
        return []
