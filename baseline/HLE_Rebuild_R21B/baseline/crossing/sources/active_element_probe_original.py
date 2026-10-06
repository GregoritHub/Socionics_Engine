#!/usr/bin/env python3
"""Probe: the active element in the R8/R9 layers (run from the HLE_Rebuild_R10 root).

    python3 active_element_probe.py

Standard library only. Builds small worlds with the shipped demo helpers and reports:
  P1  Profile default active element, per type.
  P2  Active element after language (R8) and organization (R9) operations, per actor.
  P3  Active element after the R6 socion demo (the layer that does move it).
  P4  The element stamped on the wire by senders of every type after Produce.
  P5  Reception charge by receiver type under the shipped default, and the seat Ne occupies there.
Every observation is asserted so that a fix flips the probe from PASS-as-observed to FAIL-as-observed.
"""
import sys, os
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from hle.model_a import TYPES, stack, position_of
from hle.metabolism_records import Profile
from hle.organization_demo import world, ACTORS, ALICE, BOB, CARA, DARA, BOX, train, move, propose, agree, perform
from hle.language_records import Speech, Act, Produce, Learn
from hle.language_demo import acquire, finish, deliver
from hle.socion_records import ReceiveCommand
from hle.socion_demo import run_socion_demo

def hdr(s): print('\n' + s + '\n' + '-' * len(s))

# P1 ------------------------------------------------------------------------------------------
hdr('P1  Profile default active element')
defaults = {t: Profile(ALICE, t).active for t in TYPES}
print('  ', defaults)
assert set(defaults.values()) == {'ne'}, 'default is now type-dependent'
print('   observed: every type defaults to active="ne" (metabolism_records.Profile)')

# P2 ------------------------------------------------------------------------------------------
hdr('P2  Active element through R8 (language) and R9 (organization) operations')
def prepared_typed(types):
    w = world(types=types)
    for a in ACTORS[:3]:
        acc = acquire(w, a, (BOX,), a.key + ':concept'); finish(w, a, Learn('kept', acc), a.key + ':learn')
    for i, peer in enumerate((BOB, CARA)):
        train(w, ALICE, peer, 'example:' + str(i), ('transfer',), 'kept'); move(w, peer, ALICE, 'return:' + str(i))
    return w
w = prepared_typed(('lse', 'iee', 'lsi', 'eii'))
act = lambda a: w.processing_state(a).active
after_training = {a.key: act(a) for a in ACTORS}
p = propose(w, ALICE, 'i'); ident = agree(w, ALICE, p, 'i:a'); perform(w, ALICE, ident, 'i:perf')
after_org = {a.key: act(a) for a in ACTORS}
print('   after training (Learn/Produce/Interpret/enact):', after_training)
print('   after Formulate/Review/Ratify/Perform         :', after_org)
assert set(after_training.values()) == set(after_org.values()) == {'ne'}, 'R8/R9 now move the active element'
print('   observed: neither layer moves the active element')

# P3 ------------------------------------------------------------------------------------------
hdr('P3  Active element after the R6 socion demo')
out = run_socion_demo(); w6 = out[0] if isinstance(out, tuple) else out
final6 = {a.key: w6.processing_state(a).active for a in w6.config.actors}
print('  ', final6)
assert set(final6.values()) != {'ne'}, 'R6 no longer moves the active element'
print('   observed: R6 goals (theorize/apply/embody/understand) do move it')

# P4 ------------------------------------------------------------------------------------------
hdr('P4  Element stamped on the wire after Produce, by sender type')
emitted = {}
for t in TYPES:
    w = prepared_typed(('lse', 'iee', 'lsi', t))
    acc = acquire(w, DARA, (BOX,), 'x:access')
    definition = deliver(w, BOB, w.lexeme(BOB, 'kept').ref, DARA, 'x:definition')
    finish(w, DARA, Learn('kept', acc, definition), 'x:learn')
    speech = Speech('request', (w.word(DARA, 'kept', (BOX, ALICE)),), (Act('transfer', BOX, DARA),))
    finish(w, DARA, Produce(speech), 'x:produce')
    emitted[t] = w.processing_state(DARA).active
print('  ', emitted)
assert set(emitted.values()) == {'ne'}, 'emission is now type-dependent'
print('   observed: every sender type emits "ne" (language.py stamps processing_state(sender).active)')

# P5 ------------------------------------------------------------------------------------------
hdr('P5  Reception charge by receiver type under the shipped default (sender EII emits "ne")')
rows = []
for t in TYPES:
    w = prepared_typed((t, 'iee', 'lsi', 'eii'))
    acc = acquire(w, DARA, (BOX,), 'x:access')
    definition = deliver(w, BOB, w.lexeme(BOB, 'kept').ref, DARA, 'x:definition')
    finish(w, DARA, Learn('kept', acc, definition), 'x:learn')
    speech = Speech('request', (w.word(DARA, 'kept', (BOX, ALICE)),), (Act('transfer', BOX, DARA),))
    utt = finish(w, DARA, Produce(speech), 'x:produce').result
    e0 = w._wallets[ALICE].energy
    w.execute(w.send_language(DARA, utt, ALICE, 'x:tell'))
    obs = [o for o in w._journal[-1].observations if o.observer == ALICE and o.source.kind.value == 'message'][0].ref
    for n in range(10000):
        w.execute(ReceiveCommand(f'x:receive:{n}', 'x:receive', ALICE, obs))
        if (ALICE, obs) in w._completed_reception: break
    rows.append((t, e0 - w._wallets[ALICE].energy, position_of(t, 'ne')))
print('   type  charge  seat-of-Ne')
for t, c, s in sorted(rows, key=lambda r: (r[1], r[0])): print(f'   {t:4}  {c:5}    {s}')
by_seat = {}
for t, c, s in rows: by_seat.setdefault(s, set()).add(c)
assert all(len(v) == 1 for v in by_seat.values()), 'charge no longer a function of the Ne seat alone'
print('   observed: charge is a function of the seat Ne occupies in the receiver, nothing else')

print('\nAll observations reproduced. A fix should make at least one assertion above fail.')
