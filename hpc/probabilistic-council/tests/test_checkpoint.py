"""Checkpoint snapshots must survive later optimizer steps on CPU."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jevlike import train
from jevlike.model import TinyScorer, load_checkpoint, trainable_state


class CheckpointTests(unittest.TestCase):
    def test_snapshot_is_independent_and_excludes_frozen_parameters(self):
        model = TinyScorer(8, 8, 32)
        model.embedding.requires_grad_(False)
        snapshot = trainable_state(model)
        self.assertNotIn("embedding.weight", snapshot)
        originals = {name: value.clone() for name, value in snapshot.items()}
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                if parameter.requires_grad:
                    parameter.add_(1)
                    self.assertFalse(snapshot[name].requires_grad)
                    self.assertEqual(snapshot[name].device.type, "cpu")
                    self.assertTrue(torch.equal(snapshot[name], originals[name]), name)

    def test_training_saves_best_epoch_after_later_validation_worsens(self):
        # Actual optimizer/data/checkpoint code; only the validation ranking is controlled.
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / "rows.jsonl"
            data.write_text(json.dumps({"context": "choose amber", "options": ["amber", "azure"], "label": 0}) + "\n")
            output = Path(temp) / "tiny.pt"
            observed = []

            def validation(model, loader, device):
                observed.append({name: p.detach().clone() for name, p in model.named_parameters()})
                return (0.1, 0.9)[len(observed) - 1]

            args = ["train", str(data), "--validation", str(data), "--output", str(output),
                    "--width", "8", "--rank", "8", "--context-tokens", "32",
                    "--option-tokens", "16", "--epochs", "2", "--batch-size", "1", "--device", "cpu"]
            with patch.object(sys, "argv", args), patch.object(train, "mean_loss", side_effect=validation), contextlib.redirect_stdout(io.StringIO()):
                train.main()
            self.assertTrue(any(not torch.equal(observed[0][k], observed[1][k]) for k in observed[0]))
            restored, _, _ = load_checkpoint(output, torch.device("cpu"))
            for name, parameter in restored.named_parameters():
                self.assertTrue(torch.equal(parameter, observed[0][name]), name)


if __name__ == "__main__":
    unittest.main()
