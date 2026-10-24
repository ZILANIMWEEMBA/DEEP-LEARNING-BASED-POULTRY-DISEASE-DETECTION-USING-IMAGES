from machine_learning.training.train import compute_class_weights


def test_compute_class_weights_balances_classes():
    counts = {
        "Healthy": 16,
        "Coccidiosis": 16,
        "Newcastle Disease": 16,
        "Salmonella": 16,
    }
    weights = compute_class_weights(counts)
    assert list(weights.keys()) == [0, 1, 2, 3]
    assert all(v > 0 for v in weights.values())
    assert weights[0] == weights[1] == weights[2] == weights[3]
