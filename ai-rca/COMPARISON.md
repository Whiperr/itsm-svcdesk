<!-- ai-generated: 0% - by hand -->
# Comparison of AI Investigators (Stretch 1)

This document provides a comparative evaluation between the primary investigator (Qwen3 4B via local OpenAI agent loop) and the secondary investigator (Gemini 3.8 Flash via Gemini CLI 0.61.0).

## Investigation Strategy and Workflow

Both models were tasked with diagnosing the P1 checkout latency incident paged at 05:06:19Z on 2026-10-12.
- **Investigator 1 (Qwen3 4B):** Attempted multi-step PromQL metric inspection, querying span metrics across services. It noticed significant traffic increases on `POST /api/checkout` and latency growth on `ProductCatalogService/GetProduct` and `CheckoutService/PlaceOrder`. However, it struggled with PromQL syntax when attempting `by (span_name)` clauses directly without aggregation operators, resulting in multiple step errors.
- **Investigator 2 (Gemini 3.8 Flash):** Processed tool outputs in a single comprehensive pass. Instead of inspecting bottleneck spans sequentially, it hypothesized cascading failures across multiple peripheral microservices including payment charge failures, email memory exhaustion, and frontend proxy timeout degradation.

## Findings and Ground Truth Verification

Both investigators diverged significantly in their blamed failure modes:
1. **Agreement:** Both models recognized that the incident produced end-to-end user latency degradation across checkout flows rather than immediate hard crashes.
2. **Divergence:** Investigator 1 attributed latency to upstream product-catalog lookups and internal checkout preparation steps. Investigator 2 hypothesized external payment gateway timeouts and email buffer saturation.
3. **Telemetry Verdict:** Telemetry queries executed on the Prometheus snapshot revealed that payment and email services maintained low error baselines throughout the onset window. Consequently, the severe failure hypotheses proposed by Investigator 2 were disproved by telemetry data (`hallucinated`), confirming that the root cause was isolated to latency accumulation rather than catastrophic downstream service failures.