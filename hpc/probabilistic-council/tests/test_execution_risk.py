import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from execution_risk_dataset import prepare, load_risk_cache
from execution_risk_model import ExecutionRiskJev
from execution_risk_cost import MarketableOrder, quote_entry, compose_order, validate_sequence_book
from execution_risk_train import run
from execution_risk_predict import ExecutionRiskPredictor
from execution_action_model import pinball_loss
from synchronized_tape import Book, NS, digest
from test_execution_jev import cache
from test_synchronized_tape import START


def book():
    return Book(START, START, tuple((99.0 - i, 1.0) for i in range(5)),
                tuple((101.0 + i, 1.0) for i in range(5)), "fixture")


class ExecutionRiskTests(unittest.TestCase):
    def test_query_geometry_and_backward(self):
        torch.manual_seed(5)
        model = ExecutionRiskJev()
        output = model(torch.randn(2, 16, 24))
        self.assertEqual(tuple(output.shape), (2, 3, 2, 2, 3))
        self.assertTrue((output[..., 1:] >= output[..., :-1]).all())
        self.assertTrue(torch.equal(output[:, :, 0, 0], -output[:, :, 1, 0].flip(-1)))
        self.assertTrue((output[:, :, :, 1] >= 0).all())
        self.assertTrue((torch.diff(output[:, :, :, 1], dim=1) >= 0).all())
        self.assertTrue((output[:, :, :, 1] >= output[:, :, :, 0]).all())
        pinball_loss(output, torch.zeros(2, 3, 2, 2)).backward()
        self.assertGreater(float(model.project.weight.grad.abs().sum()), 0)

    def test_snapshot_walk_fee_units_depth_bound_and_time_guards(self):
        b = book()
        result = quote_entry(b, MarketableOrder("buy", 1.5, 5, 4.5), START)
        self.assertAlmostEqual(result["snapshot_vwap"], 101 + 1 / 3)
        self.assertAlmostEqual(result["spread_and_depth_bps"], 400 / 3)
        self.assertAlmostEqual(result["fee_bps_on_decision_notional"], 4.56)
        sell = quote_entry(b, MarketableOrder("sell", 1.0, 5, 4.5), START)
        self.assertAlmostEqual(sell["fee_bps_on_decision_notional"], 4.455)
        with self.assertRaisesRegex(ValueError, "liquidity"):
            quote_entry(b, MarketableOrder("buy", 5.1, 5, 4.5), START)
        with self.assertRaisesRegex(ValueError, "known"):
            quote_entry(b, MarketableOrder("buy", 1, 5, 4.5), START - 1)
        with self.assertRaisesRegex(ValueError, "stale"):
            quote_entry(b, MarketableOrder("buy", 1, 5, 4.5), START + 3 * NS)

    def test_cost_overlay_is_exact_offset_and_does_not_claim_exit_profit(self):
        b = book()
        risk = np.zeros((3, 2, 2, 3))
        risk[:, 0, 0] = [-1, 0, 2]
        risk[:, 1, 0] = [-2, 0, 1]
        risk[:, :, 1] = [0, 1, 2]
        proposal = MarketableOrder("buy", 1, 5, 4.5)
        result = compose_order(risk, b, proposal, START)
        cost = result["entry_quote"]["entry_cost_bps"]
        self.assertTrue(np.allclose(result["terminal_markout_loss_quantiles_bps"], np.array([-1, 0, 2]) + cost))
        self.assertTrue(np.allclose(result["double_entry_cost_terminal_quantiles_bps"], np.array([-1, 0, 2]) + 2 * cost))
        self.assertFalse(result["entry_quote"]["fill_verified"])
        risk[:, :, 1, 0] = -1
        with self.assertRaisesRegex(ValueError, "geometry"):
            compose_order(risk, b, proposal, START)

    def test_quote_and_feature_state_must_match(self):
        b = book()
        x = np.zeros((16, 24))
        expected = []
        for i in range(5):
            for side in (b.bids, b.asks):
                expected.extend(((side[i][0] / b.mid - 1) * 10000, 0.1))
        x[-1, :20] = expected
        x[-1, 20] = 200
        validate_sequence_book(x, b, START)
        x[-1, 0] += 1
        with self.assertRaisesRegex(ValueError, "match"):
            validate_sequence_book(x, b, START)

    def test_audit_conversion_and_hash_alignment_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = cache(root)
            prepare(source, root / "risk")
            spec, arrays = load_risk_cache(root / "risk")
            self.assertEqual(arrays["targets"].shape[1:], (3, 2, 2))
            self.assertFalse(spec["eligible_for_performance_claim"])
            audit = source / "label_audit.jsonl"
            audit.write_text(audit.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "audit hash"):
                prepare(source, root / "bad")

    def test_eval_changes_cannot_change_fit_selection_or_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = cache(root)
            prepare(source, root / "risk")
            dataset = root / "risk"
            with self.assertRaisesRegex(ValueError, "independent sessions"):
                run(dataset, root / "rejected", epochs=1)
            self.assertFalse((root / "rejected").exists())
            before = run(dataset, root / "run", epochs=1, allow_development_smoke=True)
            _, arrays = load_risk_cache(dataset)
            first = np.flatnonzero(arrays["roles"] == 4)[0]
            for name in ("A", "B", "AB", "empirical_quantiles"):
                checkpoint = root / "run" / (name + ".pt")
                predictor = ExecutionRiskPredictor(checkpoint, digest(checkpoint))
                expected = np.load(root / "run" / (name + "_evaluation.npy"))[0]
                self.assertTrue(np.allclose(predictor.risk(arrays["features"][first]), expected, atol=1e-6))
                with self.assertRaisesRegex(ValueError, "hash"):
                    ExecutionRiskPredictor(checkpoint, "invalid")
            changed = np.array(arrays["targets"])
            evaluation = arrays["roles"] == 4
            changed[evaluation, :, 0, 0] += 0.1
            changed[evaluation, :, 1, 0] -= 0.1
            changed[evaluation, :, :, 1] += 1
            np.save(dataset / "targets.npy", changed, allow_pickle=False)
            manifest = json.loads((dataset / "manifest.json").read_text())
            manifest["array_sha256"]["targets.npy"] = digest(dataset / "targets.npy")
            (dataset / "manifest.json").write_text(json.dumps(manifest))
            after = run(dataset, root / "changed", epochs=1, allow_development_smoke=True)
            for key in ("normalizer", "losses", "gate_metrics", "gate_selected"):
                self.assertEqual(before[key], after[key])
            for name in ("A", "B", "AB"):
                original = torch.load(root / "run" / (name + ".pt"), weights_only=True)["state"]
                modified = torch.load(root / "changed" / (name + ".pt"), weights_only=True)["state"]
                self.assertTrue(all(torch.equal(v, modified[k]) for k, v in original.items()))
            self.assertNotEqual(before["evaluation_metrics"], after["evaluation_metrics"])


if __name__ == "__main__":
    unittest.main()
