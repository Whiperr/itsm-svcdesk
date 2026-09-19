# ai-generated: 90% - AI drafted implementation, adjusted SLA and tie rules
import os
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

WARSAW_TZ = ZoneInfo("Europe/Warsaw")
UTC_TZ = timezone.utc

tickets_db: dict[str, dict[str, Any]] = {}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "validation_error", "message": str(exc)}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "not_found", "message": "Resource not found"}},
    )


def parse_iso(dt_str: str) -> datetime:
    val = dt_str.strip()
    if val.endswith("Z") or val.endswith("z"):
        val = val[:-1] + "+00:00"
    dt = datetime.fromisoformat(val)
    if dt.tzinfo is None:
        raise ValueError("Timezone offset required")
    return dt.astimezone(UTC_TZ)


def get_current_time(x_test_clock: Optional[str] = None) -> datetime:
    test_clock_enabled = os.getenv("SVCDESK_TEST_CLOCK", "").lower() in ("1", "true")
    if test_clock_enabled and x_test_clock:
        try:
            return parse_iso(x_test_clock)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "invalid_clock", "message": "Malformed X-Test-Clock header"}},
            )
    return datetime.now(UTC_TZ)


def format_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(UTC_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    matrix = {
        (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
        (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
        (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
    }
    prio = matrix.get((impact, urgency), "P4")
    if vip and prio in ("P3", "P4"):
        prio = "P2"
    return prio


def add_business_seconds(start_dt: datetime, target_seconds: int) -> datetime:
    current_local = start_dt.astimezone(WARSAW_TZ)
    remaining_seconds = target_seconds

    while remaining_seconds > 0:
        weekday = current_local.weekday()
        if weekday >= 5:
            days_to_add = 7 - weekday
            next_day = current_local.date() + timedelta(days=days_to_add)
            current_local = datetime.combine(next_day, time(8, 0, 0), tzinfo=WARSAW_TZ)
            continue

        day_start = datetime.combine(current_local.date(), time(8, 0, 0), tzinfo=WARSAW_TZ)
        day_end = datetime.combine(current_local.date(), time(16, 0, 0), tzinfo=WARSAW_TZ)

        if current_local < day_start:
            current_local = day_start

        if current_local >= day_end:
            next_day = current_local.date() + timedelta(days=1)
            current_local = datetime.combine(next_day, time(8, 0, 0), tzinfo=WARSAW_TZ)
            continue

        available_seconds = int((day_end - current_local).total_seconds())
        if remaining_seconds <= available_seconds:
            current_local = current_local + timedelta(seconds=remaining_seconds)
            remaining_seconds = 0
        else:
            remaining_seconds -= available_seconds
            next_day = current_local.date() + timedelta(days=1)
            current_local = datetime.combine(next_day, time(8, 0, 0), tzinfo=WARSAW_TZ)

    return current_local.astimezone(UTC_TZ)


def calculate_sla(created_at: datetime, priority: str) -> tuple[datetime, datetime]:
    sla_targets = {
        "P1": (15 * 60, 4 * 3600),
        "P2": (3600, 8 * 3600),
        "P3": (4 * 3600, 24 * 3600),
        "P4": (8 * 3600, 72 * 3600),
    }
    ack_sec, res_sec = sla_targets[priority]

    if priority == "P1":
        ack_due = created_at + timedelta(seconds=ack_sec)
        res_due = created_at + timedelta(seconds=res_sec)
    else:
        ack_due = add_business_seconds(created_at, ack_sec)
        res_due = add_business_seconds(created_at, res_sec)

    return ack_due, res_due


def is_in_business_hours(dt: datetime) -> bool:
    local_dt = dt.astimezone(WARSAW_TZ)
    if local_dt.weekday() >= 5:
        return False
    return time(8, 0, 0) <= local_dt.time() < time(16, 0, 0)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(request: Request, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    now = get_current_time(x_test_clock)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_json"}})

    impact = body.get("impact")
    urgency = body.get("urgency")
    if not isinstance(impact, int) or isinstance(impact, bool) or impact not in (1, 2, 3):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_impact", "message": "impact must be 1, 2, or 3"}})
    if not isinstance(urgency, int) or isinstance(urgency, bool) or urgency not in (1, 2, 3):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_urgency", "message": "urgency must be 1, 2, or 3"}})

    title = body.get("title")
    if not title or not isinstance(title, str) or len(title) > 200:
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_title", "message": "title invalid"}})

    reporter_raw = body.get("reporter")
    if not isinstance(reporter_raw, dict) or not reporter_raw.get("name") or not isinstance(reporter_raw.get("name"), str):
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_reporter", "message": "reporter.name required"}})

    vip = bool(reporter_raw.get("vip", False))
    priority = compute_priority(impact, urgency, vip)
    ack_due_at, resolve_due_at = calculate_sla(now, priority)

    ticket_id = str(uuid.uuid4())
    ticket = {
        "id": ticket_id,
        "title": title,
        "description": body.get("description", ""),
        "reporter": {
            "name": reporter_raw["name"],
            "email": reporter_raw.get("email"),
            "vip": vip,
        },
        "impact": impact,
        "urgency": urgency,
        "priority": priority,
        "state": "new",
        "created_at": format_iso(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": body.get("related_to"),
        "sla": {
            "ack_due_at": format_iso(ack_due_at),
            "resolve_due_at": format_iso(resolve_due_at),
        },
        "_ack_due_dt": ack_due_at,
        "_resolve_due_dt": resolve_due_at,
    }
    tickets_db[ticket_id] = ticket

    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.get("/tickets")
def list_tickets(state: Optional[str] = None, priority: Optional[str] = None):
    results = []
    for t in tickets_db.values():
        if state and t["state"] != state:
            continue
        if priority and t["priority"] != priority:
            continue
        results.append({k: v for k, v in t.items() if not k.startswith("_")})
    return results


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Ticket not found"}})
    ticket = tickets_db[ticket_id]
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.get("/tickets/{ticket_id}/sla")
def get_ticket_sla(ticket_id: str, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "Ticket not found"}})

    now = get_current_time(x_test_clock)
    ticket = tickets_db[ticket_id]

    ack_due_dt = ticket["_ack_due_dt"]
    resolve_due_dt = ticket["_resolve_due_dt"]

    if ticket["acknowledged_at"]:
        ack_time = parse_iso(ticket["acknowledged_at"])
        ack_breached = ack_time > ack_due_dt
    else:
        ack_breached = now > ack_due_dt

    if ticket["resolved_at"]:
        res_time = parse_iso(ticket["resolved_at"])
        resolve_breached = res_time > resolve_due_dt
    else:
        resolve_breached = now > resolve_due_dt

    is_open = ticket["state"] not in ("resolved", "closed")
    is_business_clock = ticket["priority"] != "P1"
    paused = is_open and is_business_clock and (not is_in_business_hours(now))

    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }


@app.post("/tickets/{ticket_id}/ack")
def ack_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    now = get_current_time(x_test_clock)
    ticket = tickets_db[ticket_id]
    if ticket["state"] != "new":
        return JSONResponse(status_code=409, content={"error": {"code": "invalid_transition"}})
    ticket["state"] = "acknowledged"
    ticket["acknowledged_at"] = format_iso(now)
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.post("/tickets/{ticket_id}/start")
def start_ticket(ticket_id: str):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    ticket = tickets_db[ticket_id]
    if ticket["state"] != "acknowledged":
        return JSONResponse(status_code=409, content={"error": {"code": "invalid_transition"}})
    ticket["state"] = "in_progress"
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    now = get_current_time(x_test_clock)
    ticket = tickets_db[ticket_id]
    if ticket["state"] != "in_progress":
        return JSONResponse(status_code=409, content={"error": {"code": "invalid_transition"}})
    ticket["state"] = "resolved"
    ticket["resolved_at"] = format_iso(now)
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    now = get_current_time(x_test_clock)
    ticket = tickets_db[ticket_id]
    if ticket["state"] != "resolved":
        return JSONResponse(status_code=409, content={"error": {"code": "invalid_transition"}})
    ticket["state"] = "closed"
    ticket["closed_at"] = format_iso(now)
    return {k: v for k, v in ticket.items() if not k.startswith("_")}


@app.post("/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: str, x_test_clock: Optional[str] = Header(None, alias="X-Test-Clock")):
    if ticket_id not in tickets_db:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found"}})
    now = get_current_time(x_test_clock)
    ticket = tickets_db[ticket_id]

    if ticket["state"] == "closed":
        return JSONResponse(status_code=409, content={"error": {"code": "immutable_ticket"}})

    if ticket["state"] != "resolved":
        return JSONResponse(status_code=409, content={"error": {"code": "invalid_transition"}})

    resolved_dt = parse_iso(ticket["resolved_at"])
    if now > resolved_dt + timedelta(days=7):
        return JSONResponse(status_code=409, content={"error": {"code": "reopen_window_expired"}})

    ticket["state"] = "in_progress"
    ticket["resolved_at"] = None
    ticket["closed_at"] = None
    return {k: v for k, v in ticket.items() if not k.startswith("_")}