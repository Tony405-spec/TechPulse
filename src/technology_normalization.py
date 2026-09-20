"""Technology name normalization helpers."""

from __future__ import annotations

from src.common import normalise_name

ALIAS_MAP = {
    ".net": ".NET",
    ".net framework": ".NET Framework",
    "amazon web services (aws)": "AWS",
    "amazon web services": "AWS",
    "aws": "AWS",
    "c#": "C#",
    "c++": "C++",
    "css": "CSS",
    "html/css": "HTML/CSS",
    "javascript": "JavaScript",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "react.js": "React",
    "reactjs": "React",
    "sql server": "SQL Server",
    "typescript": "TypeScript",
}


def normalize_technology_name(value: object) -> str:
    """Normalize a technology name using conservative aliases."""
    raw = str(value).strip()
    if not raw:
        return raw
    key = raw.casefold()
    if key in ALIAS_MAP:
        return ALIAS_MAP[key]
    simplified = normalise_name(raw)
    for alias, canonical in ALIAS_MAP.items():
        if normalise_name(alias) == simplified:
            return canonical
    return raw
