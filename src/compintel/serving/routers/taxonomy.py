"""Taxonomy and reference lookup endpoints (architecture.md Section 11)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from compintel.schema.enums import MetroLocation, RoleFamily

router = APIRouter(prefix="/v1/taxonomy", tags=["Taxonomy"])

_OCCUPATIONS: list[dict[str, Any]] = [
    {
        "id": RoleFamily.SWE.value,
        "name": "Software Engineering",
        "description": "Software development across backend, frontend, fullstack, cloud & systems.",
        "examples": [
            "Software Engineer",
            "Backend Developer",
            "Frontend Engineer",
            "Full Stack Engineer",
        ],
    },
    {
        "id": RoleFamily.DATA.value,
        "name": "Data Science & Engineering",
        "description": "Data analytics, data pipelining, business intelligence and data science.",
        "examples": ["Data Scientist", "Data Engineer", "Analytics Engineer", "BI Analyst"],
    },
    {
        "id": RoleFamily.MLAI.value,
        "name": "Machine Learning & AI",
        "description": "Machine learning systems, generative AI, deep learning and research.",
        "examples": ["ML Engineer", "AI Engineer", "MLOps Engineer", "ML Researcher"],
    },
    {
        "id": RoleFamily.OTHER.value,
        "name": "Other Technical Roles",
        "description": "Technical and adjacent occupations outside primary engineering categories.",
        "examples": ["Technical Program Manager", "Solutions Architect", "QA Automation Engineer"],
    },
]

_LOCATIONS: list[dict[str, Any]] = [
    {
        "id": MetroLocation.BENGALURU.value,
        "name": "Bengaluru",
        "state": "Karnataka",
        "tier": 1,
        "aliases": ["Bangalore", "BLR"],
    },
    {
        "id": MetroLocation.HYDERABAD.value,
        "name": "Hyderabad",
        "state": "Telangana",
        "tier": 1,
        "aliases": ["HYD", "Cyberabad"],
    },
    {
        "id": MetroLocation.PUNE.value,
        "name": "Pune",
        "state": "Maharashtra",
        "tier": 1,
        "aliases": ["PNQ"],
    },
    {
        "id": MetroLocation.MUMBAI.value,
        "name": "Mumbai",
        "state": "Maharashtra",
        "tier": 1,
        "aliases": ["BOM", "Bombay"],
    },
    {
        "id": MetroLocation.NCR.value,
        "name": "National Capital Region (NCR)",
        "state": "Delhi / Haryana / Uttar Pradesh",
        "tier": 1,
        "aliases": ["Delhi", "Gurgaon", "Gurugram", "Noida"],
    },
    {
        "id": MetroLocation.CHENNAI.value,
        "name": "Chennai",
        "state": "Tamil Nadu",
        "tier": 1,
        "aliases": ["Madras", "MAA"],
    },
    {
        "id": MetroLocation.OTHER.value,
        "name": "Other Indian Metros / Non-Metro",
        "state": "India",
        "tier": 2,
        "aliases": ["Tier-2", "Remote"],
    },
]


@router.get("/occupations", summary="List and search canonical role families")
async def list_occupations(
    q: str | None = Query(default=None, description="Search term filter"),
) -> dict[str, Any]:
    """Retrieve supported canonical occupational categories."""
    if not q:
        return {"total": len(_OCCUPATIONS), "items": _OCCUPATIONS}

    query = q.strip().lower()
    matches = [
        item
        for item in _OCCUPATIONS
        if query in item["name"].lower()
        or query in item["id"].lower()
        or any(query in ex.lower() for ex in item.get("examples", []))
    ]
    return {"total": len(matches), "query": q, "items": matches}


@router.get("/locations", summary="List and search supported metro locations")
async def list_locations(
    q: str | None = Query(default=None, description="Search term filter"),
) -> dict[str, Any]:
    """Retrieve supported Indian technology metro tech hubs."""
    if not q:
        return {"total": len(_LOCATIONS), "items": _LOCATIONS}

    query = q.strip().lower()
    matches = [
        item
        for item in _LOCATIONS
        if query in item["name"].lower()
        or query in item["id"].lower()
        or query in item.get("state", "").lower()
        or any(query in alias.lower() for alias in item.get("aliases", []))
    ]
    return {"total": len(matches), "query": q, "items": matches}
