"""Freeze identity and the confirmatory gate for IrrevOps v3
(pre-registration v3 SS10, SS14; review blocker B2).

The freeze block is a JSON object inside an HTML comment in
docs/PREREGISTRATION_V3.md:

    <!-- freeze-v3
    { "status": "FROZEN", "freeze_tag": "freeze-v3", "task_set_sha256": ...,
      "runpath_sha256": ..., "prompts_sha256": ..., "regime": "default",
      "arms": [...], "reps": [7001, 7002, 7003],
      "backbones": { "A": { "agent_role": null, "realised_model": ...,
                            "monitor_role": "Monitor", "monitor_realised_model": ...,
                            "t2": ..., "t4": ..., "l5b_lo": ...,
                            "cal_bare_harm_decidable": ..., "cal_bare_harm_undecidable": ... } } }
    -->

A confirmatory (ops-) campaign starts only if the block says FROZEN, its
hashes equal the current tree, the tag exists and is an ancestor of HEAD,
and the requested run is exactly what the block fixes.
"""
import hashlib
import json
import os
import re
import subprocess

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
PREREG = os.path.join(ROOT, "docs", "PREREGISTRATION_V3.md")
REQUIRED_BACKBONE_FIELDS = ("agent_role", "realised_model", "monitor_role", "monitor_realised_model",
                            "t2", "t4", "l5b_lo", "cal_bare_harm_decidable", "cal_bare_harm_undecidable")


def runpath_files() -> list:
    """Every file that decides what a confirmatory episode does or how it
    is analysed: all of src/irrevops (runner, world, tasks, controls,
    calibration, analysis), the client, roles, config and the ledger code."""
    files = []
    d = os.path.join(ROOT, "src", "irrevops")
    for dirpath, _dirs, names in os.walk(d):
        files += [os.path.join(dirpath, n) for n in names if n.endswith(".py")]
    files += [os.path.join(ROOT, "src", n) for n in ("llm_client.py", "roles.py", "config.py")]
    files.append(os.path.join(ROOT, "src", "eval", "run_arena.py"))
    return sorted(files)


def runpath_sha256() -> str:
    h = hashlib.sha256()
    for p in runpath_files():
        h.update(os.path.relpath(p, ROOT).replace(os.sep, "/").encode())
        with open(p, "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()


def prompts_sha256() -> str:
    """Every string a model is shown by the harness itself."""
    from . import agent, controls, world
    parts = [agent.SYSTEM, controls.RULE, controls.VERIFIER_SYSTEM, world.TOOL_DOC,
             controls.verifier_user("<ticket>", "<transcript>", "<tool>", {"a": 1}),
             str(agent.MAX_STEPS), str(agent.OUTPUT_CLIP)]
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def parse_block(text: str) -> dict:
    m = re.search(r"<!--\s*freeze-v3\s*(\{.*?\})\s*-->", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _tag_is_ancestor(tag: str) -> bool:
    try:
        subprocess.check_call(["git", "-C", ROOT, "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def problems(campaign: str, backbone: str, arms, reps, splits, reasoning_effort, prereg_path: str = None,
             task_set: str = None, check_tag=_tag_is_ancestor) -> list:
    """Reasons a confirmatory campaign may not start. Empty = may start."""
    path = prereg_path or PREREG
    blk = parse_block(open(path, encoding="utf-8").read()) if os.path.exists(path) else {}
    if not blk:
        return ["no freeze-v3 block in the pre-registration"]
    out = []
    if blk.get("status") != "FROZEN":
        out.append(f"pre-registration status is {blk.get('status')!r}, not FROZEN")
    if blk.get("runpath_sha256") != runpath_sha256():
        out.append("runpath_sha256 does not match the current tree")
    if blk.get("prompts_sha256") != prompts_sha256():
        out.append("prompts_sha256 does not match the current prompts")
    if task_set is None:
        from .tasks import task_set_sha256
        task_set = task_set_sha256()
    if blk.get("task_set_sha256") != task_set:
        out.append("task_set_sha256 does not match the current task set")
    tag = blk.get("freeze_tag")
    if not tag or not check_tag(tag):
        out.append(f"freeze tag {tag!r} is missing or not an ancestor of HEAD")
    bb = (blk.get("backbones") or {}).get(backbone)
    if not isinstance(bb, dict):
        out.append(f"backbone {backbone!r} is not in the freeze block")
    else:
        missing = [k for k in REQUIRED_BACKBONE_FIELDS if k not in bb]
        if missing:
            out.append(f"backbone {backbone}: freeze block lacks {missing}")
    if sorted(arms) != sorted(blk.get("arms") or []):
        out.append(f"arms must be exactly the frozen arms {blk.get('arms')}")
    if sorted(reps) != sorted(blk.get("reps") or []):
        out.append(f"repetitions must be exactly {blk.get('reps')}")
    if set(splits) != {"test"}:
        out.append("a confirmatory campaign runs the test split and nothing else")
    regime = blk.get("regime", "default")
    if (reasoning_effort or "default") != regime:
        out.append(f"reasoning regime must be {regime!r}")
    if not campaign.startswith(f"ops-{backbone}-"):
        out.append(f"campaign must be named ops-{backbone}-<nn>")
    return out


def backbone_config(backbone: str, prereg_path: str = None) -> dict:
    blk = parse_block(open(prereg_path or PREREG, encoding="utf-8").read())
    return dict(blk["backbones"][backbone])
