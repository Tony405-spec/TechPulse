from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.experiment.features import build_features
from src.experiment.modeling import _cv_metrics, _json_clean, _metrics, grouped_cv_splits, grouped_train_test_indices
from src.simulate import simulate_corpus


@pytest.fixture(scope="module")
def corpus():
    return simulate_corpus()


def test_grouped_train_test_and_cv_have_zero_technology_overlap(corpus):
    labels=corpus.anchor_labels.dropna(subset=["trajectory_label"]).reset_index(drop=True)
    y=labels.trajectory_label.astype(str)
    groups=labels.technology_id.astype(str)
    train,test=grouped_train_test_indices(y,groups,seed=42)
    assert set(groups.iloc[train]).isdisjoint(set(groups.iloc[test]))
    assert set(groups.iloc[train]) | set(groups.iloc[test]) == set(groups)
    train_labels=y.iloc[train].reset_index(drop=True)
    train_groups=groups.iloc[train].reset_index(drop=True)
    splits=grouped_cv_splits(pd.DataFrame({"row":np.arange(len(train))}),train_labels,train_groups)
    validation_group_fold={}
    for fold_no,(fit_idx,valid_idx) in enumerate(splits):
        assert set(train_groups.iloc[fit_idx]).isdisjoint(set(train_groups.iloc[valid_idx]))
        for group in set(train_groups.iloc[valid_idx]):
            assert group not in validation_group_fold
            validation_group_fold[group]=fold_no
    assert set(validation_group_fold)==set(train_groups)


def test_metric_auc_uses_explicit_project_class_order():
    y=np.array(["Growing","Stable","Declining"]*4)
    probabilities=np.tile(np.eye(3), (4,1))
    predicted=np.array(["Growing","Stable","Declining"]*4)
    result=_metrics(y,predicted,probabilities)
    assert result["roc_auc_ovr_macro"]==1.0
    assert result["Declining_roc_auc_ovr"]==1.0


def test_cv_metric_aggregation_handles_class_and_overall_rows():
    rows=[{"metric_name":"macro_f1","class_label":None,"metric_value":.5},
          {"metric_name":"macro_f1","class_label":None,"metric_value":.7},
          {"metric_name":"recall","class_label":"Declining","metric_value":.4},
          {"metric_name":"recall","class_label":"Declining","metric_value":.6}]
    result=_cv_metrics(rows)
    assert result["macro_f1"]=={"mean":.6,"std":pytest.approx(.1414213562)}
    assert result["Declining_recall"]["mean"]==.5


def test_model_metadata_json_converts_nonfinite_metrics_to_null():
    cleaned=_json_clean({"value":float("nan"),"folds":[float("inf"),.5]})
    assert cleaned=={"value":None,"folds":[None,.5]}


def test_features_are_identical_after_removing_all_future_records(corpus):
    full=build_features(corpus)
    chosen=corpus.anchor_labels.dropna(subset=["trajectory_label"]).iloc[[100,1700,4200]]
    for selected in chosen.itertuples(index=False):
        tech_id=selected.technology_id
        anchor_date=selected.anchor_date
        tables={name:frame.copy(deep=True) for name,frame in corpus.tables.items()}
        tables["stack_overflow_questions"]=tables["stack_overflow_questions"][tables["stack_overflow_questions"].observation_month<=anchor_date]
        tables["fortune500_stacks"]=tables["fortune500_stacks"][tables["fortune500_stacks"].adoption_date<=anchor_date]
        tables["developer_survey"]=tables["developer_survey"].assign(available_date=lambda f: pd.to_datetime(f.survey_year.astype(str)+'-06-30').dt.date)
        tables["developer_survey"]=tables["developer_survey"][tables["developer_survey"].available_date<=anchor_date].drop(columns="available_date")
        tables["question_company_mapping"]=tables["question_company_mapping"][tables["question_company_mapping"].observation_month<=anchor_date]
        truncated=replace(corpus,tables=tables)
        after=build_features(truncated,anchors=pd.DataFrame([selected._asdict()]))
        expected=full[(full.technology_id==tech_id)&(full.anchor_date==anchor_date)].feature_values.iloc[0]
        actual=after.iloc[0].feature_values
        assert expected.keys()==actual.keys()
        assert expected["trend_baseline_label"] in {"Growing","Stable","Declining"}
        for feature in expected:
            if isinstance(expected[feature],str):
                assert expected[feature]==actual[feature],feature
            else:
                assert np.allclose(expected[feature],actual[feature],equal_nan=True),feature

