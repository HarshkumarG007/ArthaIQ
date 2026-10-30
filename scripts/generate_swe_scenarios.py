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

    provenance_api = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-04",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-31",
    )

    provenance_test = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-05",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-31",
    )

    provenance_obs = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-06",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-31",
    )

    provenance_dist = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-SWE-07",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (SWE Family)",
        modified_flag=False,
        curator="SWE Review Panel",
        curated_date="2026-10-31",
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

    # =========================================================================
    # 4. SCEN-SWE-04-API: Order Fulfillment REST API Endpoint Review
    # =========================================================================
    api_code = (
        "from fastapi import FastAPI, HTTPException\n"
        "from pydantic import BaseModel\n"
        "import traceback\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "class OrderRequest(BaseModel):\n"
        "    user_id: str\n"
        "    items: list[dict]\n"
        "    shipping_address: dict | None = None\n"
        "\n"
        "@app.post('/v1/orders/checkout')\n"
        "async def checkout_order(order: OrderRequest, db = None):\n"
        "    try:\n"
        "        # Unhandled null access on optional shipping address\n"
        "        postal_code = order.shipping_address['pincode']\n"
        "        # Unpaginated full table query loading all historical records into memory\n"
        "        all_orders = db.query('SELECT * FROM orders').fetchall()\n"
        "        # Process checkout\n"
        "        return {'status': 'success', 'pincode': postal_code, 'order_count': len(all_orders)}\n"
        "    except Exception as exc:\n"
        "        # Leaks internal DB traceback and schema details to client\n"
        "        return {'error': str(exc), 'stack_trace': traceback.format_exc()}\n"
    )

    scen_api = PracticeScenario(
        id="SCEN-SWE-04-API",
        title="Order Fulfillment REST API Endpoint Review",
        description=(
            "Inspect an order checkout endpoint for optional field null dereferences, "
            "unpaginated full table query memory risks, and raw exception stack trace leaks."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        primary_competency_id="swe.app.l2_rest_api",
        secondary_competency_ids=["swe.app.l3_concurrency", "swe.test.l2_unit_test"],
        artifact=ScenarioArtifact(
            content=api_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(api_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-04-API",
            defects=[
                SeededDefect(
                    id="DEF-SWE-04-NULL",
                    line_number=16,
                    category=DefectCategory.NULL_HANDLING,
                    severity=DefectSeverity.CRITICAL,
                    title="Unhandled Optional Address Null Dereference",
                    consequence=(
                        "Subscripting order.shipping_address without null checking raises TypeError "
                        "when client submits payload without optional shipping details."
                    ),
                    diagnostic_explanation=(
                        "Validate that shipping_address is not None before subscripting or use "
                        "safe dictionary access like (order.shipping_address or {}).get('pincode')."
                    ),
                    competency_id="swe.app.l2_rest_api",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-04-UNBOUND",
                    line_number=18,
                    category=DefectCategory.UNBOUNDED_COLLECTION,
                    severity=DefectSeverity.MAJOR,
                    title="Unpaginated Full Table Query in API Handler",
                    consequence=(
                        "Loading all historical orders into server process memory causes extreme latency "
                        "and Out-Of-Memory termination under high production data volumes."
                    ),
                    diagnostic_explanation=(
                        "Apply parameterized pagination (LIMIT and OFFSET or cursor pagination) and filter by user_id."
                    ),
                    competency_id="swe.app.l2_rest_api",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-04-LEAK",
                    line_number=23,
                    category=DefectCategory.DATA_LEAKAGE,
                    severity=DefectSeverity.CRITICAL,
                    title="Internal Database Stack Trace Exposure in Response",
                    consequence=(
                        "Returning raw traceback strings reveals internal schema details, table names, "
                        "and filesystem paths to potential attackers."
                    ),
                    diagnostic_explanation=(
                        "Return generic error message with unique correlation ID and log the detailed traceback server-side."
                    ),
                    competency_id="swe.app.l2_rest_api",
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
                variant_id="VAR-MARKETPLACE-CHECKOUT",
                description="Consumer retail marketplace checkout handler",
                parameters={"batch_size": "100", "auth_mode": "session"},
            ),
        ],
        instructions=(
            "Inspect the checkout API endpoint for unhandled null references, unpaginated data queries, "
            "and sensitive stack trace leakage. Flag flawed line numbers and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_api,
    )

    # =========================================================================
    # 5. SCEN-SWE-05-TEST: Payment Gateway Unit Test Suite Review
    # =========================================================================
    test_code = (
        "import os\n"
        "import pytest\n"
        "from unittest.mock import AsyncMock, patch\n"
        "\n"
        "class TestPaymentService:\n"
        "    def test_payment_gateway_timeout(self):\n"
        "        # Modifies global environment variable without teardown or fixture cleanup\n"
        "        os.environ['PAYMENT_GATEWAY_TIMEOUT'] = '0'\n"
        "        from services import payment\n"
        "        result = payment.initiate_charge(amount=1000)\n"
        "        assert result.status == 'FAILED'\n"
        "\n"
        "    def test_mock_return_none_dereference(self):\n"
        "        with patch('services.payment.client') as mock_client:\n"
        "            # Mock returns None, causing unhandled attribute error when reading status\n"
        "            mock_client.charge.return_value = None\n"
        "            res = mock_client.charge(500)\n"
        "            assert res.status == 'FAILED'\n"
        "\n"
        "    async def test_async_refund_missing_await(self):\n"
        "        refund_mock = AsyncMock(return_value={'refund_id': 'REF-123'})\n"
        "        # Coroutine called without await: assertion passes tautologically without executing logic\n"
        "        refund_mock(charge_id='CHG-99')\n"
        "        assert True\n"
    )

    scen_test = PracticeScenario(
        id="SCEN-SWE-05-TEST",
        title="Payment Gateway Unit Test Suite Review",
        description=(
            "Inspect an automated test suite for global environment mutation, "
            "mock null dereference traps, and unawaited async coroutine assertions."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        primary_competency_id="swe.test.l2_unit_test",
        secondary_competency_ids=["swe.test.l3_integration", "swe.app.l2_rest_api"],
        artifact=ScenarioArtifact(
            content=test_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(test_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-05-TEST",
            defects=[
                SeededDefect(
                    id="DEF-SWE-05-ENV",
                    line_number=8,
                    category=DefectCategory.RESOURCE_LEAK,
                    severity=DefectSeverity.MAJOR,
                    title="Global Environment Mutation without Teardown",
                    consequence=(
                        "Mutating os.environ directly within a test pollutes subsequent test cases in the "
                        "suite, causing non-deterministic order-dependent test failures."
                    ),
                    diagnostic_explanation=(
                        "Use pytest's monkeypatch fixture (monkeypatch.setenv) to guarantee automatic cleanup."
                    ),
                    competency_id="swe.test.l2_unit_test",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-05-NULL",
                    line_number=16,
                    category=DefectCategory.NULL_HANDLING,
                    severity=DefectSeverity.CRITICAL,
                    title="Mock Null Return Value Dereference Trap",
                    consequence=(
                        "Setting return_value to None causes res.status to raise AttributeError instead "
                        "of asserting the expected FAILED status."
                    ),
                    diagnostic_explanation=(
                        "Mock the response object with appropriate schema (e.g., Mock(status='FAILED')) or test handling of None."
                    ),
                    competency_id="swe.test.l2_unit_test",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-05-AWAIT",
                    line_number=23,
                    category=DefectCategory.RACE_CONDITION,
                    severity=DefectSeverity.CRITICAL,
                    title="Unawaited Async Mock Coroutine Invocation",
                    consequence=(
                        "Calling an async coroutine without await produces an unawaited coroutine warning "
                        "and causes the test to pass vacously without executing the underlying verification logic."
                    ),
                    diagnostic_explanation=(
                        "Prefix async mock invocations with await (await refund_mock(...)) and assert specific return values."
                    ),
                    competency_id="swe.test.l2_unit_test",
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
                variant_id="VAR-PAYMENT-MOCK-TEST",
                description="Core payment processing unit test harness",
                parameters={"mock_backend": "stripe_stub"},
            ),
        ],
        instructions=(
            "Inspect the unit test methods for global state contamination, mock null dereferences, "
            "and missing async await calls. Flag flawed line numbers and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_test,
    )

    # =========================================================================
    # 6. SCEN-SWE-06-OBS: Telemetry Instrumentation & Audit Logging Review
    # =========================================================================
    obs_code = (
        "import logging\n"
        "from prometheus_client import Counter\n"
        "\n"
        "logger = logging.getLogger('api.telemetry')\n"
        "\n"
        "# Prometheus counter for incoming HTTP requests\n"
        "REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'user_id'])\n"
        "\n"
        "def record_request_telemetry(method: str, user_id: str, auth_token: str, path: str):\n"
        "    # High-cardinality metric explosion by tagging with unique user ID\n"
        "    REQUEST_COUNT.labels(method=method, user_id=user_id).inc()\n"
        "\n"
        "    # Logging raw Authorization Bearer token into plain application logs\n"
        "    logger.info(f'Processing request for path={path} with bearer_token={auth_token}')\n"
        "\n"
        "    # Insecure authentication parsing: accepts any string without checking Bearer scheme\n"
        "    token_value = auth_token.split(' ')[-1]\n"
        "    if not token_value:\n"
        "        raise ValueError('Empty token')\n"
        "    return {'status': 'recorded', 'user': user_id}\n"
    )

    scen_obs = PracticeScenario(
        id="SCEN-SWE-06-OBS",
        title="Telemetry Instrumentation & Audit Logging Review",
        description=(
            "Inspect request telemetry handlers for Prometheus cardinality explosions, "
            "plaintext authentication token leaks in logs, and insecure token prefix extraction."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="swe.sec.l3_auth_rbac",
        secondary_competency_ids=["swe.sec.l4_threat_model", "swe.arch.l3_microservices"],
        artifact=ScenarioArtifact(
            content=obs_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(obs_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-06-OBS",
            defects=[
                SeededDefect(
                    id="DEF-SWE-06-CARD",
                    line_number=11,
                    category=DefectCategory.CARDINALITY_EXPLOSION,
                    severity=DefectSeverity.CRITICAL,
                    title="Prometheus Metric High-Cardinality User Label",
                    consequence=(
                        "Tagging time-series metrics with unique user IDs causes unbounded time-series creation, "
                        "leading to monitoring cluster memory exhaustion and ingestion failure."
                    ),
                    diagnostic_explanation=(
                        "Remove individual user ID labels from Prometheus metrics; use distributed tracing for per-user diagnostics."
                    ),
                    competency_id="swe.sec.l3_auth_rbac",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-06-LEAK",
                    line_number=14,
                    category=DefectCategory.DATA_LEAKAGE,
                    severity=DefectSeverity.CRITICAL,
                    title="Plaintext Authentication Token Leak in Application Logs",
                    consequence=(
                        "Writing raw bearer tokens to application logs exposes sensitive authentication tokens "
                        "to log collectors, third-party indexers, and unauthorized internal operators."
                    ),
                    diagnostic_explanation=(
                        "Mask or redact sensitive authentication headers before logging (e.g., token[:6] + '***')."
                    ),
                    competency_id="swe.sec.l3_auth_rbac",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-06-AUTH",
                    line_number=17,
                    category=DefectCategory.BROKEN_AUTHENTICATION,
                    severity=DefectSeverity.MAJOR,
                    title="Insecure Token Header Scheme Parsing",
                    consequence=(
                        "Splitting on space without validating the 'Bearer ' scheme prefix allows malformed or "
                        "spoofed token schemes to bypass preliminary format validation."
                    ),
                    diagnostic_explanation=(
                        "Strictly validate that the Authorization header starts with 'Bearer ' before extracting the token."
                    ),
                    competency_id="swe.sec.l3_auth_rbac",
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
                variant_id="VAR-INGRESS-TELEMETRY",
                description="API gateway telemetry and security audit handler",
                parameters={"log_format": "json"},
            ),
        ],
        instructions=(
            "Inspect the telemetry recorder for metric cardinality explosion, plaintext token exposure in logs, "
            "and header parsing flaws. Flag flawed line numbers and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_obs,
    )

    # =========================================================================
    # 7. SCEN-SWE-07-DIST: Distributed Cache & Resilient Read-Through Review
    # =========================================================================
    dist_code = (
        "import time\n"
        "import redis\n"
        "\n"
        "def fetch_user_profile(user_id: str, db_pool):\n"
        "    # Creates unpooled raw Redis client on every single request causing connection exhaustion\n"
        "    client = redis.Redis(host='localhost', port=6379, db=0)\n"
        "    cache_key = f'user:profile:{user_id}'\n"
        "    cached = client.get(cache_key)\n"
        "    if cached:\n"
        "        return cached\n"
        "\n"
        "    # Cache stampede: concurrent requests all query database directly without distributed lock\n"
        "    data = db_pool.query_user(user_id)\n"
        "    # Unbounded key scanning blocking Redis event loop instead of targeted pipeline\n"
        "    all_keys = client.keys('user:profile:*')\n"
        "    client.set(cache_key, str(data), ex=300)\n"
        "    return data\n"
    )

    scen_dist = PracticeScenario(
        id="SCEN-SWE-07-DIST",
        title="Distributed Cache & Resilient Read-Through Review",
        description=(
            "Inspect a distributed caching function for unpooled client connection exhaustion, "
            "cache stampede thundering herd vulnerabilities, and blocking KEYS command usage."
        ),
        role_family=RoleFamily.SWE,
        target_level=RoleLevel.LEVEL_4_SENIOR,
        primary_competency_id="swe.arch.l4_system_design",
        secondary_competency_ids=["swe.arch.l3_microservices", "swe.app.l3_concurrency"],
        artifact=ScenarioArtifact(
            content=dist_code,
            language=ArtifactLanguage.PYTHON,
            line_count=len(dist_code.splitlines()),
        ),
        rubric=ScenarioRubric(
            scenario_id="SCEN-SWE-07-DIST",
            defects=[
                SeededDefect(
                    id="DEF-SWE-07-CONN",
                    line_number=6,
                    category=DefectCategory.RESOURCE_LEAK,
                    severity=DefectSeverity.CRITICAL,
                    title="Unpooled Redis Client Instantiation per Request",
                    consequence=(
                        "Creating a new Redis connection object on every function call exhausts OS socket descriptors "
                        "and introduces severe TCP handshake latency overhead under load."
                    ),
                    diagnostic_explanation=(
                        "Instantiate a persistent Redis ConnectionPool once at application startup and share it across calls."
                    ),
                    competency_id="swe.arch.l4_system_design",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-07-STAMPEDE",
                    line_number=13,
                    category=DefectCategory.RACE_CONDITION,
                    severity=DefectSeverity.CRITICAL,
                    title="Cache Stampede Thundering Herd Vulnerability",
                    consequence=(
                        "When a popular cache key expires, multiple concurrent requests simultaneously query the primary "
                        "database, overwhelming database connection pools."
                    ),
                    diagnostic_explanation=(
                        "Implement distributed locking (e.g. Redlock or singleflight pattern) to ensure only one process rebuilds the cache."
                    ),
                    competency_id="swe.arch.l4_system_design",
                    points=1.0,
                ),
                SeededDefect(
                    id="DEF-SWE-07-KEYS",
                    line_number=15,
                    category=DefectCategory.UNBOUNDED_COLLECTION,
                    severity=DefectSeverity.CRITICAL,
                    title="Blocking KEYS Command Execution in Production",
                    consequence=(
                        "The KEYS command iterates over all keys in the single-threaded Redis database synchronously, "
                        "freezing all Redis operations for the entire application cluster."
                    ),
                    diagnostic_explanation=(
                        "Avoid KEYS in production. Use SCAN with cursor pagination or maintain a dedicated set of keys."
                    ),
                    competency_id="swe.arch.l4_system_design",
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
                variant_id="VAR-USER-PROFILE-CACHE",
                description="High-throughput user profile read-through cache layer",
                parameters={"ttl_seconds": "300"},
            ),
        ],
        instructions=(
            "Inspect the caching function for connection leaks, cache stampede vulnerabilities, "
            "and blocking Redis operations. Flag flawed line numbers and select correct defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_dist,
    )

    scenarios = {
        "scen_swe_01_concur.json": scen_concur,
        "scen_swe_02_sec.json": scen_sec,
        "scen_swe_03_db.json": scen_db,
        "scen_swe_04_api.json": scen_api,
        "scen_swe_05_test.json": scen_test,
        "scen_swe_06_obs.json": scen_obs,
        "scen_swe_07_dist.json": scen_dist,
    }

    for filename, scenario in scenarios.items():
        filepath = out_dir / filename
        data = scenario.model_dump(mode="json")
        filepath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Serialized {scenario.id} to {filepath}")

    return scenarios


if __name__ == "__main__":
    generate_swe_scenarios()
