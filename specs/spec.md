<!--
ai-generated: 10% outline and draft assisted
-->

# Specification: ITSM Service Desk (svcdesk)

## Overview
This document specifies the behavior, data models, and constraints for the `svcdesk` service.
The service implements ticket handling, state transitions, priority calculation, and SLA tracking.

## Ticket Data Model
Each ticket managed by the service must conform to the following schema:
- `id`: Unique identifier (UUID or sequential integer string).
- `title`: Short summary string describing the issue (non-empty).
- `description`: Detailed description of the problem.
- `priority`: Derived priority level (`P1`, `P2`, `P3`, `P4`).
- `urgency`: Input parameter (`high`, `medium`, `low`).
- `impact`: Input parameter (`high`, `medium`, `low`).
- `is_vip`: Boolean flag indicating whether the reporter has VIP status.
- `status`: Lifecycle state (`new`, `open`, `pending`, `resolved`, `closed`).
- `created_at`: ISO 8601 UTC timestamp of creation.
- `updated_at`: ISO 8601 UTC timestamp of last modification.
- `sla_breach_at`: Projected or evaluated SLA expiration timestamp.

## Endpoints
- `GET /health`: Returns HTTP 200 with `{"status": "ok"}` within probe window.
- `POST /tickets`: Validates input payload, calculates priority, and creates a ticket.
- `GET /tickets/{id}`: Retrieves the current state and SLA status of a ticket.
- `PATCH /tickets/{id}`: Applies state machine transitions (open, resolve, close, reopen).
- `POST /test/clock`: Modifies virtual time for SLA vector and breach verification.

## Conflict Resolution Contracts
- C1 (SLA Clock for P1): Clarifies whether the clock runs continuously or pauses on pending.
- C2 (Ticket Reopening): Defines behavior of reopened tickets relative to closed status.
- C3 (VIP Matrix): Determines priority escalation overrides for VIP reporters.