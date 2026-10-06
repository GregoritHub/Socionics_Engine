"""Offline U4 audit from raw native transactions, without engine caches.

This deliberately does not call the executor's material transformation or read
its reservations, actor wallets, job tables, or assessment flags. It derives
charges, conflicts, stock sinks and physical results from chronological writes.
"""
from .records import Material, Account, Occurrence, Relation, ChangeKind
from .operation_records import EXTENTS, MATERIAL_OPS


def data(value):
    return {a.name: a.value for a in value.attributes}


def indexed(values, prefix):
    return tuple(values[prefix + str(i)] for i in range(sum(k.startswith(prefix) for k in values)))


def audit_transactions(transactions, *, extent_check=None):
    heads, locks, energy, time = {}, {}, {}, {}
    physical, receipts, attempts, charged = 0, 0, 0, 0
    keys = set()
    for tx in transactions:
        if tx.key in keys:
            raise ValueError("duplicate transaction")
        keys.add(tx.key)
        old = {v.ref.identity: heads.get(v.ref.identity) for v in tx.versions}
        pending = {v.ref.identity: v for v in tx.versions}
        jobs = [v for v in tx.versions if data(v).get("record_type") == "operation"]
        wallets = [v for v in tx.versions if data(v).get("record_type") == "wallet"]
        materials = [v for v in tx.versions if v.facet(Material) is not None and old[v.ref.identity] is not None]
        native_receipts = [v for v in tx.versions if v.ref.identity.namespace == "u4.receipt"]
        if len(jobs) > 1:
            raise ValueError("one work operation per atomic commitment")
        job = jobs[0] if jobs else None
        jd = data(job) if job else {}
        prior = old[job.ref.identity] if job else None
        pd = data(prior) if prior else {}
        delta = 0
        if job:
            attempts += int(prior is None)
            if extent_check is not None and (jd.get("u5") or jd.get("u6") or jd.get("u7") or jd.get("u8") or jd.get("u9") or jd.get("u10") or jd.get("u11")):
                extent_check(jd)
            elif jd["required"] != 1 + EXTENTS[jd["primitive"]] or jd["route_prepare"] != 1 or jd["route_execute"] != EXTENTS[jd["primitive"]]:
                raise ValueError("unearned operation extent")
            delta = jd["completed"] - pd.get("completed", 0)
            if not 0 <= jd["completed"] <= jd["required"] or delta < 0 or jd["spent"] != jd["completed"]:
                raise ValueError("invalid cumulative work")
            if pd and jd["spent"] - pd["spent"] != delta:
                raise ValueError("spent work was erased or forged")
            ids = indexed(jd, "lock.")
            if delta and any(locks.get(i) not in (None, job.ref.identity) for i in ids):
                raise ValueError("paid conflicting reservation")
            if jd["status"] in ("pending", "partial", "ready"):
                if any(locks.get(i) not in (None, job.ref.identity) for i in ids):
                    raise ValueError("double reservation")
                for i in ids:
                    locks[i] = job.ref.identity
            if jd["status"] == "ready" and jd["completed"] != jd["required"]:
                raise ValueError("premature ready state")
            if jd["status"] in ("succeeded", "failed") and (not prior or pd["status"] != "ready"):
                raise ValueError("result without paid ready state")
            if jd["status"] in ("succeeded", "failed", "cancelled"):
                for i in ids:
                    if locks.get(i) == job.ref.identity:
                        del locks[i]
        for wallet in wallets:
            wd, before = data(wallet), old[wallet.ref.identity]
            actor = wd["actor"]
            if before is None:
                if any(type(wd[k]) is not int or wd[k] < 0 for k in ("energy", "time")) or wd["energy"] != wd["initial_energy"] or wd["time"] != wd["initial_time"]:
                    raise ValueError("invalid initial budget")
                energy[actor], time[actor] = wd["energy"], wd["time"]
            else:
                if not job or actor != jd["actor"] or delta < 1:
                    raise ValueError("unexplained resource write")
                if wd["energy"] != energy[actor] - delta or wd["time"] != time[actor] - delta or min(wd["energy"], wd["time"]) < 0:
                    raise ValueError("resource debit does not equal performed work")
                energy[actor], time[actor] = wd["energy"], wd["time"]
        if delta and (len(wallets) != 1 or old[wallets[0].ref.identity] is None):
            raise ValueError("work has no matching budget debit")
        charged += delta
        op = jd.get("primitive")
        successful = job is not None and jd["status"] == "succeeded"
        if materials and (not successful or op not in MATERIAL_OPS - {"inspect"}):
            raise ValueError("material changed without completed physical work")
        if successful and op in MATERIAL_OPS - {"inspect"}:
            expected_ids = {jd[k].identity for k in ("target", "tool", "stock") if jd[k] is not None}
            if {v.ref.identity for v in materials} != expected_ids:
                raise ValueError("physical effect is missing a required resource")
            physical += 1
        for after in materials:
            before = old[after.ref.identity]
            bm, am = before.facet(Material), after.facet(Material)
            bd, ad = data(before), data(after)
            if bm.quantity != am.quantity or bm.unit != am.unit or bm.custodian != jd["actor"]:
                raise ValueError("material conservation or custody violation")
            matching = [e for e in tx.lineage if after.ref in e.outputs]
            if len(matching) != 1 or matching[0].kind != ChangeKind.MATERIAL or not matching[0].evidence or matching[0].evidence[0] != prior.ref:
                raise ValueError("missing paid causal material lineage")
            if before.ref == jd.get("stock"):
                if (bm.owner != jd["actor"] or bm != am or ad["consumed"] != bd["consumed"] + jd["amount"]
                        or ad["consumed"] > am.quantity or ad["consumed"] < 0):
                    raise ValueError("invalid or double stock consumption")
                if op != "consume" and bd["purpose"] != op:
                    raise ValueError("incompatible stock")
            else:
                if before.ref == jd.get("tool") or op == "use":
                    if bd["wear"] >= bd["max_wear"] or bm.condition != "serviceable" or ad["wear"] != bd["wear"] + 1:
                        raise ValueError("unsupported tool use")
                    expected_condition = "damaged" if ad["wear"] == bd["max_wear"] else "serviceable"
                elif op == "repair":
                    if bm.condition != "damaged" or ad["wear"] != 0:
                        raise ValueError("invalid repair")
                    expected_condition = "serviceable"
                elif op == "care":
                    if bm.condition != "serviceable" or bd["wear"] < 1 or ad["wear"] != bd["wear"] - 1:
                        raise ValueError("invalid care")
                    expected_condition = bm.condition
                elif op == "damage":
                    if bm.condition != "serviceable" or ad["wear"] != bd["max_wear"]:
                        raise ValueError("invalid condition change")
                    expected_condition = "damaged"
                else:
                    expected_condition = bm.condition
                    if ad != bd:
                        raise ValueError("custody operation hid a material change")
                if am.condition != expected_condition:
                    raise ValueError("condition does not match performed work")
                owner = jd["recipient"] if op == "transfer" else bm.owner
                custodian = jd["recipient"] if op == "transfer" else (bm.owner if op == "return" else bm.custodian)
                if am.owner != owner or am.custodian != custodian or op == "transfer" and bm.owner != jd["actor"]:
                    raise ValueError("invalid ownership/custody effect")
        if successful and op == "return":
            relation = pending.get(jd["relation"].identity)
            if relation is None or {a.name: a.value for a in relation.facet(Relation).terms}.get("status") != "fulfilled":
                raise ValueError("return omitted obligation change")
        if successful:
            event = pending.get(jd["result"].identity)
            if event is None or event.occurrence != Occurrence.ACTUAL_EVENT or prior.ref not in event.facet(Account).sources:
                raise ValueError("successful result lacks causal actual event")
            ed = data(event)
            if ed["actor"] != jd["actor"] or ed["primitive"] != op or ed["outcome"] != "succeeded":
                raise ValueError("event does not describe its operation")
            if op == "inspect":
                target = heads[jd["target"].identity]
                m = target.facet(Material)
                if ed.get("target") != target.ref or ed.get("owner") != m.owner or ed.get("custodian") != m.custodian or ed.get("condition") != m.condition:
                    raise ValueError("inspection does not match physical state at execution")
        if successful and op in ("read", "bind", "acquire"):
            if len(native_receipts) != 1:
                raise ValueError("processing result has no receipt")
        for receipt in native_receipts:
            rd = data(receipt)
            if (not successful or rd["actor"] != jd["actor"] or rd["operation"] != op
                    or any(rd[k] != jd[k] for k in ("required", "completed", "spent"))):
                raise ValueError("unpaid processing receipt")
            receipts += 1
        for value in tx.versions:
            heads[value.ref.identity] = value
    stocks = []
    for value in heads.values():
        m = value.facet(Material)
        if m is not None and m.condition == "stock":
            consumed = data(value)["consumed"]
            if not 0 <= consumed <= m.quantity:
                raise ValueError("negative availability")
            stocks.append({"key": value.ref.identity.key, "quantity": m.quantity,
                           "available": m.quantity - consumed, "consumed": consumed})
    return {"passed": True, "transactions": len(transactions), "operation_attempts": attempts,
            "charged_energy": charged, "charged_time": charged, "physical_commits": physical,
            "native_processing_receipts": receipts, "stocks": sorted(stocks, key=lambda s: s["key"]),
            "active_reservations": len(locks)}
