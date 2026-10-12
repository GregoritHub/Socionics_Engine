"""Model-matched initial creation only; never refill a running world."""
from dataclasses import replace
from hle_unified.material import OperationStore, attrs, attributes
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine

def factory(model, energy=200000, time=200000, engine_class=WorkflowFinalSelectionEngine):
    def create(world, law):
        fresh = OperationStore()
        for tx in world.journal():
            versions=[]
            for v in tx.versions:
                d=attrs(v)
                if d.get('record_type')=='wallet':
                    assert v.ref.revision == 1
                    d.update(energy=energy, initial_energy=energy, time=time, initial_time=time)
                    v=replace(v, attributes=attributes(d))
                versions.append(v)
            fresh.commit(tx.key, tx.writer, tuple(versions), tx.lineage, actor=tx.actor)
        return engine_class.create(fresh, law, resource_model=model)
    return create
