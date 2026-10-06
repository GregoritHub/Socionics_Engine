"""R21B finite paid reuse. Exact owned inputs, never an assessment or answer.

This is a versioned operational accounting choice. Model A prices and physical
prices stay fixed. Cache entries are derived receipts of completed choose work;
the journal remains authoritative and reconstructs every entry on restore.
"""
from dataclasses import fields, replace

from .contracts import WorkStatus
from .clearance_records import EpisodeResourceContract
from .individuation_records import CircuitCommand, CircuitTransaction, CircuitMessage
from .individuation_logic import constraints
from .resource_contracts import V3_ID, V3_CONTROLS, V4_ID, V4_CONTROLS


def semantic_key(context, offer, option, menu):
    """Normalize instance labels only; preserve all predicate-relevant values."""
    values = tuple((f.name, option.observed_epoch-offer.epoch if f.name == 'observed_epoch'
                    else getattr(option, f.name)) for f in fields(option) if f.name != 'key')
    return (context, offer.partner, values, offer.due, offer.budget, offer.credits,
            offer.minimum_output, dict(menu.permissions).get(option.key, False),
            dict(menu.acknowledgments).get(option.key, False))


class PaidWorkReuse:
    def __init__(self, *args, **kwargs):
        self._work_contract = None
        self._paid_option_cache = {}
        self._paid_choice_groups = {}
        super().__init__(*args, **kwargs)

    def _work_mode(self):
        c = self._work_contract
        if c is None or c.protocol_id not in (V3_ID,V4_ID)+V3_CONTROLS+V4_CONTROLS:
            return 'legacy_cost'
        return 'reuse' if c.protocol_id in (V3_ID,V4_ID) else c.protocol_id.rsplit('.', 1)[1]

    def _paid_entry(self, actor, key):
        if self._work_mode() != 'reuse':
            return None
        entry = self._paid_option_cache.get(actor, {}).get(key)
        if entry is None or not all(self._evidence_live(r) for r in entry[1]):
            return None
        # Bulletin/menu are this actor's permitted observations. The event is
        # the receipt of that actor's own completed work.
        if not all(r in self._known[actor] for r in entry[1][1:]):
            return None
        return entry

    def _choose_quote(self, order):
        f = order.offer
        menu = self._read_circuit(f.learner, order.menu, CircuitMessage)
        unseen = set(); receipts = []
        for option in f.options:
            key = semantic_key(self.config.context, f, option, menu)
            entry = self._paid_entry(f.learner, key)
            if entry is None: unseen.add(key)
            else: receipts.extend(entry[1])
        group = self._epoch_orders.get((f.learner, f.partner, f.epoch), ())
        visible = sum(self._circuit_orders[k].bulletin in self._known[f.learner] for k in group)
        return 2+2*len(f.options)+8*len(unseen)+visible, tuple(dict.fromkeys(receipts))

    def _prepare_circuit(self, command):
        job = super()._prepare_circuit(command)
        if self._work_mode() == 'legacy_cost':
            return job
        order = self._circuit_orders.get(command.order)
        op = command.operator; receipts = ()
        if order is None or op == 'withdraw': extent = 2
        elif op in ('menu', 'refresh'): extent = 2+2*len(order.offer.options)
        elif op == 'choose': extent, receipts = self._choose_quote(order)
        elif op == 'review': extent = 5
        elif op in ('coordinate', 'organize'): extent = 3
        elif op == 'apply': extent = 11
        elif op in ('inspect', 'consult'):
            extent = 3+len(self._records[order.outcome].errors)
        elif op == 'feedback':
            extent = 3+len(order.uses)+8*len(order.provisional)+len(self._records[order.signal].errors)
        else: raise ValueError('unknown paid circuit extent')
        old_extent = 2 if order is None else 2+len(order.offer.options)*8
        price, remainder = divmod(job.plan.content_units, old_extent)
        if remainder or price < 1: raise ValueError('invalid inherited circuit price')
        return replace(job, plan=replace(job.plan, content_units=extent*price),
                       basis=tuple(dict.fromkeys(job.basis+receipts)))

    def _circuit_basis_stale(self, job):
        if self._work_mode() == 'legacy_cost': return False
        frozen = self._paid_choice_groups.get((job.command.actor, job.command.task_id))
        return (any(not self._evidence_live(r) for r in job.basis)
                or frozen is not None and frozen != self._visible_group(job.command.order))

    def _visible_group(self, key):
        f = self._circuit_orders[key].offer
        return tuple(self._circuit_orders[k].ref
                     for k in self._epoch_orders.get((f.learner, f.partner, f.epoch), ())
                     if self._circuit_orders[k].bulletin in self._known[f.learner])

    def _visible_option_predicates(self, offer, menu):
        """Called only during completed paid choice; no cache mutation here."""
        local = {}; rows = []
        for option in offer.options:
            key = semantic_key(self.config.context, offer, option, menu)
            if key not in local:
                entry = self._paid_entry(offer.learner, key)
                local[key] = dict(entry[0]) if entry is not None else constraints(
                    offer, option, dict(menu.permissions), dict(menu.acknowledgments))
            rows.append(dict(local[key]))
        return rows

    def _actual_menu(self, order):
        if self._work_mode() == 'legacy_cost' or order.chosen is None:
            return super()._actual_menu(order)
        # Review and enactment use the selected option, and check the actual
        # partner afresh. Cached testimony can never authorize physical work.
        p = self._work_partners[order.offer.partner]
        selected = tuple(o for o in order.offer.options if o.key == order.chosen)
        return (tuple((o.key, o.license in p.licenses) for o in selected),
                tuple((o.key, p.willing and o.start not in p.unavailable_slots
                       and o.load <= p.max_load) for o in selected))

    def _commit(self, tx):
        # Obtain the paid result before superclass publication changes an order.
        staged = []
        c = tx.command
        if (self._work_mode() != 'legacy_cost' and type(c) is CircuitCommand
                and c.operator == 'choose'):
            k = c.actor, c.task_id
            # Frozen derived input: replay reconstructs it at the first paid
            # quantum. A new offer or changed commitment cannot ride on a quote
            # paid against a smaller/different visible group.
            if tx.event.outcome in (WorkStatus.PARTIAL, WorkStatus.DEFERRED):
                self._paid_choice_groups.setdefault(k, self._visible_group(c.order))
            else: self._paid_choice_groups.pop(k, None)
        if (self._work_mode() == 'reuse' and type(tx) is CircuitTransaction
                and type(c) is CircuitCommand and c.operator == 'choose'
                and tx.event.outcome == WorkStatus.COMPLETED):
            order = self._circuit_orders[c.order]
            f = order.offer; menu = self._read_circuit(c.actor, order.menu, CircuitMessage)
            rows = self._visible_option_predicates(f, menu)
            for option, values in zip(f.options, rows):
                key = semantic_key(self.config.context, f, option, menu)
                if self._paid_entry(c.actor, key) is None:
                    staged.append((key, (tuple(values.items()), (tx.event.ref, order.bulletin, menu.ref))))
        super()._commit(tx)
        if type(c) is EpisodeResourceContract: self._work_contract = c
        if staged: self._paid_option_cache.setdefault(c.actor, {}).update(staged)
