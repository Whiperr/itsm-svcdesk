---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.95
      threshold_seconds: 0.24
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.24"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.05, minutes: 2160}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 0% - by hand -->

# SLO for `GET /kb/search`

## Availability
The availability SLI measures successful requests to `/kb/search` excluding 5xx errors, set to an objective of 0.99 over a 30-day window (432 minutes error budget).

## Latency
The latency SLI measures requests completing at or below 0.24 seconds, aligned with our histogram bucket boundary, with an objective of 0.95 (2160 minutes error budget).

## Alerts
| alert | SLI | burn rate | long / short window | budget spent when it fires | severity |
|---|---|---|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | 2% | P1 (page) |
| KbSearchErrorsBurnSlow | availability | 6 | 6h / 30m | 5% | P2 (chat) |

## Buckets
Our ladder resolves the measured p99 within a narrow bucket satisfying resolution rules.
