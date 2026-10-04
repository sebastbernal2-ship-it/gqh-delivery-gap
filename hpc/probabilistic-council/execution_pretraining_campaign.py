"""Frozen nine-variant movement-risk engineering comparison, with update-count control."""
import argparse
import importlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import torch

from execution_action_model import pinball_loss
from execution_risk_dataset import load_risk_cache
from execution_risk_model import ExecutionRiskJev
from execution_risk_train import VIEWS, metrics, forecast, view_tensor
from synchronized_tape import digest

SEED = 20261004
VARIANTS = {'scratch3': (0, 3), 'scratch6': (0, 6), 'masked3_supervised3': (3, 3)}


def source_files():
    names = ('execution_risk_train', 'execution_risk_model', 'execution_model',
             'execution_risk_dataset', 'execution_action_model')
    return [Path(__file__)] + [Path(importlib.import_module(n).__file__) for n in names]


def normalize(raw, labels, roles):
    training = roles == 0
    mean = raw[training].mean((0, 1))
    scale = raw[training].std((0, 1))
    scale = np.where(scale < 1e-6, 1., scale)
    target_scale = max(float(labels[training].std()), .1)
    return torch.tensor((raw - mean) / scale, dtype=torch.float32), mean, scale, target_scale


def masked_view_loss(model, x, mask, view):
    if mask.dtype != torch.bool or mask.shape != x.shape[:2] or not mask.any():
        raise ValueError('nonempty boolean temporal mask required')
    corrupted = torch.where(mask.unsqueeze(-1), model.mask_token, x)
    prediction = model.reconstruct(model.encode(corrupted))
    channels = list(VIEWS[view])
    return ((prediction[mask][:, channels] - x[mask][:, channels]) ** 2).mean()


def train(x, y, view, variant, target_scale, device):
    torch.manual_seed(SEED)
    model = ExecutionRiskJev().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
    pre_epochs, supervised_epochs = VARIANTS[variant]
    history = {'masked': [], 'supervised': []}
    updates = {'masked': 0, 'supervised': 0}
    x = view_tensor(x, view)
    start = time.perf_counter()
    for stage, epochs in [('masked', pre_epochs), ('supervised', supervised_epochs)]:
        for _ in range(epochs):
            for indexes in torch.randperm(len(x)).split(32):
                batch = x[indexes].to(device)
                optimizer.zero_grad()
                if stage == 'masked':
                    mask = torch.rand(batch.shape[:2], device=device) < .25
                    if not mask.any():
                        mask[0, 0] = True
                    loss = masked_view_loss(model, batch, mask, view)
                else:
                    loss = pinball_loss(model(batch), y[indexes].to(device) / target_scale)
                if not torch.isfinite(loss):
                    raise ValueError('nonfinite campaign loss')
                loss.backward()
                optimizer.step()
                history[stage].append(float(loss.detach()))
                updates[stage] += 1
    if device.startswith('cuda'):
        torch.cuda.synchronize()
    return model.eval(), history, updates, time.perf_counter() - start


def run(dataset, output, device='cpu', allow_reused_development_smoke=False):
    spec, arrays = load_risk_cache(dataset)
    roles = np.asarray(arrays['roles'])
    labels = np.asarray(arrays['targets'], dtype=np.float64)
    role_sessions = {name: sorted({spec['sessions'][i] for i in np.flatnonzero(roles == role)})
                     for role, name in enumerate(spec['partitions'])}
    scarce = [name for name in ('training', 'gate_fit', 'evaluation') if len(role_sessions[name]) < 3]
    if scarce and not allow_reused_development_smoke:
        raise ValueError('insufficient independent dates; fresh training campaign refused')
    if device.startswith('cuda') and not torch.cuda.is_available():
        raise ValueError('CUDA unavailable')
    torch.set_num_threads(2)
    x, mean, scale, target_scale = normalize(np.asarray(arrays['features'], dtype=np.float64), labels, roles)
    y = torch.tensor(labels, dtype=torch.float32)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    models, losses, updates, elapsed, gate = {}, {}, {}, {}, {}
    for view in VIEWS:
        for variant in VARIANTS:
            name = view + '_' + variant
            model, losses[name], updates[name], elapsed[name] = train(
                x[roles == 0], y[roles == 0], view, variant, target_scale, device)
            models[name] = (view, model)
            gate[name] = metrics(forecast(model, x[roles == 2], view, target_scale), labels[roles == 2])
    prior = np.moveaxis(np.quantile(labels[roles == 0], [.1, .5, .9], axis=0), 0, -1)
    gate['empirical_quantiles'] = metrics(np.broadcast_to(prior, (int(sum(roles == 2)),) + prior.shape), labels[roles == 2])
    selected = min(gate, key=lambda name: gate[name]['mean_parent_pinball_bps'])
    predictions = {name: forecast(model, x[roles == 4], view, target_scale)
                   for name, (view, model) in models.items()}
    predictions['empirical_quantiles'] = np.broadcast_to(prior, (int(sum(roles == 4)),) + prior.shape)
    scores = {name: metrics(p, labels[roles == 4]) for name, p in predictions.items()}
    for name, (view, model) in models.items():
        torch.save({'schema_version': 'execution-risk-jev-v1', 'variant': view,
                    'campaign_variant': name, 'config': model.config,
                    'state': {k: v.detach().cpu() for k, v in model.state_dict().items()},
                    'mean': mean.tolist(), 'scale': scale.tolist(), 'target_scale': target_scale,
                    'quantiles': [.1, .5, .9], 'feature_order': spec['feature_order'],
                    'dataset_manifest_sha256': digest(Path(dataset) / 'manifest.json'),
                    'scope': 'development_only', 'calibrated': False}, out / (name + '.pt'))
    for name, p in predictions.items():
        np.save(out / (name + '_evaluation.npy'), p, allow_pickle=False)
    report = {'schema_version': 'execution-pretraining-campaign-v1',
              'scope': 'reused_development_engineering_only', 'eligible_for_performance_claim': False,
              'seed': SEED, 'comparison_count': 10, 'variants': VARIANTS,
              'view_channels': {k: list(v) for k, v in VIEWS.items()},
              'dataset_manifest_sha256': digest(Path(dataset) / 'manifest.json'),
              'code_sha256': {p.name: digest(p) for p in source_files()},
              'role_sessions': role_sessions, 'role_cases': {n: int(sum(roles == i)) for i, n in enumerate(spec['partitions'])},
              'scarce_roles': scarce, 'masked_training_roles': [0],
              'normalizer': {'mean': mean.tolist(), 'scale': scale.tolist(), 'target_scale': target_scale},
              'gate_selected': selected, 'gate_metrics': gate, 'evaluation_metrics': scores,
              'losses': losses, 'optimizer_updates': updates, 'fit_elapsed_seconds': elapsed,
              'environment': {'python': platform.python_version(), 'torch': torch.__version__,
                              'numpy': np.__version__, 'device': device,
                              'gpu': torch.cuda.get_device_name(0) if device.startswith('cuda') else None},
              'artifacts': {p.name: digest(p) for p in out.iterdir()},
              'limitations': ['previously inspected development cases; new fitting is not new OOS',
                              'equal optimizer updates do not mean equal FLOPs or time',
                              'calibration roles unused; all neural forecasts uncalibrated',
                              'no fills, strategy trade policy, quantum computation or HFT latency measured']}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'selected': selected, 'pinball': {n: s['mean_parent_pinball_bps'] for n, s in scores.items()},
                      'coverage80': {n: s['interval_80_coverage'] for n, s in scores.items()}}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--allow-reused-development-smoke', action='store_true')
    args = parser.parse_args()
    run(args.dataset, args.output, args.device, args.allow_reused_development_smoke)
