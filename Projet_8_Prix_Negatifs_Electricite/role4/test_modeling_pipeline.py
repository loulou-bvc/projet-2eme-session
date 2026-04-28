from pathlib import Path

from modeling_pipeline import (
    DATA_PATH,
    build_features,
    load_dataset,
    split_temporally,
)


def test_feature_dataset_has_target_and_no_current_price_leakage():
    df = load_dataset(DATA_PATH)
    features, target = build_features(df)

    assert "is_negative_price" == target.name
    assert target.sum() > 0
    assert "DK_1_price_day_ahead" not in features.columns
    assert "DK_2_price_day_ahead" not in features.columns
    assert "price_DK1_lag_1h" in features.columns
    assert features.isna().sum().sum() == 0


def test_temporal_split_is_ordered_and_contains_positive_cases():
    df = load_dataset(DATA_PATH)
    features, target = build_features(df)
    splits = split_temporally(features, target)

    assert splits.X_train.index.max() < splits.X_val.index.min()
    assert splits.X_val.index.max() < splits.X_test.index.min()
    assert splits.y_train.sum() > 0
    assert splits.y_val.sum() > 0
    assert splits.y_test.sum() > 0
    assert Path(DATA_PATH).exists()
