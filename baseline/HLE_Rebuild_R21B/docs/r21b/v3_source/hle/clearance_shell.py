"""R19 adapter authenticates the R17 conditional view at the old monitor.

Historical sign predicates are unchanged. The old R16 adapter only knew a
concept relation, so a legitimate conditional confirmation could incorrectly
raise a view-mismatch diagnostic after R17. This adapter follows raw paid uses.
"""
from .shell_runtime import ShellJournalMonitor
from .conversion_records import ConversionTransaction
from .compensation_records import DEPENDENCY
from .contracts import WorkStatus

class ConversionShellMonitor(ShellJournalMonitor):
    def __init__(self,*args,material_access=True,**kwargs):
        super().__init__(*args,**kwargs)
        self.converted_studies={};self.converted_uses={};self.converted_caps={}
        self.converted_access={};self.default_access=material_access

    def feed(self,tx):
        if type(tx) is ConversionTransaction:
            a=tx.command.actor
            if tx.study is not None:self.converted_studies[a]=tx.study
            if tx.capacity is not None:self.converted_caps[a]=tx.capacity
            if tx.use is not None:self.converted_uses[a,tx.use.loan]=tx.use
            if tx.event.outcome==WorkStatus.COMPLETED and tx.command.operator in ('restrict','restore_access'):
                self.converted_access[a]=tx.command.operator=='restore_access'
        super().feed(tx)

    def _dependency_matches(self,v,concept):
        s=self.converted_studies.get(v.owner)
        if s is None:return super()._dependency_matches(v,concept)
        use=self.converted_uses.get((v.owner,v.loan));cap=self.converted_caps.get(v.owner)
        valid=use is not None and use.terms==v.terms and self.converted_access.get(v.owner,self.default_access)
        if valid:
            valid=(s.active and not s.paused and s.candidate==use.rule) if use.capacity is None else (
                cap is not None and cap.current and cap.ref==use.capacity and cap.rule==use.rule)
        original=self.records.get(s.concept_origin)
        expected=use.required if valid else original is not None and DEPENDENCY in original.relations
        return v.dependency==expected
