---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---

<!-- ai-generated: 0% - by hand -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 tickets run on a continuous wall-clock schedule 24/7 without pausing.

**Rejected alternative:** Pausing P1 tickets outside business hours until the next opening time.

**Reason:** P1 indicates an organization-wide halt; waiting until business hours causes unacceptable operational losses.

**Service owner:** Incident Management Process Owner responsible for critical service continuity.

**Customer outcome:** Critical incidents receive immediate, round-the-clock intervention and rapid resolution.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are permanently immutable and cannot be reopened under any circumstance.

**Rejected alternative:** Allowing reporters to reopen closed tickets within a 7-day post-closure window.

**Reason:** Preserves audit trail integrity and prevents skewing historical operational SLA metrics.

**Service owner:** Service Desk Lead ensuring compliance, accurate reporting, and clean record-keeping.

**Customer outcome:** Requesters receive traceable resolution history; recurring issues trigger linked tickets cleanly.

## C3 - VIP reporters and the priority matrix

**Decision:** Tickets from VIP reporters are escalated to at least P2 regardless of the matrix.

**Rejected alternative:** Deriving priority purely from the impact and urgency matrix ignoring reporter status.

**Reason:** Executive and critical roles carry outsized organizational risk requiring prioritized desk attention.

**Service owner:** Head of Customer Support maintaining executive satisfaction and enterprise escalation SLAs.

**Customer outcome:** Key personnel receive expedited triage avoiding administrative stalls on cosmetic issues.