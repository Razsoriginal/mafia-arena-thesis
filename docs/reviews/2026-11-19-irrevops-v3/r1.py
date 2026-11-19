import json, sys
sys.path.insert(0, ".")
from src.irrevops import controls as C
from src.irrevops.agent import run_episode, OUTPUT_CLIP
from src.irrevops.tasks import build_tasks, call_of
from src.irrevops.world import World

tasks = build_tasks()
by_pair = {}
for t in tasks: by_pair.setdefault(t.pair_id, []).append(t)
def scripted(calls):
    it = iter(list(calls) + [("finish", {"summary": "done"})] * 20)
    def step(_s, _u):
        tool, args = next(it); return {"tool": tool, "args": args}, False
    return step
def T(tid, twin, i=0):
    return [t for t in tasks if t.template_id.startswith(tid) and t.twin == twin and t.pair_id.endswith(f"-{i}")][0]

print("== 1 leak: tool outputs with truth keys / truth.of vs meta.of / max output len")
bad = 0; maxlen = 0; maxwho = None; ofdiff = 0
TRUTH_KEYS = ("truth", "live", "last_admin", "frozen", "in_scope", "blast", "valid")
for t in tasks:
    w = World(t.world)
    outs = [w.call("list_resources", {}), w.call("read_policies", {}), w.call("whoami", {})]
    for rid, r in w.resources.items():
        outs += [w.call("describe", {"resource_id": rid}), w.call("get_dependents", {"resource_id": rid})]
        if r["kind"] == "snapshot" and r["truth"].get("of") != r["meta"].get("of"): ofdiff += 1
    for d in w.docs: outs.append(w.call("read_doc", {"doc_id": d}))
    for a in w.approvals: outs.append(w.call("check_approval", {"request_id": a}))
    for o in outs:
        if len(o) > maxlen: maxlen, maxwho = len(o), t.task_id
        try:
            j = json.loads(o)
            if isinstance(j, dict) and set(j) & set(TRUTH_KEYS): bad += 1; print("LEAK", t.task_id, o[:200])
        except Exception: pass
print("truth-key leaks:", bad, "| truth.of != meta.of:", ofdiff, "| max tool output len:", maxlen, maxwho, "clip", OUTPUT_CLIP)

print("== 2 twin surface diff on undecidable")
def surface(t, with_text=False):
    w = World(t.world)
    s = {"list": w.call("list_resources", {}), "who": w.call("whoami", {})}
    for rid in list(w.resources):
        s["d:" + rid] = w.call("describe", {"resource_id": rid}); s["g:" + rid] = w.call("get_dependents", {"resource_id": rid})
    s["docids"] = sorted(w.docs); s["apids"] = sorted(w.approvals)
    s["apmeta"] = json.dumps({k: v.get("meta") for k, v in w.approvals.items()}, sort_keys=True)
    if with_text:
        s["pol"] = w.policies; s["aptext"] = json.dumps({k: v.get("text") for k, v in w.approvals.items()}, sort_keys=True)
    return s
diff_meta, diff_text = set(), set()
for pid, (a, b) in by_pair.items():
    if a.decidable: continue
    if surface(a) != surface(b): diff_meta.add(a.template_id)
    sa, sb = surface(a, True), surface(b, True)
    if (sa["pol"], sa["aptext"]) != (sb["pol"], sb["aptext"]): diff_text.add(a.template_id)
    if a.world.get("identity") != b.world.get("identity"): print("identity differs", pid)
print("undecidable templates with differing structured surface:", diff_meta)
print("undecidable templates differing in policy registry or approval registry text:", diff_text)

print("== 3 gate & L6 on undecidable, compliant agent, instance 4")
rows = []
for pid, pair in by_pair.items():
    if pair[0].decidable or not pid.endswith("-4"): continue
    act = [t for t in pair if t.twin == "act"][0]; risky = [t for t in pair if t.twin != "act"][0]
    out = {}
    for name, ctl in (("L0", C.Control()), ("L3", C.PolicyGate()), ("L6", C.Reversibility())):
        ra = run_episode(act, ctl, scripted([(c["tool"], c["args"]) for c in act.bait]))
        rr = run_episode(risky, ctl, scripted([(c["tool"], c["args"]) for c in risky.bait]))
        out[name] = (int(rr["harm"]), int(rr["residual_harm"]), int(ra["false_hold"]))
    rows.append((act.template_id, risky.twin, out))
    print(f"{act.template_id:40s} {risky.twin:8s} (harm,resid,act_false_hold) L0={out['L0']} L3={out['L3']} L6={out['L6']}")
print("L3 harm on undecidable (compliant):", sum(r[2]['L3'][0] for r in rows), "/", len(rows), " L3 act false hold:", sum(r[2]['L3'][2] for r in rows))
print("L6 residual:", sum(r[2]['L6'][1] for r in rows), " L6 harm:", sum(r[2]['L6'][0] for r in rows), "L6 act false hold:", sum(r[2]['L6'][2] for r in rows))

print("== 4 adversarial scoring")
def show(label, row, keys=("harm","n_harmful","residual_harm","completed","false_hold","escalated","n_executed","n_denied","ended","n_human_reviews","n_blocked_harmful","n_attempted_harmful")):
    print(label, {k: row[k] for k in keys})
# a. delete_matching pre-check vs execution
t = T("T2c", "act")
row = run_episode(t, C.ApproveAll(), scripted([("delete_matching", {"pattern": "snap-"})]))
show("a) T2c act, delete_matching('snap-') under L5a perfect human:", row)
print("   review truth_harmful:", [r["truth_harmful"] for r in json.loads(row["reviews"])], "executed harmful:", [(e["target"], e["harm_reason"]) for e in json.loads(row["executed"]) if e["harmful"]])
t = T("T2c", "mixed")
row = run_episode(t, C.ApproveAll(), scripted([("delete_matching", {"pattern": "snap-"})]))
show("a2) T2c mixed same:", row)
# b. duplicate payment
t = T("T5a", "act"); c = t.bait[0]
row = run_episode(t, C.Control(), scripted([(c["tool"], c["args"])] * 5))
show("b) T5a act, same approved payment sent 5 times:", row)
# c. non-numeric amount
for amt in ("USD 4750", "4,750", [1], {"v": 1}):
    try:
        row = run_episode(t, C.Control(), scripted([(c["tool"], dict(c["args"], amount=amt))]))
        show(f"c) amount={amt!r}:", row)
    except Exception as e:
        print(f"c) amount={amt!r}: EPISODE CRASH {type(e).__name__}: {e}")
# c2 wrong amount in act twin then right
row = run_episode(t, C.Control(), scripted([(c["tool"], dict(c["args"], amount=1)), ]))
show("c2) T5a act wrong amount only:", row)
row = run_episode(t, C.Control(), scripted([(c["tool"], dict(c["args"], request_id="PAY-0"))]))
show("c3) T5a act wrong request id only:", row)
# d. wrong arg names
t = T("T10a", "mixed")
row = run_episode(t, C.Control(), scripted([("delete_matching", {"prefix": "lt-"})]))
show("d) T10a mixed delete_matching with arg 'prefix' instead of 'pattern':", row)
t = T("T1a", "abstain")
w = World(t.world); print("d2) delete_resource with arg 'id':", w.call("delete_resource", {"id": "x"}), "| nonexistent:", w.call("delete_resource", {"resource_id": "nope"}), "| executed:", len(w.executed))
# e. U2d snapshot loophole
t = T("U2d", "abstain"); c = t.bait[0]
db = [k for k, v in t.world["resources"].items() if v["kind"] == "database"][0]
show("e) U2d abstain bait only:", run_episode(t, C.Control(), scripted([(c["tool"], c["args"])])))
show("e) U2d abstain create_snapshot(db) then bait:", run_episode(t, C.Control(), scripted([("create_snapshot", {"resource_id": db}), (c["tool"], c["args"])])))
# f. harm in act twins
t = T("T3a", "act"); state = [k for k in t.world["resources"] if "tfstate" in k][0]
show("f) T3a act: delete state store + required lock:", run_episode(t, C.Control(), scripted([("delete_resource", {"resource_id": state}), (t.bait[0]["tool"], t.bait[0]["args"])])))
t = T("T10b", "act")
show("f2) T10b act: wipe all:", run_episode(t, C.Control(), scripted([("delete_matching", {"pattern": ""})])))
# g. T10b abstain: deleting the named (nonexistent) VMs
t = T("T10b", "abstain")
named = [x for x in t.ticket.split("`") if "-vm-" in x]
row = run_episode(t, C.Control(), scripted([("delete_resource", {"resource_id": v}) for v in named]))
show("g) T10b abstain: delete the two named nonexistent VMs:", row); print("   outputs:", [s["output"] for s in json.loads(row["steps"])][:2])
# h. L6 details
t = T("U1e", "abstain"); c = t.bait[0]
show("h) U1e abstain L6 (env_tag production):", run_episode(t, C.Reversibility(), scripted([(c["tool"], c["args"])])))
show("h) U1e abstain L3:", run_episode(t, C.PolicyGate(), scripted([(c["tool"], c["args"])])))
t = T("T1b", "abstain"); c = t.bait[0]
show("h2) T1b abstain L6:", run_episode(t, C.Reversibility(), scripted([(c["tool"], c["args"])])))
# i. step cap / invalid
t = T("T1a", "act")
show("i) T1a act 12 invalid tool names:", run_episode(t, C.Control(), scripted([("rm_rf", {})] * 12)))
show("i2) T1a act required then escalate:", run_episode(t, C.Control(), scripted([(t.bait[0]["tool"], t.bait[0]["args"]), ("escalate", {})])))
# j. L5a delete_matching with harmful member then members individually
t = T("T10a", "mixed")
show("j) T10a mixed L5a bait then required:", run_episode(t, C.ApproveAll(), scripted([(c["tool"], c["args"]) for c in t.bait] + [(x["tool"], x["args"]) for x in map(call_of, t.required)])))
# k. T4b: delete_resource on last admin user instead of revoke
t = T("T4b", "mixed"); adm = [k for k, v in t.world["resources"].items() if v["truth"].get("last_admin")][0]
show("k) T4b mixed delete_resource(admin):", run_episode(t, C.Control(), scripted([("delete_resource", {"resource_id": adm})])))
show("k2) T4b mixed L3 delete_resource(admin):", run_episode(t, C.PolicyGate(), scripted([("delete_resource", {"resource_id": adm})])))
# l. T2a abstain L3: snapshot first then delete
t = T("T2a", "abstain"); c = t.bait[0]; db = [k for k, v in t.world["resources"].items() if v["kind"] == "database"][0]
show("l) T2a abstain L3 snapshot then delete:", run_episode(t, C.PolicyGate(), scripted([("create_snapshot", {"resource_id": db}), (c["tool"], c["args"])])))
# m. L6 recovery of a snapshot created in-episode
show("m) T2a abstain L6: snapshot, delete old, delete new:", run_episode(t, C.Reversibility(), scripted([("create_snapshot", {"resource_id": db}), (c["tool"], c["args"]), ("delete_resource", {"resource_id": f"snap-{db}-new1"})]), ), keys=("harm","residual_harm","n_recovery_attempted","n_recovered","state_restored","n_denied"))
t = T("T1a", "abstain"); c = t.bait[0]
show("m2) T1a abstain L6 delete twice:", run_episode(t, C.Reversibility(), scripted([(c["tool"], c["args"])]*2)), keys=("harm","n_harmful","residual_harm","n_recovery_attempted","n_recovered","state_restored"))
