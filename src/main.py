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
from decimal import Decimal, ROUND_HALF_UP

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

@app.get("/dora/ticket-events")
def get_ticket_events():
    events = []
    for ticket in tickets_db.values():
        ticket_id = ticket["id"]

        # 1. Created event (always present)
        if ticket.get("created_at"):
            events.append({
                "ticket_id": ticket_id,
                "at": ticket["created_at"],
                "phase": "created",
                "priority": ticket["priority"],
                "state": "new"
            })

        # 2. Acknowledged event
        if ticket.get("acknowledged_at"):
            events.append({
                "ticket_id": ticket_id,
                "at": ticket["acknowledged_at"],
                "phase": "acknowledged",
                "priority": ticket["priority"],
                "state": "acknowledged"
            })

        # 3. Resolved event
        if ticket.get("resolved_at"):
            events.append({
                "ticket_id": ticket_id,
                "at": ticket["resolved_at"],
                "phase": "resolved",
                "priority": ticket["priority"],
                "state": "resolved"
            })

        # 4. Closed event
        if ticket.get("closed_at"):
            events.append({
                "ticket_id": ticket_id,
                "at": ticket["closed_at"],
                "phase": "closed",
                "priority": ticket["priority"],
                "state": "closed"
            })

    # Sort strictly by `at` ascending, then `ticket_id` ascending
    events.sort(key=lambda x: (x["at"], x["ticket_id"]))
    return events

def round_half_up(val: float, decimals: int = 6) -> float:
    d = Decimal(str(val))
    fmt = "0." + "0" * decimals if decimals > 0 else "0"
    return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def median(lst: list[int]) -> Optional[int]:
    if not lst:
        return None
    s = sorted(lst)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    else:
        return int(round_half_up((s[n // 2 - 1] + s[n // 2]) / 2.0, 0))

@app.post("/dora/metrics")
async def calculate_dora_metrics(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_json"}}, headers={"content-type": "application/json"})

    # Walidacja struktury okna
    window = body.get("window")
    events_raw = body.get("events")

    if not isinstance(window, dict) or "from" not in window or "to" not in window:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_window"}}, headers={"content-type": "application/json"})

    try:
        from_dt = parse_iso(window["from"])
        to_dt = parse_iso(window["to"])
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_window_format"}}, headers={"content-type": "application/json"})

    if to_dt <= from_dt:
        return JSONResponse(status_code=400, content={"error": {"code": "window_to_not_after_from"}}, headers={"content-type": "application/json"})

    if not isinstance(events_raw, list):
        return JSONResponse(status_code=400, content={"error": {"code": "events_not_array"}}, headers={"content-type": "application/json"})

    # R-05: Deduplikacja po event_id (pierwsze wystąpienie wygrywa)
    seen_event_ids = set()
    events = []
    for ev in events_raw:
        if not isinstance(ev, dict) or "event_id" not in ev or "type" not in ev or "at" not in ev:
            return JSONResponse(status_code=400, content={"error": {"code": "malformed_event"}}, headers={"content-type": "application/json"})
        eid = ev["event_id"]
        if eid in seen_event_ids:
            continue
        seen_event_ids.add(eid)
        try:
            ev_parsed = dict(ev)
            ev_parsed["_at_dt"] = parse_iso(ev["at"])
            events.append(ev_parsed)
        except Exception:
            return JSONResponse(status_code=400, content={"error": {"code": "malformed_timestamp"}}, headers={"content-type": "application/json"})

    # Indeksowanie zasobów logu
    commits_map = {} # sha -> commit_event
    reverts_count = 0

    for ev in events:
        if ev["type"] == "commit":
            sha = ev.get("sha")
            if not sha:
                return JSONResponse(status_code=400, content={"error": {"code": "commit_missing_sha"}}, headers={"content-type": "application/json"})
            if sha in commits_map:
                # Duplikat sha w logu (dobrze sformułowany log zakłada unikalność sha)
                pass
            commits_map[sha] = ev
            if ev.get("reverts") is not None:
                reverts_count += 1

    # Well-formedness checks
    for ev in events:
        if ev["type"] == "commit":
            reverts = ev.get("reverts")
            change_id = ev.get("change_id")
            if reverts is not None:
                if reverts not in commits_map:
                    return JSONResponse(status_code=400, content={"error": {"code": "reverts_sha_not_found"}}, headers={"content-type": "application/json"})
                if change_id is not None:
                    return JSONResponse(status_code=400, content={"error": {"code": "revert_has_change_id"}}, headers={"content-type": "application/json"})
            else:
                if change_id is None:
                    return JSONResponse(status_code=400, content={"error": {"code": "commit_missing_change_id"}}, headers={"content-type": "application/json"})
        elif ev["type"] == "deployment":
            for sha in ev.get("commits", []):
                if sha not in commits_map:
                    return JSONResponse(status_code=400, content={"error": {"code": "deployment_sha_not_found"}}, headers={"content-type": "application/json"})
        elif ev["type"] == "incident":
            for dep_id in ev.get("deployments", []):
                # Sprawdzenie czy deployment istnieje
                dep_exists = any(e["type"] == "deployment" and e.get("deployment_id") == dep_id for e in events)
                if not dep_exists:
                    return JSONResponse(status_code=400, content={"error": {"code": "incident_deployment_not_found"}}, headers={"content-type": "application/json"})

    # R-06: Rozwiązywanie change_id tranzytywnie dla revertów
    def resolve_change_id(sha: str) -> Optional[str]:
        visited = set()
        current_sha = sha
        while current_sha in commits_map:
            if current_sha in visited:
                break
            visited.add(current_sha)
            c = commits_map[current_sha]
            if c.get("change_id") is not None:
                return c["change_id"]
            rev = c.get("reverts")
            if rev is not None:
                current_sha = rev
            else:
                break
        return None

    # R-07: Pierwszy commit instant dla każdej zmiany (w całym logu)
    change_first_commit_dt = {}
    for sha, c in commits_map.items():
        ch_id = resolve_change_id(sha)
        if ch_id:
            at_dt = c["_at_dt"]
            if ch_id not in change_first_commit_dt or at_dt < change_first_commit_dt[ch_id]:
                change_first_commit_dt[ch_id] = at_dt

    # R-01 & R-02: Filtrowanie wdrożeń produkcyjnych w oknie [from, to)
    deployments = [e for e in events if e["type"] == "deployment"]
    prod_deployments_in_window = []
    for d in deployments:
        if d.get("environment") == "production":
            at_dt = d["_at_dt"]
            if from_dt <= at_dt < to_dt:
                prod_deployments_in_window.append(d)

    total_deployments = len(prod_deployments_in_window)
    successful_deployments_list = [d for d in prod_deployments_in_window if d.get("outcome") == "success"]
    failed_deployments_list = [d for d in prod_deployments_in_window if d.get("outcome") == "failure"]

    successful_deployments_count = len(successful_deployments_list)
    failed_deployments_count = len(failed_deployments_list)

    # R-10 (E4): Wdrożenia bez commitów
    deployments_without_commits = sum(1 for d in prod_deployments_in_window if not d.get("commits"))

    # R-09 (E3): Commity spoza main w wdrożeniach produkcyjnych
    prod_shas = set()
    for d in prod_deployments_in_window:
        for sha in d.get("commits", []):
            prod_shas.add(sha)
    commits_never_on_main = 0
    for sha in prod_shas:
        if sha in commits_map:
            if commits_map[sha].get("branch") != "main":
                commits_never_on_main += 1

    # R-08 (E1): Change lead time & Negative lead time pairs
    lead_time_seconds_list = []
    lead_time_pairs_count = 0
    negative_lead_time_pairs = 0

    # Mapowanie commit -> pierwsze udane wdrożenie w oknie (lub w ogóle)
    commit_first_success_dep = {}
    # Dla każdego commita szukamy najwcześniejszego udanego wdrożenia, które go zawierało
    for sha in commits_map:
        earliest_dep_at = None
        for d in successful_deployments_list:
            if sha in d.get("commits", []):
                if earliest_dep_at is None or d["_at_dt"] < earliest_dep_at:
                    earliest_dep_at = d["_at_dt"]
        if earliest_dep_at is not None:
            commit_first_success_dep[sha] = earliest_dep_at

    for d in successful_deployments_list:
        d_at = d["_at_dt"]
        for sha in d.get("commits", []):
            if sha in commits_map:
                c_at = commits_map[sha]["_at_dt"]
                # Para jest tworzona przy pierwszym udanym wdrożeniu tego commita
                # (sprawdzamy czy to d jest tym najwcześniejszym)
                if commit_first_success_dep.get(sha) == d_at:
                    lead_time_pairs_count += 1
                    diff = int((d_at - c_at).total_seconds())
                    if diff < 0:
                        negative_lead_time_pairs += 1
                        diff = 0 # R-03 clamp to zero
                    lead_time_seconds_list.append(diff)

    change_lead_time_seconds_p50 = median(lead_time_seconds_list)

    # R-12 & R-13 (E5 & E6): Incydenty i recovery time
    incidents = [e for e in events if e["type"] == "incident"]
    # Grupowanie incydentów po incident_id
    incident_events_map = {}
    for inc in incidents:
        inc_id = inc.get("incident_id")
        if inc_id not in incident_events_map:
            incident_events_map[inc_id] = []
        incident_events_map[inc_id].append(inc)

    recovered_failures = 0
    open_failures = 0
    recovery_times = []

    for d in failed_deployments_list:
        d_id = d.get("deployment_id")
        d_at = d["_at_dt"]

        # Szukamy incydentów pokrywających to wdrożenie
        covering_incidents = []
        for inc_id, inc_list in incident_events_map.items():
            # Sprawdzamy czy wdrożenie jest w deployments tego incydentu
            # oraz czy incydent ma fazę opened
            opened_ev = next((x for x in inc_list if x.get("phase") == "opened" and d_id in x.get("deployments", [])), None)
            if opened_ev:
                resolved_ev = next((x for x in inc_list if x.get("phase") == "resolved"), None)
                covering_incidents.append({
                    "incident_id": inc_id,
                    "opened_at": opened_ev["_at_dt"],
                    "resolved_at": resolved_ev["_at_dt"] if resolved_ev else None
                })

        if not covering_incidents:
            open_failures += 1
            continue

        # Wybór najwcześniej otwartego, przy remisie najniższy incident_id
        covering_incidents.sort(key=lambda x: (x["opened_at"], x["incident_id"]))
        chosen_cov = covering_incidents[0]

        if chosen_cov["resolved_at"] is not None:
            recovered_failures += 1
            rec_sec = int((chosen_cov["resolved_at"] - d_at).total_seconds())
            if rec_sec < 0:
                rec_sec = 0
            recovery_times.append(rec_sec)
        else:
            open_failures += 1

    failed_deployment_recovery_time_seconds_p50 = median(recovery_times)

    # R-13 (E6): Overlapping incident pairs
    # Interwał incydentu: [opened, resolved) lub dla nierozwiązanych [opened, to)
    incident_intervals = []
    for inc_id, inc_list in incident_events_map.items():
        opened_ev = next((x for x in inc_list if x.get("phase") == "opened"), None)
        if opened_ev:
            resolved_ev = next((x for x in inc_list if x.get("phase") == "resolved"), None)
            start = opened_ev["_at_dt"]
            end = resolved_ev["_at_dt"] if resolved_ev else to_dt
            incident_intervals.append((inc_id, start, end))

    overlapping_incident_pairs = 0
    n_incs = len(incident_intervals)
    for i in range(n_incs):
        for j in range(i + 1, n_incs):
            id_a, a_start, a_end = incident_intervals[i]
            id_b, b_start, b_end = incident_intervals[j]
            # Przecięcie interwałów: a_start < b_end and b_start < a_end
            if a_start < b_end and b_start < a_end:
                overlapping_incident_pairs += 1

    # R-14: Change fail rate
    change_fail_rate = round_half_up(failed_deployments_count / total_deployments, 6) if total_deployments > 0 else None

    # R-15: Deployment rework rate (unplanned == true and caused_by != null)
    rework_deployments_list = [d for d in prod_deployments_in_window if d.get("unplanned") is True and d.get("caused_by") is not None]
    rework_deployments_count = len(rework_deployments_list)
    deployment_rework_rate = round_half_up(rework_deployments_count / total_deployments, 6) if total_deployments > 0 else None

    # R-11: Deployment frequency per day
    window_seconds = (to_dt - from_dt).total_seconds()
    window_days = window_seconds / 86400.0
    deployment_frequency_per_day = round_half_up(total_deployments / window_days, 6) if window_days > 0 else 0.0

    # Ground truth (R-16, R-17)
    # Unikalne zmiany dostarczone w oknie (przez udane wdrożenia)
    delivered_changes = set()
    change_first_successful_dep_in_window = {}

    for d in successful_deployments_list:
        d_at = d["_at_dt"]
        for sha in d.get("commits", []):
            ch_id = resolve_change_id(sha)
            if ch_id:
                delivered_changes.add(ch_id)
                if ch_id not in change_first_successful_dep_in_window or d_at < change_first_successful_dep_in_window[ch_id]:
                    change_first_successful_dep_in_window[ch_id] = d_at

    changes_delivered_count = len(delivered_changes)

    true_lead_times = []
    for ch_id in delivered_changes:
        if ch_id in change_first_commit_dt and ch_id in change_first_successful_dep_in_window:
            first_commit = change_first_commit_dt[ch_id]
            first_success = change_first_successful_dep_in_window[ch_id]
            diff = int((first_success - first_commit).total_seconds())
            if diff < 0:
                diff = 0
            true_lead_times.append(diff)

    true_change_lead_time_seconds_p50 = median(true_lead_times)

    response_data = {
        "spec_version": "1.0.0",
        "window": {
            "from": format_iso(from_dt),
            "to": format_iso(to_dt)
        },
        "deployment_frequency_per_day": deployment_frequency_per_day,
        "change_lead_time_seconds_p50": change_lead_time_seconds_p50,
        "failed_deployment_recovery_time_seconds_p50": failed_deployment_recovery_time_seconds_p50,
        "change_fail_rate": change_fail_rate,
        "deployment_rework_rate": deployment_rework_rate,
        "counts": {
            "deployments": total_deployments,
            "successful_deployments": successful_deployments_count,
            "failed_deployments": failed_deployments_count,
            "recovered_failures": recovered_failures,
            "open_failures": open_failures,
            "rework_deployments": rework_deployments_count,
            "lead_time_pairs": lead_time_pairs_count,
            "changes": len(change_first_commit_dt)
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_time_pairs,
            "deployments_without_commits": deployments_without_commits,
            "commits_never_on_main": commits_never_on_main,
            "revert_chains_collapsed": reverts_count,
            "overlapping_incident_pairs": overlapping_incident_pairs
        },
        "ground_truth": {
            "changes_delivered": changes_delivered_count,
            "true_change_lead_time_seconds_p50": true_change_lead_time_seconds_p50
        }
    }

    return response_data