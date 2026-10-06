from itertools import product
import unittest

from hle.contracts import WorkStatus
from hle.demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from hle.world import World
from hle.world_records import Attempt, TRANSFER, INSPECT
from hle_unified import legacy, codec
from tests.reference_world import fold


class MatchedSequences(unittest.TestCase):
    def test_all_216_three_action_sequences_through_the_common_adapter(self):
        choices = ((ALICE, TRANSFER, (BOX, BOB)), (BOB, TRANSFER, (BOX, ALICE)),
                   (ALICE, TRANSFER, (TOOL, BOB)), (BOB, TRANSFER, (TOOL, ALICE)),
                   (ALICE, INSPECT, (BOX,)), (BOB, INSPECT, (TOOL,)))
        for sequence in product(range(6), repeat=3):
            with self.subTest(sequence=sequence):
                w = World(config())
                bridge = legacy.LegacyWorldBridge(config())
                owners, budget = {BOX: ALICE, TOOL: BOB}, {ALICE: 20, BOB: 20}
                for index, token in enumerate(sequence):
                    actor, operation, inputs = choices[token]
                    success = operation == INSPECT or owners[inputs[0]] == actor
                    budget[actor] -= 1 if operation == INSPECT else 2
                    if success and operation == TRANSFER:
                        owners[inputs[0]] = inputs[1]
                    cmd = Attempt(str(index), str(index), request(actor, operation, inputs))
                    baseline = w.execute(cmd)
                    migrated = bridge.execute_adapted(legacy.adapt(cmd))
                    self.assertEqual(legacy.recover_object(migrated), baseline)
                    self.assertEqual(baseline.outcome, WorkStatus.COMPLETED if success else WorkStatus.FAILED)
                    self.assertEqual(w.state(), fold(w.config, w.truth.journal()))
                    for participant in (ALICE, BOB):
                        av, cursor = bridge.participant_input(legacy.adapt_ref(participant))
                        self.assertEqual((legacy.recover(av), cursor), w.participant_input(participant))
                        self.assertEqual(w.truth.wallet(participant).energy, budget[participant])
                    for item in (BOX, TOOL):
                        last = bridge.ownership_history(legacy.adapt_ref(item))[-1]
                        self.assertEqual(legacy.recover_object(last).object, owners[item])
                checkpoint = codec.loads(codec.dumps(bridge.checkpoint()))
                restored = legacy.LegacyWorldBridge.restore(checkpoint)
                self.assertEqual(restored.legacy_checkpoint(), w.checkpoint())


if __name__ == "__main__":
    unittest.main()
