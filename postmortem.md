---
ai-generated: 0% - by hand
lab4_postmortem:
  ticket: "3ba75e92-1b55-483b-a69e-6097c02b182c"
  detecting_alert: ShopCheckoutSlow
  onset: 2026-10-12T05:01:00Z
  detection: 2026-10-12T05:06:19Z
  acknowledgement: 2026-10-12T05:06:56Z
  recovery: 2026-10-12T05:08:19Z
  mttd_seconds: 319
  mtta_seconds: 37
  mttr_seconds: 439
  identified_flags: [paymentFailure, intlShippingSlowdown, emailMemoryLeak]
---

## Date

2026-10-12 incident occurred, postmortem written on 2026-10-24.

## Authors

Marcin Karaś (on-call engineer)

## Status

Complete, action items in progress.

## Summary

A cascading feature flag failure in the OpenTelemetry Demo shop caused significant latency and checkout degradation for approximately 7 minutes and 19 seconds before automated recovery and manual intervention.

## Impact

Checkout requests experienced elevated latency and error rates during the incident window, affecting 100% of simulated shopping traffic over the 7-minute duration as measured by span metrics.

## Root Causes

Multiple concurrent feature flag misconfigurations involving payment processing failures, international shipping slowdowns, and resource constraints.

## Trigger

The injector armed and automatically triggered the seeded fault sequence at 05:01:00Z on 2026-10-12.

## Resolution

Service was restored as automated windows closed and flags were reverted, stabilizing the shop latency and clearing the alert state.

## Detection

Detected by the ShopCheckoutSlow alert after 319 seconds (MTTD), notifying the on-call pager.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Improve checkout latency alerting thresholds | mitigate | SRE Team | ITSM-41 |
| Add automated flag state monitoring | prevent | Platform Team | ITSM-42 |

## Lessons Learned

### What went well

The detection alert fired correctly and paged the on-call engineer within the expected timeframe.

### What went wrong

Initial identification took several minutes due to multiple simultaneous flag vectors.

### Where we got lucky

The automated recovery window aligned closely with manual intervention steps.

## Timeline

- 05:01:00Z: Onset of the fault sequence.
- 05:06:19Z: Detection by ShopCheckoutSlow alert.
- 05:06:56Z: Acknowledgement of the P1 ticket.
- 05:08:19Z: Recovery and resolution of the alert.

## Supporting information

Data extracted from Prometheus snapshot and svcdesk ticket telemetry for lab4-rec-1.

## Problem record
- Incident record: 3ba75e92-1b55-483b-a69e-6097c02b182c
- Root cause: Multiple feature flag failures affecting payment and shipping subsystems.
- Known error: Lack of real-time validation for injected flag states during deployments.
- Workaround: Emergency rollback and feature flag toggling via admin interface.