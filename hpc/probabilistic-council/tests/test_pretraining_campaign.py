"""Guard against holdout leakage and unavailable-channel reconstruction."""
import numpy as np
import pytest
import torch

from execution_pretraining_campaign import normalize, masked_view_loss, VARIANTS, source_files
from execution_risk_model import ExecutionRiskJev


def test_holdout_cannot_change_training_normalizer():
    rng = np.random.default_rng(8)
    x = rng.normal(size=(5, 16, 24))
    y = rng.normal(size=(5, 3, 2, 2))
    roles = np.arange(5)
    _, mean, scale, target = normalize(x, y, roles)
    x[1:] = 1e9
    y[1:] = -1e9
    _, mean2, scale2, target2 = normalize(x, y, roles)
    assert np.array_equal(mean, mean2)
    assert np.array_equal(scale, scale2)
    assert target == target2


def test_unavailable_channels_have_no_reconstruction_gradient():
    torch.manual_seed(3)
    model = ExecutionRiskJev()
    x = torch.zeros(2, 16, 24)
    x[:, :, 21:23] = 1
    mask = torch.zeros(2, 16, dtype=torch.bool)
    mask[:, ::4] = True
    masked_view_loss(model, x, mask, 'B').backward()
    grad = model.reconstruct.weight.grad
    excluded = list(range(21)) + [23]
    assert torch.count_nonzero(grad[excluded]) == 0
    assert torch.count_nonzero(grad[21:23]) > 0


def test_empty_mask_rejected_and_budget_control_fixed():
    model = ExecutionRiskJev()
    with pytest.raises(ValueError, match='mask'):
        masked_view_loss(model, torch.zeros(1, 16, 24), torch.zeros(1, 16, dtype=torch.bool), 'A')
    assert sum(VARIANTS['scratch6']) == sum(VARIANTS['masked3_supervised3']) == 6


def test_dependency_provenance_uses_imported_module_location(monkeypatch, tmp_path):
    import execution_pretraining_campaign as campaign
    staged = tmp_path / 'campaign.py'
    staged.write_text('# staged wrapper')
    monkeypatch.setattr(campaign, '__file__', str(staged))
    sources = source_files()
    assert sources[0] == staged
    assert len(sources) == 6 and all(p.is_file() for p in sources)
    assert all(p.parent != tmp_path for p in sources[1:])
