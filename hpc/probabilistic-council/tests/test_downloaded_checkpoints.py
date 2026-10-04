from pathlib import Path

from verify_downloaded_checkpoints import verify


def test_published_weights_match_hpg_gpu_predictions():
    root = Path(__file__).resolve().parents[1] / 'checkpoints/hpg-44665003'
    result = verify(root)
    assert result['checkpoints'] == 9
    assert result['calibrated'] is False
    assert max(result['max_absolute_difference_bps'].values()) < 1e-5
