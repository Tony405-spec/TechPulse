"""Grouped nested evaluation and persistence for the simulated label experiment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap
from dotenv import load_dotenv
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
                             roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine, text
from xgboost import XGBClassifier

from src.db.migrate import _database_url, apply_migrations
from src.experiment.features import FEATURE_COLUMNS, _git_provenance, read_training_frame
from src.labels import load_label_config

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
CLASSES = ["Growing", "Stable", "Declining"]
LABEL_CFG = load_label_config()
LABEL_RULE = f"{LABEL_CFG['version']}: trailing {LABEL_CFG['recent_window_months']} month mean vs following {LABEL_CFG['future_horizon_months']} month mean"
NUMERIC = [c for c in FEATURE_COLUMNS if c != "category"]
CONTEXT = ["category", "history_months", "low_confidence"]
SIGNAL = {
    "community": [c for c in FEATURE_COLUMNS if c.startswith("community_") or c == "growth_momentum_index"],
    "enterprise": [c for c in FEATURE_COLUMNS if c.startswith("enterprise_")],
    "sentiment": [c for c in FEATURE_COLUMNS if c.startswith("sentiment_")],
}
SIGNAL_SUBSETS = [
    ("community",), ("enterprise",), ("sentiment",),
    ("community", "enterprise"), ("community", "sentiment"), ("enterprise", "sentiment"),
    ("community", "enterprise", "sentiment"),
]


class PriorAdjustedKNN(ClassifierMixin, BaseEstimator):
    """Distance-weighted KNN with inverse class-prior probability correction."""
    def __init__(self, n_neighbors: int = 7):
        self.n_neighbors = n_neighbors

    def fit(self, X, y):
        self.classes_, counts = np.unique(y, return_counts=True)
        self.priors_ = counts / counts.sum()
        self.model_ = KNeighborsClassifier(n_neighbors=self.n_neighbors, weights="distance")
        self.model_.fit(X, y)
        return self

    def predict_proba(self, X):
        probabilities = self.model_.predict_proba(X)
        adjusted = probabilities / np.maximum(self.priors_[None, :], 1e-8)
        return adjusted / adjusted.sum(axis=1, keepdims=True)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


class StringLabelXGB(ClassifierMixin, BaseEstimator):
    """XGBoost wrapper that preserves the project's string class labels."""
    def __init__(self, max_depth: int = 3, min_child_weight: float = 1, n_estimators: int = 100,
                 learning_rate: float = .06, subsample: float = .85, colsample_bytree: float = .85,
                 reg_lambda: float = 1.0, random_state: int = 42):
        self.max_depth=max_depth; self.min_child_weight=min_child_weight; self.n_estimators=n_estimators
        self.learning_rate=learning_rate; self.subsample=subsample; self.colsample_bytree=colsample_bytree
        self.reg_lambda=reg_lambda; self.random_state=random_state

    def fit(self, X, y, sample_weight=None):
        self.classes_=np.asarray(CLASSES)
        lookup={label:index for index,label in enumerate(self.classes_)}
        encoded=np.asarray([lookup[str(value)] for value in y],dtype=int)
        if sample_weight is None:
            class_counts=np.bincount(encoded,minlength=len(self.classes_))
            sample_weight=len(encoded)/(len(self.classes_)*np.maximum(class_counts[encoded],1))
        self.model_=XGBClassifier(objective="multi:softprob",eval_metric="mlogloss",num_class=3,
            n_estimators=self.n_estimators,max_depth=self.max_depth,min_child_weight=self.min_child_weight,
            learning_rate=self.learning_rate,subsample=self.subsample,colsample_bytree=self.colsample_bytree,
            reg_lambda=self.reg_lambda,n_jobs=1,random_state=self.random_state,verbosity=0)
        self.model_.fit(X,encoded,sample_weight=sample_weight)
        return self

    def predict_proba(self, X): return self.model_.predict_proba(X)
    def predict(self, X): return self.classes_[self.model_.predict(X).astype(int)]


@dataclass
class ExperimentResult:
    result_summary: dict[str, Any]
    comparison: pd.DataFrame
    ablation: pd.DataFrame
    best_run_id: str


def grouped_train_test_indices(y: pd.Series | np.ndarray, groups: pd.Series | np.ndarray, seed: int = 42):
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    train_index, test_index = next(splitter.split(np.zeros(len(y)), y, groups))
    if set(np.asarray(groups)[train_index]) & set(np.asarray(groups)[test_index]):
        raise AssertionError("Technology group overlap in held-out split.")
    return train_index, test_index


def grouped_cv_splits(X: pd.DataFrame, y: pd.Series, groups: pd.Series, seed: int = 42):
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    splits = list(splitter.split(X, y, groups))
    validation_group_fold = {}
    for fold_number, (train_index, valid_index) in enumerate(splits):
        if set(groups.iloc[train_index]) & set(groups.iloc[valid_index]):
            raise AssertionError("Technology group overlap inside a CV fold.")
        for group in set(groups.iloc[valid_index]):
            if group in validation_group_fold:
                raise AssertionError("A technology appears in validation in multiple CV folds.")
            validation_group_fold[group] = fold_number
    if set(validation_group_fold) != set(groups):
        raise AssertionError("A technology appears in validation more than once across CV folds.")
    return splits


def _make_pipeline(name: str, columns: list[str], params: dict[str, Any] | None = None) -> Pipeline:
    categorical = [c for c in columns if c == "category"]
    numeric = [c for c in columns if c not in categorical]
    preprocess = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())]), numeric),
        ("category", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ], remainder="drop", verbose_feature_names_out=False)
    params = params or {}
    if name == "logistic_regression":
        model = LogisticRegression(
            max_iter=1500,
            class_weight="balanced",
            solver="lbfgs",
            random_state=42,
            **params,
        )
    elif name == "knn":
        model = PriorAdjustedKNN(**params)
    elif name == "random_forest":
        model = RandomForestClassifier(n_estimators=160, class_weight="balanced_subsample", n_jobs=1, random_state=42, **params)
    elif name == "xgboost":
        model = StringLabelXGB(**params)
    else:
        raise ValueError(name)
    return Pipeline([("preprocess", preprocess), ("model", model)])


def _grid(name: str) -> dict[str, list[Any]]:
    if name == "logistic_regression": return {"model__C": [.2, 1.0, 5.0]}
    if name == "knn": return {"model__n_neighbors": [5, 11, 21]}
    if name == "random_forest": return {"model__max_depth": [None, 10], "model__min_samples_leaf": [2, 5]}
    return {"model__max_depth": [2, 4], "model__min_child_weight": [1, 4]}


def _sample_weights(y: pd.Series | np.ndarray) -> np.ndarray:
    classes, counts = np.unique(y, return_counts=True)
    weights = {c: len(y) / (len(classes) * count) for c, count in zip(classes, counts)}
    return np.asarray([weights[label] for label in y], dtype=float)


def _fit_params(name: str, y: pd.Series | np.ndarray) -> dict[str, Any]:
    # Every estimator derives its imbalance correction inside its own fit call:
    # class_weight for LR/RF, train-fold priors for KNN, sample_weight in XGB.
    return {}


def _probabilities(estimator, X: pd.DataFrame) -> np.ndarray:
    values = estimator.predict_proba(X)
    classes = list(estimator.classes_)
    return np.column_stack([values[:, classes.index(c)] if c in classes else np.zeros(len(X)) for c in CLASSES])


def _ece(y_true, probabilities, bins: int = 10) -> float:
    confidence = probabilities.max(axis=1)
    predicted = np.asarray(CLASSES)[probabilities.argmax(axis=1)]
    correct = predicted == np.asarray(y_true)
    result = 0.0
    for low in np.linspace(0, 1, bins, endpoint=False):
        high = low + 1/bins
        mask = (confidence >= low) & (confidence < high if high < 1 else confidence <= high)
        if mask.any(): result += float(mask.mean() * abs(correct[mask].mean()-confidence[mask].mean()))
    return result


def _metrics(y_true, predicted, probabilities) -> dict[str, float]:
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, predicted, labels=CLASSES, zero_division=0)
    aucs=[]
    for i,label in enumerate(CLASSES):
        binary=(np.asarray(y_true)==label).astype(int)
        aucs.append(float(roc_auc_score(binary,probabilities[:,i])) if binary.min()!=binary.max() else np.nan)
    valid_aucs=[value for value in aucs if np.isfinite(value)]
    result = {"accuracy": float(accuracy_score(y_true, predicted)), "macro_f1": float(f1_score(y_true,predicted,labels=CLASSES,average="macro",zero_division=0)),
              "roc_auc_ovr_macro": float(np.mean(valid_aucs)) if valid_aucs else float("nan"),
              "brier_multiclass": float(np.mean(np.sum((probabilities - pd.get_dummies(pd.Categorical(y_true,categories=CLASSES)).to_numpy())**2,axis=1))),
              "calibration_ece_10bin": _ece(y_true,probabilities)}
    for i, label in enumerate(CLASSES):
        result[f"{label}_precision"] = float(precision[i]); result[f"{label}_recall"] = float(recall[i]); result[f"{label}_f1"] = float(f1[i])
        binary=(np.asarray(y_true)==label).astype(int)
        if binary.min()!=binary.max():
            result[f"{label}_roc_auc_ovr"] = float(roc_auc_score(binary,probabilities[:,i]))
    return result


def _add_metric_rows(rows, model_run_id, part, metrics, fold=None):
    for name, value in metrics.items():
        class_label=None; metric_name=name
        for label in CLASSES:
            prefix=label+"_"
            if name.startswith(prefix):
                class_label=label; metric_name=name[len(prefix):]; break
        rows.append({"model_run_id": model_run_id,"evaluation_part":part,"fold_number":fold,"metric_name":metric_name,
                     "class_label":class_label,"metric_value":float(value),"support":None,"metadata":{}})


def _confusion_rows(rows, model_run_id, part, y_true, predicted, fold=None):
    matrix=confusion_matrix(y_true,predicted,labels=CLASSES)
    for i,actual in enumerate(CLASSES):
        for j,guess in enumerate(CLASSES):
            rows.append({"model_run_id":model_run_id,"evaluation_part":part,"fold_number":fold,
                "metric_name":f"confusion_pred_{guess}","class_label":actual,"metric_value":float(matrix[i,j]),"support":int(matrix[i,:].sum()),"metadata":{"predicted_class":guess}})


def _cv_metrics(model_rows):
    metrics=pd.DataFrame(model_rows)
    result={}
    for (metric,label),group in metrics.groupby(["metric_name","class_label"],dropna=False):
        key=f"{label}_{metric}" if pd.notna(label) else metric
        result[key]={"mean":float(group.metric_value.mean()),"std":float(group.metric_value.std(ddof=1) if len(group)>1 else 0.0)}
    return result


def _json_value(value):
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, (pd.Timestamp, datetime)): return value.isoformat()
    raise TypeError(type(value).__name__)


def _json_clean(value):
    """Replace non-finite numbers with JSON null before PostgreSQL JSONB casts."""
    if isinstance(value, dict): return {str(k):_json_clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_json_clean(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,datetime)): return value.isoformat()
    return value


def _family_for_feature(name: str) -> str:
    simple=name.split("__")[-1]
    if simple.startswith("community_") or simple == "growth_momentum_index": return "community"
    if simple.startswith("enterprise_"): return "enterprise"
    if simple.startswith("sentiment_"): return "sentiment"
    return "context"


def _plain_driver(feature: str, shap_value: float, predicted_label: str) -> str:
    readable=feature.replace("_", " ").replace("category ", "category: ")
    direction="increased" if shap_value >= 0 else "decreased"
    return f"The model associated {readable} with an {direction} in the {predicted_label} probability (SHAP contribution {shap_value:+.4f})."


def run_experiment(data_version_id: str | None = None, url: str | None = None) -> ExperimentResult:
    """Fit nested grouped CV models, choose by CV macro-F1, then evaluate test once."""
    started=datetime.now(timezone.utc)
    frame=read_training_frame(url,data_version_id)
    if frame.empty: raise RuntimeError("No persisted feature snapshots and labels were found.")
    frame=frame.dropna(subset=["trajectory_label"]).reset_index(drop=True)
    if set(frame.trajectory_label.unique()) != set(CLASSES): raise RuntimeError("All three classes are required for stratified evaluation.")
    y=frame.trajectory_label.astype(str)
    groups=frame.technology_id.astype(str)
    X=frame[FEATURE_COLUMNS].copy()
    X["category"]=X["category"].astype("string")
    train_index,test_index=grouped_train_test_indices(y,groups)
    X_train,y_train,groups_train=X.iloc[train_index].reset_index(drop=True),y.iloc[train_index].reset_index(drop=True),groups.iloc[train_index].reset_index(drop=True)
    X_test,y_test=X.iloc[test_index].reset_index(drop=True),y.iloc[test_index].reset_index(drop=True)
    train_rows=frame.iloc[train_index].reset_index(drop=True); test_rows=frame.iloc[test_index].reset_index(drop=True)
    outer_splits=grouped_cv_splits(X_train,y_train,groups_train)
    commit,dirty=_git_provenance()
    version_id=str(frame.data_version_id.iloc[0])
    if frame.data_version_id.nunique()!=1: raise RuntimeError("Training frame mixed multiple data versions.")
    model_results={}; metric_store=[]; model_protocols={}; summary_rows=[]
    candidate_names=["logistic_regression","knn","random_forest","xgboost"]
    for model_name in candidate_names:
        fold_predictions=[]; fold_scores=[]; fold_params=[]
        for fold_no,(outer_train,outer_valid) in enumerate(outer_splits,1):
            Xot=X_train.iloc[outer_train]; yot=y_train.iloc[outer_train]; got=groups_train.iloc[outer_train]
            Xov=X_train.iloc[outer_valid]; yov=y_train.iloc[outer_valid]
            inner=grouped_cv_splits(Xot.reset_index(drop=True),yot.reset_index(drop=True),got.reset_index(drop=True),seed=42+fold_no)
            pipe=_make_pipeline(model_name,FEATURE_COLUMNS)
            search=GridSearchCV(pipe,_grid(model_name),scoring="f1_macro",cv=inner,n_jobs=1,refit=True,error_score="raise")
            search.fit(Xot,yot,**_fit_params(model_name,yot))
            probs=_probabilities(search.best_estimator_,Xov); preds=np.asarray(CLASSES)[probs.argmax(axis=1)]
            metrics=_metrics(yov,preds,probs); fold_scores.append(metrics); fold_params.append(search.best_params_)
            fold_predictions.append((outer_valid,preds,probs))
        run_id=f"{version_id}-{model_name}-{(commit or 'nogit')[:8]}"
        metric_rows=[]
        for fold_no,((indices,preds,probs),metrics) in enumerate(zip(fold_predictions,fold_scores),1):
            _add_metric_rows(metric_rows,run_id,"outer_cv",metrics,fold_no)
            _confusion_rows(metric_rows,run_id,"outer_cv",y_train.iloc[indices],preds,fold_no)
        cv_summary=_cv_metrics([r for r in metric_rows if not r["metric_name"].startswith("confusion_pred_") and r["fold_number"] is not None])
        score=cv_summary["macro_f1"]["mean"]
        model_results[model_name]={"run_id":run_id,"cv_scores":fold_scores,"cv_summary":cv_summary,"fold_params":fold_params,"fold_predictions":fold_predictions}
        model_protocols[model_name]={"score":score,"parameters_by_fold":fold_params,"split":"StratifiedGroupKFold(n_splits=5) on training set; grouped 80/20 test held out once","tuning":"inner StratifiedGroupKFold(n_splits=5); scoring macro-F1","features":FEATURE_COLUMNS}
        metric_store.extend(metric_rows)
        summary_rows.append({"model":model_name,"cv_macro_f1_mean":score,"cv_macro_f1_std":cv_summary["macro_f1"]["std"],"cv":cv_summary})

    # Baselines are scored on the same grouped folds and held-out set.
    baseline_results={}
    for name in ["majority_class","recent_trend_continues"]:
        run_id=f"{version_id}-{name}-{(commit or 'nogit')[:8]}"
        rows=[]
        for fold_no,(fit_idx,val_idx) in enumerate(outer_splits,1):
            yfit=y_train.iloc[fit_idx]; yval=y_train.iloc[val_idx]
            if name=="majority_class":
                pred=np.repeat(yfit.value_counts().idxmax(),len(val_idx))
                prob=np.zeros((len(val_idx),3)); prob[:,CLASSES.index(yfit.value_counts().idxmax())]=1
            else:
                pred=train_rows.iloc[val_idx].trend_baseline_label.astype(str).to_numpy()
                prob=np.eye(3)[[CLASSES.index(x) for x in pred]]
            scores=_metrics(yval,pred,prob); _add_metric_rows(rows,run_id,"outer_cv",scores,fold_no); _confusion_rows(rows,run_id,"outer_cv",yval,pred,fold_no)
        if name=="majority_class":
            class_name=y_train.value_counts().idxmax(); test_pred=np.repeat(class_name,len(y_test)); test_prob=np.zeros((len(y_test),3)); test_prob[:,CLASSES.index(class_name)]=1
        else:
            test_pred=test_rows.trend_baseline_label.astype(str).to_numpy(); test_prob=np.eye(3)[[CLASSES.index(x) for x in test_pred]]
        test_metrics=_metrics(y_test,test_pred,test_prob); _add_metric_rows(rows,run_id,"test",test_metrics); _confusion_rows(rows,run_id,"test",y_test,test_pred)
        cv_summary=_cv_metrics([r for r in rows if r["evaluation_part"]=="outer_cv" and not r["metric_name"].startswith("confusion_pred_")])
        baseline_results[name]={"run_id":run_id,"cv_summary":cv_summary,"test_metrics":test_metrics}
        metric_store.extend(rows)
        summary_rows.append({"model":name,"cv_macro_f1_mean":cv_summary["macro_f1"]["mean"],"cv_macro_f1_std":cv_summary["macro_f1"]["std"],"cv":cv_summary})

    # Select strictly on CV macro-F1; then fit selected model only on training data.
    best_model=max(candidate_names,key=lambda name:model_results[name]["cv_summary"]["macro_f1"]["mean"])
    train_inner=grouped_cv_splits(X_train,y_train,groups_train,seed=97)
    best_search=GridSearchCV(_make_pipeline(best_model,FEATURE_COLUMNS),_grid(best_model),scoring="f1_macro",cv=train_inner,n_jobs=1,refit=True,error_score="raise")
    best_search.fit(X_train,y_train,**_fit_params(best_model,y_train))
    best_pipeline=best_search.best_estimator_
    test_prob=_probabilities(best_pipeline,X_test); test_pred=np.asarray(CLASSES)[test_prob.argmax(axis=1)]
    test_metrics=_metrics(y_test,test_pred,test_prob)
    best_run_id=model_results[best_model]["run_id"]
    _add_metric_rows(metric_store,best_run_id,"test",test_metrics); _confusion_rows(metric_store,best_run_id,"test",y_test,test_pred)
    model_results[best_model]["test_metrics"]=test_metrics
    model_results[best_model]["test_probabilities"]=test_prob
    model_results[best_model]["test_predictions"]=test_pred
    model_results[best_model]["best_params"]=best_search.best_params_

    # Chronological robustness check: future anchors from held-out technologies;
    # training uses other technologies and ends before the future horizon starts.
    heldout_tech=set(groups.iloc[test_index]); unique_dates=sorted(pd.to_datetime(frame.anchor_date).unique())
    cutoff=pd.Timestamp(unique_dates[int(.8*(len(unique_dates)-1))])
    purge_months=int(LABEL_CFG["future_horizon_months"])
    train_end=cutoff-pd.DateOffset(months=purge_months)
    chrono_train=(~frame.technology_id.isin(heldout_tech)) & (pd.to_datetime(frame.anchor_date)<train_end)
    chrono_test=frame.technology_id.isin(heldout_tech) & (pd.to_datetime(frame.anchor_date)>=cutoff)
    chrono_X_train=frame.loc[chrono_train,FEATURE_COLUMNS].copy(); chrono_X_test=frame.loc[chrono_test,FEATURE_COLUMNS].copy()
    if len(chrono_X_train) and len(chrono_X_test):
        chrono_X_train["category"]=chrono_X_train.category.astype("string"); chrono_X_test["category"]=chrono_X_test.category.astype("string")
        chrono_y_train=frame.loc[chrono_train,"trajectory_label"].astype(str); chrono_y_test=frame.loc[chrono_test,"trajectory_label"].astype(str)
        chrono_pipe=_make_pipeline(best_model,FEATURE_COLUMNS, {k.removeprefix("model__"):v for k,v in best_search.best_params_.items()})
        chrono_pipe.fit(chrono_X_train,chrono_y_train,**_fit_params(best_model,chrono_y_train))
        chrono_prob=_probabilities(chrono_pipe,chrono_X_test); chrono_pred=np.asarray(CLASSES)[chrono_prob.argmax(axis=1)]
        chrono_metrics=_metrics(chrono_y_test,chrono_pred,chrono_prob)
    else:
        chrono_metrics={}; chrono_y_test=pd.Series(dtype=str); chrono_pred=np.array([]); chrono_prob=np.empty((0,3))

    # Paired ablations use the same five grouped outer folds and selected model.
    ablation_rows=[]
    for families in SIGNAL_SUBSETS:
        used=CONTEXT + [col for family in families for col in SIGNAL[family]]
        for fold_no,(fit_idx,val_idx) in enumerate(outer_splits,1):
            Xa=X_train.iloc[fit_idx][used]; ya=y_train.iloc[fit_idx]
            Xv=X_train.iloc[val_idx][used]; yv=y_train.iloc[val_idx]
            # Use the selected model family and the corresponding fold-selected
            # hyperparameters; preprocessing is refit within each fold.
            params={k.removeprefix("model__"):v for k,v in model_results[best_model]["fold_params"][fold_no-1].items()}
            estimator=_make_pipeline(best_model,used,params)
            estimator.fit(Xa,ya,**_fit_params(best_model,ya))
            p=_probabilities(estimator,Xv); pred=np.asarray(CLASSES)[p.argmax(axis=1)]
            ablation_rows.append({"model_run_id":best_run_id,"signal_set":"+".join(families),"evaluation_part":"outer_cv","fold_number":fold_no,"metric_name":"macro_f1","metric_value":float(f1_score(yv,pred,labels=CLASSES,average="macro",zero_division=0)),"metadata":{"families":list(families)}})
    ablation_frame=pd.DataFrame(ablation_rows)

    # SHAP explains a deterministic sample of held-out rows. It does not affect
    # model selection or training. Global records cover all classes and context.
    transformed_train=best_pipeline.named_steps["preprocess"].transform(X_train)
    transformed_test=best_pipeline.named_steps["preprocess"].transform(X_test)
    if hasattr(transformed_train,"toarray"): transformed_train=transformed_train.toarray()
    if hasattr(transformed_test,"toarray"): transformed_test=transformed_test.toarray()
    feature_names=list(best_pipeline.named_steps["preprocess"].get_feature_names_out())
    rng=np.random.default_rng(42); shap_n=min(48,len(transformed_test))
    explain_techs=sorted(test_rows.technology_id.unique())[:6]
    required_indices=[int(np.flatnonzero(test_rows.technology_id.to_numpy()==tech)[-1]) for tech in explain_techs]
    remaining=np.setdiff1d(np.arange(len(transformed_test)),np.asarray(required_indices,dtype=int))
    extra=rng.choice(remaining,max(0,shap_n-len(required_indices)),replace=False) if shap_n>len(required_indices) else np.array([],dtype=int)
    shap_indices=np.sort(np.unique(np.concatenate([np.asarray(required_indices,dtype=int),extra])))
    bg_n=min(40,len(transformed_train)); bg=transformed_train[np.linspace(0,len(transformed_train)-1,bg_n,dtype=int)]
    fitted_model=best_pipeline.named_steps["model"]
    shap_data=transformed_test[shap_indices]
    if best_model=="knn":
        # Kernel SHAP avoids the broken installed Numba/CFFI path while still
        # explaining the fitted, prior-adjusted KNN probability function.
        shap_explainer=shap.KernelExplainer(fitted_model.predict_proba,bg)
        raw_values=shap_explainer.shap_values(shap_data,nsamples=min(100,2*len(feature_names)+1),l1_reg=0.0)
        if isinstance(raw_values,list):
            values=np.stack([np.asarray(item) for item in raw_values],axis=2)
        else:
            raw_array=np.asarray(raw_values)
            if raw_array.shape[:2]==(len(shap_indices),len(feature_names)):
                values=raw_array
            elif raw_array.shape[0]==len(feature_names) and raw_array.shape[2]==len(shap_indices):
                values=np.transpose(raw_array,(2,0,1))
            else:
                raise RuntimeError(f"Unexpected Kernel SHAP output shape {raw_array.shape}.")
        base_values=np.tile(np.asarray(shap_explainer.expected_value,dtype=float),(len(shap_indices),1))
    else:
        explain_model=fitted_model.model_ if best_model=="xgboost" else fitted_model
        shap_explainer=shap.Explainer(explain_model,bg,feature_names=feature_names)
        if best_model in {"random_forest","xgboost"}:
            # SHAP's tree additivity check can fail by small floating-point
            # differences for multiclass probabilities; preserve the SHAP values
            # while disabling only that optional numerical assertion.
            raw_values=shap_explainer.shap_values(shap_data,check_additivity=False)
            values=np.stack([np.asarray(item) for item in raw_values],axis=2) if isinstance(raw_values,list) else np.asarray(raw_values)
            expected=np.asarray(shap_explainer.expected_value,dtype=float)
            base_values=np.tile(expected,(len(shap_indices),1)) if expected.ndim else np.repeat(expected,len(shap_indices))
        else:
            shap_values=shap_explainer(shap_data)
            values=np.asarray(shap_values.values)
            base_values=np.asarray(shap_values.base_values)
        if values.ndim==2: values=values[:,:,None]
        # sklearn's string estimators expose classes in sorted order; restore the
        # explicit project class order used by persisted probabilities.
        model_class_order=list(fitted_model.classes_) if best_model!="xgboost" else list(range(len(CLASSES)))
        order=[model_class_order.index(label) if best_model!="xgboost" else CLASSES.index(label) for label in CLASSES]
        if values.shape[2]==len(order): values=values[:,:,order]
        if base_values.ndim>1 and base_values.shape[-1]==len(order): base_values=base_values[:,order]
    shap_rows=[]
    for class_index,label in enumerate(CLASSES):
        if class_index >= values.shape[2]: continue
        global_importance=np.abs(values[:,:,class_index]).mean(axis=0)
        order=np.argsort(global_importance)[::-1]
        for rank,index in enumerate(order,1):
            shap_rows.append({"model_run_id":best_run_id,"class_label":label,"feature_name":feature_names[index],
                "signal_family":_family_for_feature(feature_names[index]),"mean_abs_shap":float(global_importance[index]),"rank":rank})
    test_shap_map={int(index):local for index,local in zip(shap_indices,values)}
    local_rows=[]
    for tech_id in explain_techs:
        candidates=np.flatnonzero(test_rows.technology_id.to_numpy()==tech_id)
        row_index=int(candidates[-1])
        if row_index not in test_shap_map: continue
        local=test_shap_map[row_index]
        label=str(test_pred[row_index]); class_index=CLASSES.index(label)
        order=np.argsort(np.abs(local[:,class_index]))[::-1][:8]
        for index in order:
            local_rows.append({"data_version_id":version_id,"technology_id":str(test_rows.technology_id.iloc[row_index]),"anchor_date":test_rows.anchor_date.iloc[row_index],
                "feature_name":feature_names[index],"shap_value":float(local[index,class_index]),"base_value":float(base_values[np.where(shap_indices==row_index)[0][0]][class_index] if np.asarray(base_values).ndim>1 else base_values[np.where(shap_indices==row_index)[0][0]]),
                "explanation":_plain_driver(feature_names[index],float(local[index,class_index]),label),"predicted_label":label,"prediction_index":row_index})

    # Store exactly the test predictions from the one designated best model.
    prediction_rows=[]
    for i,row in test_rows.iterrows():
        probs=test_prob[i]; pred=str(test_pred[i]); confidence=float(probs.max())
        prediction_rows.append({"model_run_id":best_run_id,"data_version_id":version_id,"technology_id":row.technology_id,"anchor_date":row.anchor_date,
            "predicted_label":pred,"risk_score":float(100*probs[CLASSES.index("Declining")]),"confidence":confidence,
            "low_confidence":bool(row.low_confidence),"probabilities":json.dumps({label:float(probs[j]) for j,label in enumerate(CLASSES)})})

    # Persist all metrics, fitted-run provenance, predictions, ablations and SHAP
    # in one DB transaction. A rerun upserts deterministic run IDs.
    target=_database_url(url or os.getenv("DATABASE_URL")); engine=create_engine(target,pool_pre_ping=True)
    try:
        apply_migrations(target,engine=engine)
        with engine.begin() as connection:
            connection.execute(text("UPDATE ml.data_versions SET git_commit=:commit,git_dirty=:dirty WHERE data_version_id=:v"),{"commit":commit,"dirty":dirty,"v":version_id})
            for name in candidate_names+["majority_class","recent_trend_continues"]:
                run_id=model_results[name]["run_id"] if name in model_results else baseline_results[name]["run_id"]
                protocol=model_protocols.get(name,{"baseline":name,"split":"same grouped technology split","label_rule":LABEL_RULE})
                started_at=started
                selected=(name==best_model)
                connection.execute(text("""INSERT INTO ml.model_runs(model_run_id,data_version_id,model_name,status,started_at,finished_at,seed,protocol,parameters,selected_by_cv,git_commit,git_dirty,metadata)
                    VALUES (:id,:v,:name,'succeeded',:started,:finished,42,CAST(:protocol AS jsonb),CAST(:params AS jsonb),:selected,:commit,:dirty,CAST(:metadata AS jsonb))
                    ON CONFLICT(model_run_id) DO UPDATE SET status='succeeded',finished_at=EXCLUDED.finished_at,protocol=EXCLUDED.protocol,parameters=EXCLUDED.parameters,selected_by_cv=EXCLUDED.selected_by_cv,git_commit=EXCLUDED.git_commit,git_dirty=EXCLUDED.git_dirty,metadata=EXCLUDED.metadata"""),
                    {"id":run_id,"v":version_id,"name":name,"started":started,"finished":datetime.now(timezone.utc),"protocol":json.dumps(_json_clean(protocol),allow_nan=False),
                     "params":json.dumps(_json_clean(model_results[name].get("best_params",{}) if name in model_results else {}),allow_nan=False),"selected":selected,"commit":commit,"dirty":dirty,
                     "metadata":json.dumps(_json_clean({"cv":model_results[name]["cv_summary"] if name in model_results else baseline_results[name]["cv_summary"],"test":model_results[name].get("test_metrics") if name in model_results else baseline_results[name].get("test_metrics"),"chronological":chrono_metrics if selected else None,"n_train":len(train_index),"n_test":len(test_index)}),allow_nan=False)})
                connection.execute(text("DELETE FROM ml.model_metrics WHERE model_run_id=:id"),{"id":run_id})
            connection.execute(text("DELETE FROM ml.shap_local WHERE prediction_id IN (SELECT prediction_id FROM ml.predictions WHERE model_run_id=:id)"),{"id":best_run_id})
            connection.execute(text("DELETE FROM ml.predictions WHERE model_run_id=:id"),{"id":best_run_id})
            connection.execute(text("DELETE FROM ml.shap_global WHERE model_run_id=:id"),{"id":best_run_id})
            connection.execute(text("DELETE FROM ml.ablation_results WHERE model_run_id=:id"),{"id":best_run_id})
            for row in metric_store:
                connection.execute(text("""INSERT INTO ml.model_metrics(model_run_id,evaluation_part,fold_number,metric_name,class_label,metric_value,support,metadata)
                    VALUES (:model_run_id,:evaluation_part,:fold_number,:metric_name,:class_label,:metric_value,:support,CAST(:metadata AS jsonb))"""),{**row,"metadata":json.dumps(row["metadata"])})
            for row in prediction_rows:
                connection.execute(text("""INSERT INTO ml.predictions(model_run_id,data_version_id,technology_id,anchor_date,predicted_label,risk_score,confidence,low_confidence,probabilities)
                    VALUES (:model_run_id,:data_version_id,:technology_id,:anchor_date,:predicted_label,:risk_score,:confidence,:low_confidence,CAST(:probabilities AS jsonb))"""),row)
            for row in ablation_rows:
                connection.execute(text("""INSERT INTO ml.ablation_results(model_run_id,signal_set,evaluation_part,fold_number,metric_name,metric_value,metadata)
                    VALUES (:model_run_id,:signal_set,:evaluation_part,:fold_number,:metric_name,:metric_value,CAST(:metadata AS jsonb))"""),{**row,"metadata":json.dumps(row["metadata"])})
            for row in shap_rows:
                connection.execute(text("""INSERT INTO ml.shap_global(model_run_id,class_label,feature_name,signal_family,mean_abs_shap,rank)
                    VALUES (:model_run_id,:class_label,:feature_name,:signal_family,:mean_abs_shap,:rank)"""),row)
            for row in local_rows:
                pred=connection.execute(text("SELECT prediction_id FROM ml.predictions WHERE model_run_id=:model AND technology_id=:tech AND anchor_date=:date"),{"model":best_run_id,"tech":row["technology_id"],"date":row["anchor_date"]}).scalar_one()
                connection.execute(text("""INSERT INTO ml.shap_local(prediction_id,feature_name,shap_value,base_value,explanation)
                    VALUES (:prediction_id,:feature_name,:shap_value,:base_value,:explanation)
                    ON CONFLICT(prediction_id,feature_name) DO UPDATE SET shap_value=EXCLUDED.shap_value,base_value=EXCLUDED.base_value,explanation=EXCLUDED.explanation"""),{**row,"prediction_id":pred})
    finally: engine.dispose()

    comparison=[]
    for row in summary_rows:
        if row["model"] in candidate_names:
            row["test"] = model_results[row["model"]].get("test_metrics")
        else: row["test"]=baseline_results[row["model"]]["test_metrics"]
        comparison.append(row)
    comparison_frame=pd.DataFrame(comparison)
    means={subset:ablation_frame[ablation_frame.signal_set==subset].groupby("signal_set").metric_value.agg(["mean","std"]).iloc[0].to_dict() for subset in ablation_frame.signal_set.unique()}
    best_cv=model_results[best_model]["cv_summary"]["macro_f1"]["mean"]
    trend_cv=baseline_results["recent_trend_continues"]["cv_summary"]["macro_f1"]["mean"]
    enterprise_sentiment_lift=best_cv-means.get("community",{}).get("mean",np.nan)
    summary={"data_version_id":version_id,"git_commit":commit,"git_dirty":dirty,"best_model":best_model,"best_run_id":best_run_id,
        "best_cv_macro_f1":best_cv,"trend_baseline_cv_macro_f1":trend_cv,"full_model_lift_over_trend":best_cv-trend_cv,
        "enterprise_sentiment_increment_over_community_only":enterprise_sentiment_lift,
        "test_metrics":test_metrics,"test_confusion_matrix":confusion_matrix(y_test,test_pred,labels=CLASSES).tolist(),
        "test_class_order":CLASSES,"test_declining_recall":test_metrics["Declining_recall"],"test_n":len(y_test),"train_n":len(y_train),
        "grouped_test_technology_count":int(groups.iloc[test_index].nunique()),"grouped_train_technology_count":int(groups.iloc[train_index].nunique()),
        "chronological_cutoff":cutoff.date().isoformat(),"chronological_train_n":int(chrono_train.sum()),"chronological_test_n":int(chrono_test.sum()),"chronological_metrics":chrono_metrics,
        "ablation_summary":means,"shap_rows":len(shap_rows),"local_shap_rows":len(local_rows),
        "high_score_warning":bool(any(r["cv"]["macro_f1"]["mean"]>.95 for r in summary_rows if r["model"] in candidate_names)),
        "simulation_caveat":"All observations and labels are generated from the approved simulation assumptions. Metrics describe this synthetic scenario, not real technologies or enterprises."}
    return ExperimentResult(summary,comparison_frame,ablation_frame,best_run_id)


if __name__=="__main__":
    result=run_experiment(os.getenv("DATA_VERSION_ID"))
    print(json.dumps(result.result_summary,indent=2,default=_json_value))
    print(result.comparison.to_string(index=False))
