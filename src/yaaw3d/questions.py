from __future__ import annotations

from typing import Any

from .contracts import Choice, Question


def _q(
    id: str,
    prompt: str,
    a: str,
    b: str,
    c: str,
    recommendation: str,
    rationale: str,
) -> Question:
    return Question(
        id=id,
        prompt=prompt,
        choices=(Choice("A", a), Choice("B", b), Choice("C", c)),
        recommendation=recommendation,
        rationale=rationale,
    )


QUESTION_BANK: tuple[Question, ...] = (
    _q("purpose", "What is the primary use of this asset?", "Still/product render", "Real-time/game asset", "Film/VFX/animation asset", "B", "Purpose determines topology, budgets, shading, and delivery."),
    _q("quality", "What production quality is required?", "Blockout/concept", "Production-ready", "Hero/cinematic", "B", "Quality controls refinement depth and acceptance thresholds."),
    _q("style", "What visual target should control the build?", "Photorealistic", "Stylized", "Low-poly/graphic", "A", "Style affects geometry language, materials, and criticism."),
    _q("geometry", "How much detail must exist as real geometry?", "Mostly silhouette; bake/texture small detail", "Model important seams/forms; texture microdetail", "Model nearly all visible construction detail", "B", "This prevents an execution agent from choosing an arbitrary representation."),
    _q("topology", "What topology target should be used?", "Fast/editable; topology secondary", "Clean production topology / subdivision-ready where needed", "Strict deformation/hero topology", "B", "Topology quality must match the downstream use."),
    _q("physical_accuracy", "How physically/dimensionally accurate should it be?", "Visual approximation", "Reference-faithful proportions", "Measured/engineering-level dimensions", "B", "Accuracy changes research and validation requirements."),
    _q("materials", "What material fidelity is expected?", "Simple procedural/lookdev", "Production PBR", "Hero PBR with micro-surface variation", "B", "Material fidelity affects UV, maps, and render validation."),
    _q("animation", "What motion requirement exists?", "None/static", "Simple transform/turntable/rigid motion", "Rigged/deforming/physics-aware animation", "A", "Animation changes topology, rigging, and QA."),
    _q("presentation", "How should the asset be presented for review?", "Neutral studio", "Context/environment", "Match a supplied shot/reference", "A", "Review views and lighting need a defined target."),
    _q("delivery", "What delivery target should be treated as authoritative?", ".blend working file", "Game/web interchange (FBX/GLB/USD)", "Render/VFX package", "A", "Export rules and validators depend on the target."),
    _q("condition", "What condition/age should the asset show?", "New/clean", "Lightly used", "Heavily worn/damaged", "A", "Wear is a material and geometry decision, not an execution-agent guess."),
    _q("scale", "How should scale be handled?", "Plausible visual scale", "Real-world scale", "Exact supplied dimensions", "B", "Correct scale affects shaders, physics, camera, and export."),
    _q("uv", "What UV/texturing strategy is required?", "Procedural/no authored UV requirement", "Unique UVs with consistent texel density", "UDIM/hero texture workflow", "B", "The texture workflow must be known before lookdev."),
    _q("lod", "What optimization/LOD requirement exists?", "None", "Single optimized production mesh", "LOD chain / platform budgets", "A", "Optimization affects modeling and delivery."),
    _q("references", "How should references constrain the result?", "Mood/style only", "Match proportions and construction", "Near-exact visual match", "B", "The critic needs to know how strict reference comparison should be."),
    _q("camera", "What camera constraint exists?", "No fixed camera", "Primary hero camera plus turntable views", "Exact lens/framing/shot match", "B", "A camera contract prevents scene presentation drift."),
    _q("lighting", "What lighting constraint exists?", "Neutral evaluation light", "Designed studio/environment light", "Match supplied lighting", "A", "Critique should separate asset faults from lighting choices."),
    _q("engine", "What render engine should previews target?", "EEVEE", "Cycles", "Engine-agnostic/material preview", "B", "Shader and sampling decisions vary by engine."),
    _q("physics", "What physical simulation requirement exists?", "None", "Basic rigid-body/collision", "Deformation/cloth/soft-body/advanced simulation", "A", "Simulation adds measurable acceptance criteria."),
    _q("naming", "How strict should scene organization be?", "Minimal", "Production naming/collections", "Pipeline-specific naming convention", "B", "Scene hygiene is part of production readiness."),
)

BASE_REQUIRED: tuple[str, ...] = tuple(q.id for q in QUESTION_BANK[:10])


def by_id() -> dict[str, Question]:
    return {q.id: q for q in QUESTION_BANK}


def required_ids(answers: dict[str, Any]) -> list[str]:
    """Return only questions materially required by choices already made."""
    required = set(BASE_REQUIRED)

    def choice(qid: str) -> str | None:
        raw = answers.get(qid)
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            return raw.get("choice")
        return None

    if choice("purpose") == "B" or choice("delivery") == "B":
        required.update({"lod", "scale", "uv", "naming"})
    if choice("quality") == "C":
        required.update({"condition", "scale", "uv", "references", "camera", "lighting", "engine"})
    if choice("materials") == "C":
        required.update({"condition", "uv", "lighting", "engine"})
    if choice("animation") in {"B", "C"}:
        required.add("physics")
    if choice("animation") == "C":
        required.add("scale")
    if choice("presentation") in {"B", "C"}:
        required.update({"camera", "lighting", "engine"})
    if choice("presentation") == "C":
        required.add("references")
    if choice("physical_accuracy") == "C":
        required.update({"scale", "references"})

    # Canonical bank order keeps batches stable and reproducible.
    return [q.id for q in QUESTION_BANK if q.id in required]


def next_batch(answers: dict[str, Any], batch_size: int = 10) -> list[Question]:
    answered_ids = set(answers)
    needed = set(required_ids(answers))
    unresolved = [q for q in QUESTION_BANK if q.id in needed and q.id not in answered_ids]
    return unresolved[:batch_size]
