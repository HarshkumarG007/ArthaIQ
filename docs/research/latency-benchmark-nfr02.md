# Serving Latency Benchmark & NFR-02 Target Setting

| Field | Value |
|---|---|
| Date | 2026-10-19 |
| Profile | Profile A (Laptop/Workstation CPU) |
| OS & Hardware | Windows 11 (AMD64) |
| Python Version | 3.12.9 |
| Model Version | 0.1.0 |
| Snapshot ID | `SNAP-1FF34A8E9633` |
| Iterations | 1,000 (warm-up: 50) |
| Throughput | **254.5 req/sec** |
| Error Rate | **0.0%** |
| Verdict | **VERIFIED_COMPLIANT** |

---

## 1. Executive Summary

Under Phase 9 Task T9.03, we conducted a rigorous latency benchmark of the production serving engine on **Profile A (Laptop/Workstation CPU)** across 1,000 requests.
The end-to-end HTTP endpoint (`POST /v1/estimates`) achieved a **p95 latency of 4.324 ms** and a median (**p50**) latency of **3.156 ms**, operating with **0.0% errors** at **254.5 requests/second**.

This comfortably fulfills the **50.0 ms** internal inference gate and is well within the **200.0 ms** user experience ceiling defined in PRD Section 8.
Accordingly, the formal **NFR-02 SLA Target** is established as: **`p95 <= 50ms on Profile A (Laptop/Workstation CPU)`**.

---

## 2. Latency Distribution Summary (Milliseconds)

| Measurement Layer | Mean | Std | Min | p50 (Median) | p90 | p95 (SLA) | p99 | Max |
|---|---|---|---|---|---|---|---|---|
| **HTTP Stack (POST /v1/estimates)** | 3.372 ms | 1.362 ms | 2.588 ms | **3.156 ms** | 3.922 ms | **4.324 ms** | 6.28 ms | 27.727 ms |
| **Pure Python Function (`estimate()`)** | 0.555 ms | 0.124 ms | 0.373 ms | **0.518 ms** | 0.678 ms | **0.767 ms** | 1.031 ms | 2.461 ms |

> [!NOTE]
> The difference between the HTTP stack and pure python execution (approx 2.64 ms at p50) accounts for FastAPI routing, middleware correlation tracing (`X-Request-ID`), Pydantic model validation, and RFC 9457 error wrapper checks.

---

## 3. Per-Profile Archetype Breakdown

| Profile Archetype | Samples | Mean | p50 | p95 | Max |
|---|---|---|---|---|---|
| `Core_L0_SWE_Mid_Bengaluru` | 200 | 3.359 ms | 3.181 ms | 4.392 ms | 17.338 ms |
| `Data_L1_Senior_Hyderabad_Skills` | 200 | 3.396 ms | 3.154 ms | 4.136 ms | 27.727 ms |
| `ML_L2_Staff_Pune_CompanyTier` | 200 | 3.436 ms | 3.131 ms | 4.573 ms | 27.645 ms |
| `Frontend_L3_CompareOnly_DelhiNCR` | 200 | 3.307 ms | 3.17 ms | 4.407 ms | 6.337 ms |
| `Abstention_Edge_Veteran_NonMetro` | 200 | 3.359 ms | 3.144 ms | 4.535 ms | 16.1 ms |

---

## 4. NFR-02 Target Ratification

- **Internal Budget Gate:** $\le 50.0 \text{ms}$ — **PASSED**
- **Product UX Ceiling:** $\le 200.0 \text{ms}$ — **PASSED**
- **Formally Set Target:** `p95 <= 50ms on Profile A (Laptop/Workstation CPU)`

> [!TIP]
> On modest Profile A hardware without GPU acceleration, the CatBoost CQR + Decoupled Support champion serving architecture performs at sub-10ms response times. This confirms ADR-0009 feasibility for public beta deployment on Profile B/C.