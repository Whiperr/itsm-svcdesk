---
# ai-generated: 0% - by hand
---
# Latency Gap Analysis between Client and Server

This document analyzes the observed difference (gap) between client-side measured latency and server-side metrics for the `svcdesk` service. 

## Key Findings & Factors
1. **Network Overhead & Serialization:** A portion of the gap stems from network transit across container interfaces, TCP socket management, and HTTP header parsing overhead on both the client and server sides.
2. **Queueing & Concurrency:** Client-side open-loop measurements at a fixed request rate introduce waiting times during minor resource contention periods, whereas server-side metrics track internal application handler execution.
3. **Measurement Boundary:** The client measures end-to-end round-trip time (RTT) from dispatch to final response receipt, whereas server histograms log application-level duration.