"""Script to author and validate canonical Machine Learning & AI (MLAI) practice scenarios (Task T19.06).

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


def generate_mlai_scenarios() -> dict[str, PracticeScenario]:
    """Build and validate all three canonical MLAI family scenarios."""
    out_dir = Path("config/scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    provenance_tens = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-MLAI-01",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (MLAI Family)",
        modified_flag=False,
        curator="MLAI Review Panel",
        curated_date="2026-10-31",
    )

    provenance_leak = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-MLAI-02",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (MLAI Family)",
        modified_flag=False,
        curator="MLAI Review Panel",
        curated_date="2026-10-31",
    )

    provenance_deploy = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-MLAI-03",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (MLAI Family)",
        modified_flag=False,
        curator="MLAI Review Panel",
        curated_date="2026-10-31",
    )

    # =========================================================================
    # 1. SCEN-MLAI-01-TENS: Mini-Batch Training Loop
    # =========================================================================
    code_tens = (
        "import torch\n"
        "import torch.nn as nn\n"
        "\n"
        "class MLP(nn.Module):\n"
        "    def __init__(self, in_dim: int, hidden_dim: int):\n"
        "        super().__init__()\n"
        "        self.fc1 = nn.Linear(in_dim, hidden_dim)\n"
        "        self.fc2 = nn.Linear(hidden_dim, 1)\n"
        "\n"
        "    def forward(self, x: torch.Tensor) -> torch.Tensor:\n"
        "        return self.fc2(torch.relu(self.fc1(x)))\n"
        "\n"
        "def train_epoch(model: nn.Module, loader, optimizer: torch.optim.Optimizer, criterion: nn.Module):\n"
        "    model.train()\n"
        "    # Subsample validation indices with unseeded generator\n"
        "    val_indices = torch.randperm(len(loader.dataset))[:10]\n"
        "    total_loss = 0.0\n"
        "    for batch_x, batch_y in loader:\n"
        "        optimizer.zero_grad()\n"
        "        predictions = model(batch_x)\n"
        "        # Predictions shape [B, 1] vs target shape [B] triggers broadcast\n"
        "        loss = criterion(predictions, batch_y)\n"
        "        loss.backward()\n"
        "        optimizer.step()\n"
        "        # Retaining graph reference in accumulator exhausts GPU VRAM\n"
        "        total_loss += loss\n"
        "    return total_loss / len(loader)\n"
    )
    artifact_tens = ScenarioArtifact(
        content=code_tens,
        language=ArtifactLanguage.PYTHON,
        line_count=len(code_tens.strip().split("\n")),
    )
    rubric_tens = ScenarioRubric(
        scenario_id="SCEN-MLAI-01-TENS",
        defects=[
            SeededDefect(
                id="DEF-MLAI-01-SEED",
                line_number=16,
                category=DefectCategory.UNSEEDED_RANDOMNESS,
                severity=DefectSeverity.MAJOR,
                title="Unseeded Random Permutation in Dataset Subsampling",
                consequence="Sampling validation batches without a seeded generator causes non-deterministic evaluations across runs.",
                diagnostic_explanation="Provide a seeded torch.Generator instance to ensure reproducibility.",
                competency_id="mlai.ops.l2_model_registry",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-01-SHAPE",
                line_number=22,
                category=DefectCategory.TENSOR_SHAPE_MISMATCH,
                severity=DefectSeverity.CRITICAL,
                title="Target Tensor Dimension Mismatch with Unintended Broadcasting",
                consequence="Passing (N, 1) predictions and (N,) targets to MSELoss triggers multidimensional broadcast producing an (N, N) matrix error.",
                diagnostic_explanation="Squeeze predictions to (N,) or unsqueeze targets to match dimensions exactly.",
                competency_id="mlai.core.l2_neural_backprop",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-01-GRAPH",
                line_number=26,
                category=DefectCategory.COMPUTATION_GRAPH_LEAK,
                severity=DefectSeverity.CRITICAL,
                title="Accumulating Tensor with Computational Graph Attached",
                consequence="Adding the loss tensor directly retains the entire autograd backward history across all batches, causing GPU Out-Of-Memory (OOM).",
                diagnostic_explanation="Use loss.item() or loss.detach() to accumulate scalar values without graph retention.",
                competency_id="mlai.core.l2_neural_backprop",
                points=1.0,
            ),
        ],
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )
    scen_tens = PracticeScenario(
        id="SCEN-MLAI-01-TENS",
        title="Diagnostic Review: PyTorch Mini-Batch Training Loop",
        description="Inspect a PyTorch mini-batch training loop for tensor shape broadcasting anomalies, computation graph VRAM retention, and unseeded randomness.",
        role_family=RoleFamily.MLAI,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        primary_competency_id="mlai.core.l2_neural_backprop",
        secondary_competency_ids=["mlai.ops.l2_model_registry"],
        artifact=artifact_tens,
        rubric=rubric_tens,
        variants=[
            ScenarioVariant(
                variant_id="VAR-IMAGE-CLASSIFIER",
                description="CNN training loop on image classification batches",
                parameters={"batch_size": "64", "optimizer": "AdamW"},
            ),
            ScenarioVariant(
                variant_id="VAR-TABULAR-REGRESSOR",
                description="MLP training loop on tabular regression batches",
                parameters={"batch_size": "128", "optimizer": "SGD"},
            ),
        ],
        instructions="Inspect the PyTorch training loop for broadcasting errors, computation graph leaks, and non-reproducible randomness. Flag flawed lines and select correct categories.",
        disclaimer="Technical practice scenario for capability self-reflection and professional development (Rules R-CR-08, R-CR-11).",
        provenance=provenance_tens,
    )

    # =========================================================================
    # 2. SCEN-MLAI-02-LEAK: Autoregressive Decoder Attention Block
    # =========================================================================
    code_leak = (
        "import math\n"
        "import torch\n"
        "import torch.nn as nn\n"
        "import torch.nn.functional as F\n"
        "\n"
        "def causal_attention_step(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, target_labels: torch.Tensor):\n"
        "    # Tensor dimensions: [batch_size, num_heads, seq_len, head_dim]\n"
        "    B, H, S, D = q.shape\n"
        "    scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(D)\n"
        "\n"
        "    # Masking lower triangle exposes future tokens instead of preventing lookahead\n"
        "    future_mask = torch.tril(torch.ones(S, S, device=q.device)).bool()\n"
        "    scores = scores.masked_fill(future_mask, float('-inf'))\n"
        "\n"
        "    attn_weights = F.softmax(scores, dim=-1)\n"
        "    context = torch.matmul(attn_weights, v)\n"
        "\n"
        "    # Concatenating target labels directly into hidden representation leaks ground truth\n"
        "    augmented = torch.cat([context, target_labels.unsqueeze(-1).expand(-1, -1, -1, D)], dim=-1)\n"
        "\n"
        "    # Computing unweighted pooled cross entropy over non-independent tokens\n"
        "    val_loss = F.cross_entropy(augmented.mean(dim=1), target_labels)\n"
        "    return augmented, val_loss\n"
    )
    artifact_leak = ScenarioArtifact(
        content=code_leak,
        language=ArtifactLanguage.PYTHON,
        line_count=len(code_leak.strip().split("\n")),
    )
    rubric_leak = ScenarioRubric(
        scenario_id="SCEN-MLAI-02-LEAK",
        defects=[
            SeededDefect(
                id="DEF-MLAI-02-MASK",
                line_number=13,
                category=DefectCategory.ATTENTION_MASK_LEAK,
                severity=DefectSeverity.CRITICAL,
                title="Inverted Causal Attention Mask Leaking Future Tokens",
                consequence="Masking torch.tril (the lower triangle) instead of the upper triangle zeroes out earlier tokens and allows attention to attend to future tokens.",
                diagnostic_explanation="Use torch.triu with diagonal=1 to construct the causal future mask.",
                competency_id="mlai.core.l3_transformer_attn",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-02-LEAK",
                line_number=19,
                category=DefectCategory.DATA_LEAKAGE,
                severity=DefectSeverity.CRITICAL,
                title="Target Label Injection into Intermediate Context Embeddings",
                consequence="Concatenating ground truth labels directly into hidden representations gives the decoder direct access to target labels.",
                diagnostic_explanation="Remove ground truth target label concatenation from the autoregressive forward pass.",
                competency_id="mlai.eval.l2_leakage_audit",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-02-METRIC",
                line_number=22,
                category=DefectCategory.METRIC_MISALIGNMENT,
                severity=DefectSeverity.MAJOR,
                title="Unweighted Pooled Loss Across Non-Independent Sequence Steps",
                consequence="Averaging representations across attention heads before computing cross entropy corrupts token loss weighting.",
                diagnostic_explanation="Compute per-token cross entropy across vocabulary logits without invalid head averaging.",
                competency_id="mlai.eval.l2_leakage_audit",
                points=1.0,
            ),
        ],
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )
    scen_leak = PracticeScenario(
        id="SCEN-MLAI-02-LEAK",
        title="Diagnostic Review: Autoregressive Decoder Attention Block",
        description="Inspect a transformer causal self-attention implementation for future token leakage, target label contamination, and non-independent validation pooling.",
        role_family=RoleFamily.MLAI,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="mlai.core.l3_transformer_attn",
        secondary_competency_ids=["mlai.eval.l2_leakage_audit"],
        artifact=artifact_leak,
        rubric=rubric_leak,
        variants=[
            ScenarioVariant(
                variant_id="VAR-LLAMA-ATTN",
                description="Llama-style causal self-attention block with RoPE",
                parameters={"num_heads": "32", "head_dim": "128"},
            ),
            ScenarioVariant(
                variant_id="VAR-GPT-ATTN",
                description="GPT-style causal self-attention with learned positions",
                parameters={"num_heads": "12", "head_dim": "64"},
            ),
        ],
        instructions="Inspect the transformer self-attention block for inverted causal masks, target label leakage, and metric pooling flaws. Flag flawed lines and select categories.",
        disclaimer="Technical practice scenario for capability self-reflection and professional development (Rules R-CR-08, R-CR-11).",
        provenance=provenance_leak,
    )

    # =========================================================================
    # 3. SCEN-MLAI-03-DEPLOY: FastAPI Serving Route
    # =========================================================================
    code_deploy = (
        "import torch\n"
        "from fastapi import FastAPI, HTTPException\n"
        "from pydantic import BaseModel\n"
        "\n"
        "app = FastAPI()\n"
        "GLOBAL_ACTIVATION_CACHE = []\n"
        "\n"
        "class InferenceRequest(BaseModel):\n"
        "    prompt: str\n"
        "    temperature: float = 0.7\n"
        "    max_tokens: int = 1000\n"
        "\n"
        "@app.post('/v1/generate')\n"
        "async def generate_response(req: InferenceRequest):\n"
        "    # Explicit hardware barrier blocks async event loop for concurrent requests\n"
        "    torch.cuda.synchronize()\n"
        "    tokens = tokenizer.encode(req.prompt, return_tensors='pt').cuda()\n"
        "\n"
        "    # Missing maximum generation ceiling allows unbounded token loops\n"
        "    out = model.generate(tokens, max_new_tokens=req.max_tokens * 100)\n"
        "\n"
        "    # Storing unquantized FP32 output tensors in process memory creates GPU memory leak\n"
        "    GLOBAL_ACTIVATION_CACHE.append(out)\n"
        "\n"
        "    decoded = tokenizer.decode(out[0], skip_special_tokens=True)\n"
        "    return {'response': decoded}\n"
    )
    artifact_deploy = ScenarioArtifact(
        content=code_deploy,
        language=ArtifactLanguage.PYTHON,
        line_count=len(code_deploy.strip().split("\n")),
    )
    rubric_deploy = ScenarioRubric(
        scenario_id="SCEN-MLAI-03-DEPLOY",
        defects=[
            SeededDefect(
                id="DEF-MLAI-03-BLOCK",
                line_number=16,
                category=DefectCategory.BLOCKING_CALL,
                severity=DefectSeverity.CRITICAL,
                title="Synchronous CUDA Device Barrier in Asynchronous Event Loop",
                consequence="Invoking torch.cuda.synchronize() inside an async endpoint blocks the main asyncio thread, stalling all incoming requests.",
                diagnostic_explanation="Offload inference to a dedicated thread pool or asynchronous serving runtime (e.g. vLLM engine).",
                competency_id="mlai.ops.l4_quant_serving",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-03-UNBOUNDED",
                line_number=20,
                category=DefectCategory.UNBOUNDED_COLLECTION,
                severity=DefectSeverity.MAJOR,
                title="Unconstrained Generation Budget Without Server Enforcement",
                consequence="Permitting 100x user token budgets without an upper guardrail causes VRAM exhaustion and server timeout denial-of-service.",
                diagnostic_explanation="Enforce strict server-side maximum token limits and use streaming decoders.",
                competency_id="mlai.gen.l3_guardrails",
                points=1.0,
            ),
            SeededDefect(
                id="DEF-MLAI-03-LEAK",
                line_number=23,
                category=DefectCategory.RESOURCE_LEAK,
                severity=DefectSeverity.CRITICAL,
                title="Process-Global In-Memory Tensor Cache Accumulation",
                consequence="Appending output tensors to a global module list retains GPU memory allocations indefinitely, causing Out-Of-Memory crashes.",
                diagnostic_explanation="Do not retain raw GPU tensor activations in unevicted global collections.",
                competency_id="mlai.ops.l4_quant_serving",
                points=1.0,
            ),
        ],
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )
    scen_deploy = PracticeScenario(
        id="SCEN-MLAI-03-DEPLOY",
        title="Diagnostic Review: FastAPI Low-Latency LLM Serving Route",
        description="Inspect an asynchronous FastAPI model serving endpoint for synchronous CUDA blocking, unbudgeted generation length, and process-global tensor caching.",
        role_family=RoleFamily.MLAI,
        target_level=RoleLevel.LEVEL_4_SENIOR,
        primary_competency_id="mlai.ops.l4_quant_serving",
        secondary_competency_ids=["mlai.gen.l3_guardrails"],
        artifact=artifact_deploy,
        rubric=rubric_deploy,
        variants=[
            ScenarioVariant(
                variant_id="VAR-STREAMING-ROUTE",
                description="Server-Sent Events streaming token response route",
                parameters={"engine": "vLLM", "quantization": "AWQ"},
            ),
            ScenarioVariant(
                variant_id="VAR-BATCHED-ROUTE",
                description="Dynamic continuous batching response route",
                parameters={"engine": "TGI", "quantization": "FP8"},
            ),
        ],
        instructions="Inspect the async serving route for CUDA blocking operations, unbounded token allocation, and GPU memory leaks. Flag flawed lines and select categories.",
        disclaimer="Technical practice scenario for capability self-reflection and professional development (Rules R-CR-08, R-CR-11).",
        provenance=provenance_deploy,
    )

    scenarios = {
        "SCEN-MLAI-01-TENS": scen_tens,
        "SCEN-MLAI-02-LEAK": scen_leak,
        "SCEN-MLAI-03-DEPLOY": scen_deploy,
    }

    # Deterministically serialize to config/scenarios/
    file_map = {
        "SCEN-MLAI-01-TENS": "scen_mlai_01_tens.json",
        "SCEN-MLAI-02-LEAK": "scen_mlai_02_leak.json",
        "SCEN-MLAI-03-DEPLOY": "scen_mlai_03_deploy.json",
    }

    for scen_id, scenario in scenarios.items():
        out_file = out_dir / file_map[scen_id]
        payload = scenario.model_dump(mode="json")
        out_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Generated {out_file} (lines: {scenario.artifact.line_count})")

    return scenarios


if __name__ == "__main__":
    generate_mlai_scenarios()
