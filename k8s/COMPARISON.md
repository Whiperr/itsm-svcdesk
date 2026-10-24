<!-- ai-generated: 0% - by hand -->
# Comparison: K8sGPT Analysis vs. Agentic Telemetry Loop (Stretch 3)

## Architectural Scope and Observability Domain

This analysis compares the diagnostic capabilities of K8sGPT (analyzers operating on Kubernetes cluster objects) against the agentic telemetry investigation loop (LLM operating over Prometheus span metrics via MCP) during the 2026-10-12 checkout latency incident.

### 1. What K8sGPT Can and Cannot See
K8sGPT analyzes the structural state of Kubernetes resources: pod lifecycle events (CrashLoopBackOff, OOMKilled), container readiness and liveness probe failures, services without endpoints, and volume or config map mount failures. 
During this incident, all microservices in the OpenTelemetry Demo remained fully operational (`Running 1/1`) from Kubernetes' perspective. The injected feature flag faults (such as shipping slowdowns or lock contention) induced internal latency and logic stalls rather than process termination or probe failures. Consequently, K8sGPT reported no actionable critical findings, as the cluster control plane observed all pods as completely healthy.

### 2. What the Agentic Telemetry Loop Observed
In contrast, the agentic investigation loop had direct access to OpenTelemetry span metrics (`traces_span_metrics_calls_total` and `traces_span_metrics_duration_milliseconds_bucket`). This allowed the model to observe:
- End-to-end request latency degradation on `POST /api/checkout`.
- Duration spikes in downstream spans (`ProductCatalogService/GetProduct` and `CheckoutService/PlaceOrder`).
- Real-time degradation in service response times across distributed boundaries.

### Summary
K8sGPT is designed for infrastructure and pod-level health anomalies, making it blind to application-level semantic degradation where containers stay healthy but responses stall. The agentic Prometheus loop is essential for detecting latency bottlenecks, error rate anomalies, and feature-flag misconfigurations inside running containers.