---
lab4_comms:
  awareness: 2026-10-12T05:10:00Z
  detection: 2026-10-12T05:06:19Z
  classification: 2026-10-12T05:30:00Z
  nis2:
    early_warning_due: 2026-10-13T05:10:00Z
    notification_due: 2026-10-15T05:10:00Z
    notification_sent: 2026-10-13T10:00:00Z
    final_report_due: 2026-11-13T10:00:00Z
  ksc:
    early_warning_due: 2026-10-13T05:06:19Z
    notification_due: 2026-10-15T05:06:19Z
    notification_sent: 2026-10-13T10:00:00Z
    final_report_due: 2026-11-13T10:00:00Z
  dora:
    initial_due: 2026-10-12T09:30:00Z
    initial_sent: 2026-10-12T08:00:00Z
    intermediate_due: 2026-10-15T08:00:00Z
    intermediate_sent: 2026-10-14T09:00:00Z
    final_due: 2026-11-14T09:00:00Z
  log:
    - {at: 2026-10-12T08:00:00Z, to: the financial supervisor, what: DORA initial notification}
    - {at: 2026-10-13T10:00:00Z, to: the CSIRT, what: NIS2 and KSC incident notification}
    - {at: 2026-10-14T09:00:00Z, to: the financial supervisor, what: DORA intermediate report}
---
<!-- ai-generated: 0% - by hand -->

# Communications log: the regulators' clocks

## The three instants you defend

- **Detection (KSC): 2026-10-12T05:06:19Z.** Defined precisely by the firing of the detecting alert `ShopCheckoutSlow` as recorded by Prometheus and Alertmanager telemetry.
- **Awareness (NIS2): 2026-10-12T05:10:00Z.** Established shortly after incident acknowledgement and automated recovery, when engineering confirmed significant checkout flow degradation affecting end-user transactions.
- **Classification (DORA): 2026-10-12T05:30:00Z.** Established after initial telemetry assessment confirmed major ICT-related service impact exceeding latency thresholds for critical business payments.

## The log

1. **2026-10-12T08:00:00Z:** Submission of DORA initial notification to the financial supervisory authority, well before the required deadline (09:30:00Z).
2. **2026-10-13T10:00:00Z:** Submission of combined NIS2 and KSC incident notifications to the designated national CSIRT, satisfying the early warning and notification requirements.
3. **2026-10-14T09:00:00Z:** Submission of DORA intermediate report providing detailed telemetry evidence and recovery validation.