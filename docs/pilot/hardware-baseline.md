# Legion Pro 5i Hardware Baseline & Resource Allocation Profile

| Field | Value |
|---|---|
| **Document Type** | Hardware Baseline & Workload Profile (Task T15.00) |
| **System Model** | Lenovo Legion Pro 5i Gen 9 (16IRX9) |
| **Evaluation Date** | 2026-10-24 |
| **Status** | **🟢 COMPLETED & VERIFIED ON HARDWARE** |
| **Author** | Quantitative Engineering Lead & Systems Architect |
| **Related Documents** | `docs/research/career-architect-implementation-plan.md`, `task.md` (Phase 15A), `memory.md` |

---

## 1. Executive Summary & Verification Findings

Prior to launching feature engineering and model pipelines for **Career Architect (Phase 15)**, an empirical audit of the development laptop hardware was conducted under Task `T15.00`.

### Core Determinations:
1. **CPU Capacity (Generous):** Intel Core i7-14650HX provides 16 physical cores (8 Performance + 8 Efficient) and 24 hardware threads. This provides abundant parallel execution capacity for test suites, data ingestion, and conformal bootstrap simulations.
2. **GPU Capacity (Sufficient for Local Inference):** NVIDIA GeForce RTX 4060 Laptop GPU possesses 8,188 MiB (8 GB) GDDR6 VRAM with a 125W active TGP and CUDA 13.3 support. It is sufficient for local fp16 embeddings (`sentence-transformers`), small 4-bit quantized drafting LLMs (7B–9B class), and accelerated PyTorch/CatBoost operations. It is strictly barred from serving-path runtime inference per Rule `R-SC-07`.
3. **RAM Capacity (The Binding Bottleneck):** Currently equipped with a single 16 GB DDR5-5600 SO-DIMM in Channel A (Channel B empty). Measured baseline RAM usage under normal developer workload (Windows 11, Antigravity IDE, browser sessions) consumes ~14.4 GB, leaving only ~1.33 GB free headroom before page file swapping.
   - **Critical Recommendation:** Add a second matched 16 GB DDR5-5600 module (or 2×16 GB dual-channel kit) to expand to 32 GB.
   - **Immediate Operational Policy:** Cap WSL2 memory to 8 GB via `.wslconfig` (Appendix D) and run at most 2 concurrent Antigravity agent worktrees.
4. **Primary Storage:** 1 TB NVMe SSD with 148.44 GB free (15.6%). To preserve drive health and SLC cache performance, free headroom should be maintained above 20% (~190 GB).

---

## 2. Hardware Architecture Inventory

| Subsystem | Specification | Measured State | Operational Strategy |
|:---|:---|:---|:---|
| **Processor** | Intel Core i7-14650HX | 16 Cores (8P + 8E), 24 Logical Processors, 30 MB Cache | Parallelize test suites with `pytest-xdist` (start at 6 workers); parallel bootstrap with `joblib`. |
| **Dedicated GPU** | NVIDIA GeForce RTX 4060 Laptop | 8,188 MiB GDDR6, 125W TGP, Driver 610.62, CUDA 13.3 | Local fp16 embedding re-audits (EXP-09r), offline draft validation. Idle at 51°C. |
| **System Memory** | 16 GB DDR5-5600 | 15.73 GB visible; 14.4 GB in use, 1.33 GB free | Cap WSL2 VM at 8 GB; avoid running Docker Desktop simultaneously with local LLMs. |
| **Primary Storage** | 1 TB PCIe 4.0 NVMe SSD | 951.65 GB total, 148.44 GB free | Keep project worktree on SSD; prune cached test artifacts and pip/npm caches periodically. |
| **Power Profile** | Windows Power Plan / Vantage | Active: Balanced (Fn+Q switches to Performance) | Use Balanced for plain editing; switch to Performance (Fn+Q red light) when plugged in for training. |
| **Virtualization** | WSL2 Ubuntu 22.04 LTS | Installed, currently stopped | Use native Windows tooling for IDE while running tests via WSL2 or native `uv`. |

---

## 3. Workload Benchmark Measurements

All metrics measured directly on the host machine on 2026-10-24:

| Benchmark Task | Target Subsystem | Measured Duration | Throughput / Notes |
|:---|:---|:---|:---|
| **Type Check (Strict Mypy)** | CPU (Single thread) | **1.12 s** | Evaluated across 121 domain modules in `src/compintel/` |
| **Linter Check (Ruff)** | CPU (Multi-core) | **1.04 s** | Scanned 140+ python files in `src/`, `tests/`, `scripts/` |
| **Vite Production Bundle** | CPU & Node.js | **14.83 s** | Clean production build of `apps/web` with zero warnings |
| **Vitest Unit/A11y Suite** | CPU (Single process) | **15.50 s** | 96/96 passing tests including Axe accessibility evaluations |
| **Pytest Suite (ML Subset)** | CPU (Single worker) | **5.58 s** | Evaluated 42 conformal, quantile GBM, and syndication tests |
| **GPU Telemetry (`nvidia-smi`)**| GPU | **256 MiB / 8,188 MiB** | 0% utilization, 51°C, 3W draw at idle |

---

## 4. Memory Allocation & Isolation Budget (16 GB Configuration)

```
Total Physical RAM: 16.0 GB (15.73 GB Visible)
┌─────────────────────────────────────────────────────────────┐
│ Windows 11 + OS Core Services: 3.5 GB                       │
├─────────────────────────────────────────────────────────────┤
│ Developer Tools (Antigravity IDE + Chrome Profile): 3.5 GB  │
├─────────────────────────────────────────────────────────────┤
│ WSL2 VM or Local Test Workers (Capped): 6.0 - 8.0 GB       │
├─────────────────────────────────────────────────────────────┤
│ Headroom / Page Cache: 1.0 - 2.5 GB                         │
└─────────────────────────────────────────────────────────────┘
```

### Resource Guardrails:
1. **WSL2 Configuration (`.wslconfig`):**
   ```ini
   [wsl2]
   memory=8GB
   processors=16
   swap=8GB
   ```
2. **Pytest Parallelism:**
   - On 16 GB RAM: Start with `-n 6` workers to prevent memory contention.
   - Upon upgrading to 32 GB RAM: Expand to `-n 12` workers.
3. **Task Serialization Invariant:**
   - Never concurrently run heavy model training, Playwright visual tests, and a local quantized LLM. Execute sequentially to avoid memory thrashing.

---

## 5. Verification Sign-Off

- **Task T15.00 Verdict:** **🟢 COMPLETED & RATIFIED**
- **Hardware Profile Verified:** Lenovo Legion Pro 5i Gen 9 (i7-14650HX / RTX 4060 / 16 GB)
- **Ready for Next Task:** **T15.01 Context Hygiene (`docs/STATE.md` & Split Rules)**
