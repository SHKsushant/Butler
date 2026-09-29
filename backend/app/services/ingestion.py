"""
Parses an uploaded CSV or JSON export into normalized Ticket rows.
Deliberately tolerant of missing optional columns (is_vip, sender_name,
timestamp) since real exports are messy - only sender/subject/body are
treated as required.
"""
import io
import json
from datetime import datetime
from typing import List

import pandas as pd

from app.models import Ticket

REQUIRED_COLUMNS = {"sender_email", "subject", "body"}

# Accept a couple of common aliases so a slightly different export schema
# doesn't just fail silently.
COLUMN_ALIASES = {
    "sender": "sender_email",
    "email": "sender_email",
    "from": "sender_email",
    "name": "sender_name",
    "message": "body",
    "text": "body",
    "created_at": "timestamp",
    "date": "timestamp",
    "vip": "is_vip",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: COLUMN_ALIASES.get(c, c) for c in df.columns})
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Upload is missing required column(s): {', '.join(sorted(missing))}. "
            f"Required: {', '.join(sorted(REQUIRED_COLUMNS))}"
        )
    return df


def _parse_timestamp(value) -> datetime:
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None


def parse_upload(filename: str, raw_bytes: bytes) -> List[Ticket]:
    if filename.lower().endswith(".json"):
        records = json.loads(raw_bytes.decode("utf-8"))
        df = pd.DataFrame(records)
    else:
        df = pd.read_csv(io.BytesIO(raw_bytes))

    df = _normalize_columns(df)

    tickets: List[Ticket] = []
    for _, row in df.iterrows():
        is_vip_raw = row.get("is_vip", False)
        is_vip = str(is_vip_raw).strip().lower() in {"true", "1", "yes"}

        tickets.append(
            Ticket(
                sender_email=str(row["sender_email"]),
                sender_name=str(row.get("sender_name", "") or "") or None,
                subject=str(row["subject"]),
                body=str(row["body"]),
                timestamp=_parse_timestamp(row.get("timestamp")),
                is_vip=is_vip,
                status="new",
            )
        )
    return tickets
