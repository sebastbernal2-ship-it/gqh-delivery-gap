from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from execution_action_model import (
    ACTION_FEATURES,
    ActionConditionedExecutionJev,
    pinball_loss,
)


class ActionConditionedExecutionTests(unittest.TestCase):
    def test_shape_quantile_order_and_action_conditioning(self):
        torch.manual_seed(41)
        model = ActionConditionedExecutionJev()
        state = torch.randn(1, 16, 24).expand(3, -1, -1).clone()
        actions = torch.zeros(3, len(ACTION_FEATURES))
        actions[:, 0] = 1  # buy
        actions[:, 2] = 1  # marketable
        actions[:, 4] = torch.tensor([-1.5, -0.5, 0.5])  # log size/depth

        output = model(state, actions)
        self.assertEqual(tuple(output.shape), (3, 3))
        self.assertTrue(torch.isfinite(output).all())
        self.assertTrue((output[:, 1:] > output[:, :-1]).all())
        self.assertFalse(torch.allclose(output[0], output[2]))

    def test_candidate_actions_share_market_state_and_score_in_parallel(self):
        torch.manual_seed(7)
        model = ActionConditionedExecutionJev()
        state = torch.randn(2, 16, 24)
        actions = torch.zeros(2, 4, len(ACTION_FEATURES))
        actions[:, :, 0] = 1
        actions[:, :, 2] = 1
        actions[:, :, 4] = torch.tensor([-2.0, -1.0, 0.0, 1.0])
        output = model(state, actions)
        self.assertEqual(tuple(output.shape), (2, 4, 3))
        self.assertTrue(torch.isfinite(output).all())
        self.assertFalse(torch.allclose(output[:, 0], output[:, -1]))
        for i in range(4):
            self.assertTrue(torch.allclose(output[:, i], model(state, actions[:, i]), atol=1e-6))

    def test_pinball_loss_backpropagates(self):
        prediction = torch.tensor([[-1.0, 0.0, 1.0], [0.0, 1.0, 2.0]], requires_grad=True)
        target = torch.tensor([0.5, 1.5])
        loss = pinball_loss(prediction, target)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertIsNotNone(prediction.grad)
        self.assertGreater(float(prediction.grad.abs().sum()), 0.0)

    def test_rejects_bad_shapes_nonfinite_values_and_invalid_quantiles(self):
        model = ActionConditionedExecutionJev()
        with self.assertRaisesRegex(ValueError, "state"):
            model(torch.zeros(2, 15, 24), torch.zeros(2, len(ACTION_FEATURES)))
        with self.assertRaisesRegex(ValueError, "action"):
            model(torch.zeros(2, 16, 24), torch.zeros(2, 7))
        bad = torch.zeros(2, 16, 24)
        bad[0, 0, 0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            model(bad, torch.zeros(2, len(ACTION_FEATURES)))
        with self.assertRaisesRegex(ValueError, "quantiles"):
            pinball_loss(torch.zeros(2, 3), torch.zeros(2), quantiles=(0.1, 0.5, 1.0))


if __name__ == "__main__":
    unittest.main()
