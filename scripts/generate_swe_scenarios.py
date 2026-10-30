"""Script to author and validate canonical Software Engineering (SWE) practice scenarios (Task T16.06).

Adheres to:
- ADR-0010 & Rule R-CR-15: Zero runtime LLMs.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit.
- Rule R-CR-11: Practice, not certification (rejects credentialism terms).
- Rule R-CR-01: Prohibits causal compensation promises.
- Rule R-CR-04: Ground-truth provenance and source attribution tracking.
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.career.scenario_schema import (
    ArtifactLanguage,
    DefectCategory,
    DefectSeverity,
    FalseFlagPenalty,
    PracticeScenario,
    ScenarioArtifact,
    ScenarioRubric,
    ScenarioVariant,
    SeededDefect,
)
from compintel.career.schema import (
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
)
from compintel.schema.enums import RoleFamily


def generate_swe_scenarios() -> dict[str, PracticeScenario]:
    """Build and validate all three canonical SWE family scenarios."""
    out_dir = Path("config/scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    provenance_concur = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-01",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-30",
    )

    provenance_sec = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-02",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-30",
    )

    provenance_db = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-03",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-30",
    )

    # =========================================================================
    # 1. SCEN-SWE-01-CONCUR: Concurrency & Async Queue Review
    # =========================================================================
    concur_code = (
        "import asyncio\n"
        "import httpx\n"
        "\n"
        "PENDING_TASKS = asyncio.Queue()\n"
        "COMPLETED_EVENTS = []\n"
        "USER_EXECUTION_COUNTS = {}\n"
        "\n"
        "async def process_task(task_payload: dict) -> None:\n"
        "    user_id = task_payload['user_id']\n"
        "    # Read-modify-write without synchronization across concurrent tasks\n"
        "    current = USER_EXECUTION_COUNTS.get(user_id, 0)\n"
        "    await asyncio.sleep(0.01)\n"
        "    USER_EXECUTION_COUNTS[user_id] = current + 1\n"
        "\n"
        "    # Append to process global without eviction or TTL\n"
        "    COMPLETED_EVENTS.append(task_payload)\n"
        "\n"
        "    # Ephemeral HTTP client allocated per task without connection teardown\n"
        "    client = httpx.AsyncClient(timeout=5.0)\n"
        "    response = await client.post('https://api.internal/webhook', json=task_payload)\n"
        "    if response.status_code != 200:\n"
        "        raise RuntimeError('Webhook dispatch failed')\n"
        "\n"
        "async def worker_loop() -> None:\n"
        "    while True:\n"
        "        task = await PENDING_TASKS.get()\n"
        "        asyncio.create_task(process_task(task))\n"
    )

    scen_concur = PracticeScenario(
        id="SCEN-SWE-01-CONCUR",
        title="Diagnostic Review: Asynchronous Task Dispatch Queue",
        description=(
            "Inspect an asynchronous task dispatch queue for thread synchronization hazards, "
            "unbounded memory growth, and missing connection teardown."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        primary_competency_id="swe.core.l2_concurrency",
        secondary_competency_ids=["swe.core.l3_memory_perf"],
        artifact=ScenarioArtifact(
            content=concur_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(concur_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-01-CONCUR",
            defects=[
                SeededDefect(
                    id="DEF-SWE-01-RACE",
                    line_number=13,
                    category=DefectCategory.RACE_CONDITION,
                    severity=DefectSeverity.CRITICAL,
                    title="Unsynchronized Shared State Read-Modify-Write Race Hazard",
                    consequence=(
                        "Concurrent tasks for the same user interleave between read and write, "
                        "causing lost updates and corrupted counter state."
                    ),
                    diagnostic_explanation=(
                        "Use asyncio.Lock() or an atomic counter primitive to synchronize access "
                        "to shared in-memory collections."
                    ),
                    competency_id="swe.core.l2_concurrency",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-01-UNBOUNDED",
                    line_number=16,
                    category=DefectCategory.UNBOUNDED_COLLECTION,
                    severity=DefectSeverity.MAJOR,
                    title="Unbounded In-Memory Retention of Completed Task Payloads",
                    consequence=(
                        "Appending every completed task payload to a process-global list without "
                        "eviction or TTL causes progressive heap memory exhaustion."
                    ),
                    diagnostic_explanation=(
                        "Use a bounded deque with maxlen, a TTL-backed LRU cache, or persist "
                        "completed event records to an external event store."
                    ),
                    competency_id="swe.core.l3_memory_perf",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-01-LEAK",
                    line_number=19,
                    category=DefectCategory.RESOURCE_LEAK,
                    severity=DefectSeverity.MAJOR,
                    title="Unclosed HTTP Client Session Socket Leak",
                    consequence=(
                        "Instantiating AsyncClient inside per-task handlers without an async with "
                        "block or explicit aclose() leaves TCP sockets in CLOSE_WAIT."
                    ),
                    diagnostic_explanation=(
                        "Wrap the client in 'async with httpx.AsyncClient() as client:' or reuse a "
                        "single shared client lifecycle across worker tasks."
                    ),
                    competency_id="swe.core.l2_concurrency",
                    points=1.0,
                ),
            ],
            pass_threshold_score=2.0,
            false_flag_penalty=FalseFlagPenalty(
                penalty_per_flag=0.5,
                max_penalty=1.5,
            ),
        ),
        variants=[
            ScenarioVariant(
                variant_id="VAR-PAYMENT-WORKER",
                description="Payment gateway notification webhook dispatch queue",
                parameters={"queue_name": "payments_queue", "batch_size": "50"},
            ),
            ScenarioVariant(
                variant_id="VAR-EMAIL-DISPATCH",
                description="Transactional email delivery dispatch queue",
                parameters={"queue_name": "email_queue", "batch_size": "25"},
            ),
        ],
        instructions=(
            "Inspect the asynchronous task queue for synchronization race hazards, "
            "unbounded memory retention, and missing connection teardown. Flag flawed line numbers "
            "and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_concur,
    )

    # =========================================================================
    # 2. SCEN-SWE-02-SEC: Security Audit in Web Endpoint
    # =========================================================================
    sec_code = (
        "from fastapi import FastAPI, HTTPException, Request\n"
        "import sqlite3\n"
        "\n"
        "app = FastAPI()\n"
        "SECRET_WEBHOOK_KEY = 'sk_live_99a8b7c6d5e4'\n"
        "\n"
        "@app.post('/v1/tenants/{tenant_id}/query')\n"
        "async def query_tenant_records(tenant_id: str, request: Request) -> dict:\n"
        "    token = request.headers.get('X-Webhook-Token', '')\n"
        "    # Plaintext string comparison vulnerable to timing side-channel attack\n"
        "    if token != SECRET_WEBHOOK_KEY:\n"
        "        raise HTTPException(status_code=401, detail='Invalid token')\n"
        "\n"
        "    payload = await request.json()\n"
        "    user_query = payload.get('filter_term', '')\n"
        "\n"
        "    conn = sqlite3.connect('tenants.db')\n"
        "    cursor = conn.cursor()\n"
        "    # Direct string formatting in SQL query enabling injection\n"
        "    sql = f\"SELECT id, data FROM records WHERE tenant_id = '{tenant_id}' AND tag = '{user_query}'\"\n"
        "    cursor.execute(sql)\n"
        "    results = cursor.fetchall()\n"
        "\n"
        "    # Unclosed database connection and cursor leak\n"
        "    return {'tenant': tenant_id, 'items': results, 'count': len(results)}\n"
    )

    scen_sec = PracticeScenario(
        id="SCEN-SWE-02-SEC",
        title="Security Audit: Multi-Tenant Ingress Router and Authentication",
        description=(
            "Audit a web service route handler for SQL injection vectors, timing attack "
            "vulnerabilities in token verification, and unclosed connection leaks."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="swe.sec.l3_owasp_top10",
        secondary_competency_ids=["swe.arch.l2_api_design"],
        artifact=ScenarioArtifact(
            content=sec_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(sec_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-02-SEC",
            defects=[
                SeededDefect(
                    id="DEF-SWE-02-AUTH",
                    line_number=11,
                    category=DefectCategory.BROKEN_AUTHENTICATION,
                    severity=DefectSeverity.CRITICAL,
                    title="Constant-Time Secret Comparison Violation",
                    consequence=(
                        "Standard string equality (!=) returns early upon the first mismatched byte, "
                        "exposing cryptographic API tokens to timing side-channel attacks."
                    ),
                    diagnostic_explanation=(
                        "Use hmac.compare_digest(token, SECRET_WEBHOOK_KEY) to execute constant-time "
                        "token comparison."
                    ),
                    competency_id="swe.sec.l3_owasp_top10",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-02-INJECT",
                    line_number=20,
                    category=DefectCategory.SQL_INJECTION,
                    severity=DefectSeverity.CRITICAL,
                    title="Direct String Interpolation in Relational Query",
                    consequence=(
                        "F-string formatting injects unescaped user input directly into the SQL parser, "
                        "enabling arbitrary SQL injection and cross-tenant data access."
                    ),
                    diagnostic_explanation=(
                        "Use parameterized query placeholders (?, :param) and pass inputs as separate "
                        "parameter tuples to the database driver."
                    ),
                    competency_id="swe.sec.l3_owasp_top10",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-02-LEAK",
                    line_number=25,
                    category=DefectCategory.RESOURCE_LEAK,
                    severity=DefectSeverity.MAJOR,
                    title="Unclosed Database Connection in Route Handler",
                    consequence=(
                        "Allocating a database connection per request without calling close() or using "
                        "a context manager exhausts the OS file descriptor table."
                    ),
                    diagnostic_explanation=(
                        "Use 'with sqlite3.connect(...) as conn:' or manage connections through a "
                        "persistent connection pool."
                    ),
                    competency_id="swe.sec.l3_owasp_top10",
                    points=1.0,
                ),
            ],
            pass_threshold_score=2.0,
            false_flag_penalty=FalseFlagPenalty(
                penalty_per_flag=0.5,
                max_penalty=1.5,
            ),
        ),
        variants=[
            ScenarioVariant(
                variant_id="VAR-FINTECH-AUTH",
                description="Banking partner reconciliation endpoint variant",
                parameters={"header_key": "X-Partner-Secret", "db_name": "reconciliation.db"},
            ),
            ScenarioVariant(
                variant_id="VAR-SAAS-INGRESS",
                description="B2B SaaS tenant webhook receiver variant",
                parameters={"header_key": "X-SaaS-Token", "db_name": "tenants_prod.db"},
            ),
        ],
        instructions=(
            "Inspect the web route handler for SQL injection vectors, timing side-channels, "
            "and unclosed database connection leaks. Flag flawed line numbers and select correct "
            "defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_sec,
    )

    # =========================================================================
    # 3. SCEN-SWE-03-DB: Database Query Performance and Cartesian Leak
    # =========================================================================
    db_code = (
        "from sqlalchemy.orm import Session\n"
        "from models import Order, DiscountRule\n"
        "\n"
        "def calculate_batch_discounts(db: Session, merchant_id: str) -> list[dict]:\n"
        "    # Full-table fetch loading all rows into RAM without pagination\n"
        "    all_orders = db.query(Order).filter(Order.merchant_id == merchant_id).all()\n"
        "\n"
        "    # Missing join condition producing Cartesian cross-product explosion\n"
        "    coupons = db.query(Order, DiscountRule).filter(Order.merchant_id == merchant_id).all()\n"
        "\n"
        "    processed = []\n"
        "    for order in all_orders:\n"
        "        total_rebate = sum(c.DiscountRule.amount for c in coupons if c.DiscountRule.min_spend <= order.total)\n"
        "        processed.append({'order_id': order.id, 'rebate': total_rebate})\n"
        "\n"
        "    # Dangling raw database cursor and uncommitted lock retention\n"
        "    raw_conn = db.bind.raw_connection()\n"
        "    cursor = raw_conn.cursor()\n"
        "    cursor.execute('UPDATE merchants SET last_batch_at = NOW() WHERE id = %s', (merchant_id,))\n"
        "    # Missing cursor.close() and transaction commit / release\n"
        "\n"
        "    return processed\n"
    )

    scen_db = PracticeScenario(
        id="SCEN-SWE-03-DB",
        title="Performance Audit: Order Service Relational Pipeline",
        description=(
            "Inspect an order batch processing routine for unpaginated in-memory collections, "
            "Cartesian join explosions, and database lock exhaustion."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="swe.db.l3_query_perf",
        secondary_competency_ids=["swe.arch.l3_microservices"],
        artifact=ScenarioArtifact(
            content=db_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(db_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-03-DB",
            defects=[
                SeededDefect(
                    id="DEF-SWE-03-UNBOUNDED",
                    line_number=6,
                    category=DefectCategory.UNBOUNDED_COLLECTION,
                    severity=DefectSeverity.CRITICAL,
                    title="Unpaginated Full-Table Fetch into Application Heap",
                    consequence=(
                        "Calling .all() on an unconstrained customer order table loads millions of "
                        "ORM objects into memory, triggering excessive GC latency and OOM failure."
                    ),
                    diagnostic_explanation=(
                        "Use keyset or cursor-based pagination with .limit() and .yield_per() to stream "
                        "records in manageable batches."
                    ),
                    competency_id="swe.db.l3_query_perf",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-03-EXPLOSION",
                    line_number=9,
                    category=DefectCategory.CARDINALITY_EXPLOSION,
                    severity=DefectSeverity.CRITICAL,
                    title="Cartesian Cross-Product from Missing Join Constraint",
                    consequence=(
                        "Querying two entities without an explicit join predicate generates an M x N "
                        "cross product on the database engine, exhausting query worker threads."
                    ),
                    diagnostic_explanation=(
                        "Specify an explicit join predicate via .join(DiscountRule, Order.discount_id == "
                        "DiscountRule.id) or a foreign key relationship."
                    ),
                    competency_id="swe.db.l3_query_perf",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-03-LEAK",
                    line_number=19,
                    category=DefectCategory.RESOURCE_LEAK,
                    severity=DefectSeverity.MAJOR,
                    title="Dangling Raw Database Cursor and Uncommitted Lock Retention",
                    consequence=(
                        "Acquiring a raw connection cursor without try-finally or context closure leaves "
                        "transaction locks open and leaks physical database connections from the pool."
                    ),
                    diagnostic_explanation=(
                        "Use the managed db.execute() session interface or guarantee cursor.close() "
                        "within a try...finally block."
                    ),
                    competency_id="swe.db.l3_query_perf",
                    points=1.0,
                ),
            ],
            pass_threshold_score=2.0,
            false_flag_penalty=FalseFlagPenalty(
                penalty_per_flag=0.5,
                max_penalty=1.5,
            ),
        ),
        variants=[
            ScenarioVariant(
                variant_id="VAR-ECOMMERCE-CHECKOUT",
                description="High-volume marketplace promotional discount engine",
                parameters={"batch_size": "500", "region": "APAC"},
            ),
            ScenarioVariant(
                variant_id="VAR-SUBSCRIPTION-BILLING",
                description="Recurring subscription renewal and credit recalculation",
                parameters={"batch_size": "250", "region": "IN"},
            ),
        ],
        instructions=(
            "Inspect the order processing pipeline for unpaginated collection loading, "
            "Cartesian cross-product queries, and dangling database cursors. Flag flawed line numbers "
            "and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_db,
    )

    scenarios = {
        "scen_swe_01_concur.json": scen_concur,
        "scen_swe_02_sec.json": scen_sec,
        "scen_swe_03_db.json": scen_db,
    }

    for filename, scenario in scenarios.items():
        filepath = out_dir / filename
        data = scenario.model_dump(mode="json")
        filepath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Serialized {scenario.id} to {filepath}")

    return scenarios


if __name__ == "__main__":
    generate_swe_scenarios()
