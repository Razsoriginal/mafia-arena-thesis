"""Provider roles: one key per role, no silent fallback, no borrowing.

Each role is configured by exactly three variables in .env:
    <Role>_Base_Url, <Role>_API_Key, <Role>_Model
A missing variable raises RoleNotConfigured. Nothing here falls back to
another role or to the legacy LLM_* names. The primary backbone
(`AiCredits_*`) stays in src/config.py.
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv(override=True)

ROLES = ("BackboneB", "BackboneC", "Monitor", "Reviewer", "Author", "Judge")


class RoleNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class RoleConfig:
    role: str
    base_url: str
    model: str
    api_key: str = field(repr=False)

    def __str__(self):
        return f"RoleConfig(role={self.role}, base_url={self.base_url}, model={self.model})"


def role_config(role: str) -> RoleConfig:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; known roles: {', '.join(ROLES)}")
    vals, missing = {}, []
    for part in ("Base_Url", "API_Key", "Model"):
        name = f"{role}_{part}"
        v = os.getenv(name, "").strip()
        if not v:
            missing.append(name)
        vals[part] = v
    if missing:
        raise RoleNotConfigured(f"role {role} is not configured: set {', '.join(missing)} in .env")
    return RoleConfig(role=role, base_url=vals["Base_Url"], model=vals["Model"], api_key=vals["API_Key"])


def assert_distinct_keys(role_names) -> None:
    """Refuse a run in which two roles would spend from the same key."""
    seen = {}
    for r in role_names:
        k = role_config(r).api_key
        if k in seen:
            raise RoleNotConfigured(f"roles {seen[k]} and {r} share one API key; use one key per role")
        seen[k] = r
