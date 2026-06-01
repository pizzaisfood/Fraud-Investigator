"""
FraudInvestigator — 2주차 v2 (10 features, GitHub ml_fraud_scorer.py 기준)
변경 사항:
- 피처를 깃허브 _FEATURE_NAMES 10개에 맞춤
- is_night_transaction: h < 6 or h >= 22 (이정훈 코드와 동일)
- credit_util_ratio 제거 (깃에 없음)
"""
import os, json, time
import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, classification_report,
                             precision_score, recall_score, f1_score)
import shap

PROJ = "/Users/jinyoung/내 드라이브/학교/3학년1학기/생성형 AI와 비즈니스_문현실/팀프로젝트/생성형 팀플/fraud-investigator-agent"
DATA_DIR = os.path.join(PROJ, 'data')
WEEK2_DIR = os.path.join(PROJ, '2주차')
os.makedirs(os.path.join(WEEK2_DIR, '모델'), exist_ok=True)
os.makedirs(os.path.join(WEEK2_DIR, '차트(분석결과)'), exist_ok=True)
RESULTS = {}

# ============================================================
# Day 9: Feature Engineering (10 features - GitHub 호환)
# ============================================================
print("="*70); print("Day 9: Feature Engineering (10 features, GitHub 호환)"); print("="*70)
t0 = time.time()

df = pd.read_csv(os.path.join(DATA_DIR, 'fraudTrain.csv'))
cp = pd.read_csv(os.path.join(DATA_DIR, 'customer_profiles.csv'))
mr = pd.read_csv(os.path.join(DATA_DIR, 'merchant_risk.csv'))

print(f"  fraudTrain.csv: {df.shape}")
print(f"  customer_profiles.csv: {cp.shape}")
print(f"  merchant_risk.csv: {mr.shape}")

df['trans_date_trans_time'] = pd.to_datetime(df['trans_date_trans_time'])

def build_features(df, cp, mr):
    """
    GitHub ml_fraud_scorer.py의 _FEATURE_NAMES와 정확히 일치시킴.
    is_night_transaction은 transaction_analyzer.py 코드와 동일하게 h<6 or h>=22.
    """
    features = df.copy()

    # 거래 시각 파생 (transaction_analyzer.py와 동일)
    features['hour_of_day'] = features['trans_date_trans_time'].dt.hour
    features['is_night_transaction'] = features['hour_of_day'].apply(
        lambda h: 1 if (h < 6 or h >= 22) else 0)
    features['is_weekend'] = (features['trans_date_trans_time'].dt.dayofweek >= 5).astype(int)

    # 고객 프로필 merge
    features = features.merge(
        cp[['cc_num','avg_amount_30d','std_amount_30d','credit_limit','avg_daily_txn_count']],
        on='cc_num', how='left')

    # amount_z_score (customer_profile_tool.py와 동일 공식)
    features['amount_z_score'] = np.where(
        features['std_amount_30d'] > 0,
        (features['amt'] - features['avg_amount_30d']) / features['std_amount_30d'],
        0.0)

    # 가맹점 위험도 merge
    features = features.merge(
        mr[['merchant_id','fraud_report_count','chargeback_rate','risk_level']].rename(columns={'merchant_id':'merchant'}),
        on='merchant', how='left')

    # 컬럼명 통일 (amt → amount)
    features = features.rename(columns={'amt': 'amount'})

    return features

features_df = build_features(df, cp, mr)

# 깃허브 _FEATURE_NAMES 순서 그대로
feature_cols = [
    'amount', 'hour_of_day', 'is_night_transaction', 'is_weekend',
    'amount_z_score', 'avg_amount_30d', 'credit_limit',
    'fraud_report_count', 'chargeback_rate', 'avg_daily_txn_count'
]

# NaN 처리
for c in feature_cols:
    features_df[c] = features_df[c].fillna(0)

print(f"  Feature 행렬: {features_df.shape}, 사용 feature: {len(feature_cols)}개 (GitHub 호환)")
RESULTS['day9'] = {
    'rows': len(features_df),
    'feature_cols': feature_cols,
    'elapsed_sec': round(time.time()-t0, 1)
}
print(f"  ✅ Day 9 완료 ({RESULTS['day9']['elapsed_sec']}초)")

# ============================================================
# Day 10-11: 학습 + 평가 (HistGBM — LightGBM 대체)
# ============================================================
print("\n" + "="*70); print("Day 10-11: 모델 학습 (HistGBM, LightGBM 대체)"); print("="*70)
t0 = time.time()

X = features_df[feature_cols]
y = features_df['is_fraud']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)
print(f"  Train: {len(X_train):,}건 | Test: {len(X_test):,}건")
print(f"  Train fraud 비율: {y_train.mean():.4f}")

model = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.05, max_depth=8,
    class_weight='balanced', random_state=42)
model.fit(X_train, y_train)
print(f"  모델 학습 완료 ({time.time()-t0:.1f}초)")

y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = model.predict(X_test)
auc = roc_auc_score(y_test, y_pred_proba)
f1 = f1_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
K = int(len(y_test) * 0.05)
top_k_idx = y_pred_proba.argsort()[-K:]
precision_at_k = y_test.iloc[top_k_idx].mean()

print(f"\n📊 평가 지표")
print(f"   AUC-ROC      : {auc:.4f}")
print(f"   F1 Score     : {f1:.4f}")
print(f"   Precision    : {precision:.4f}")
print(f"   Recall       : {recall:.4f}")
print(f"   Precision@5% : {precision_at_k:.4f}")

print(f"\n   Threshold sweep:")
threshold_results = []
for thr in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    yp = (y_pred_proba >= thr).astype(int)
    p, r, f = precision_score(y_test,yp), recall_score(y_test,yp), f1_score(y_test,yp)
    print(f"   thr={thr}: P={p:.3f} R={r:.3f} F1={f:.3f}")
    threshold_results.append({'thr': thr, 'P': float(p), 'R': float(r), 'F1': float(f)})

# 모델 저장 (GitHub Tool과 호환되는 형식)
model_path = os.path.join(WEEK2_DIR, '모델', 'fraud_model.pkl')
joblib.dump(model, model_path)

# 추가: data/ 루트에도 저장 (이정훈 LangGraph가 ../../data/fraud_model.pkl 경로로 로드)
data_model_path = os.path.join(DATA_DIR, 'fraud_model.pkl')
joblib.dump(model, data_model_path)

# 메타 정보
meta = {
    'algo': 'sklearn HistGradientBoostingClassifier (LightGBM 대체)',
    'feature_cols': feature_cols,
    'feature_count': len(feature_cols),
    'github_compatible': True,
    'metrics': {'auc_roc': float(auc), 'f1': float(f1),
                'precision': float(precision), 'recall': float(recall),
                'precision_at_5pct': float(precision_at_k)},
    'threshold_sweep': threshold_results,
    'training_size': len(X_train), 'test_size': len(X_test),
    'fraud_ratio_train': float(y_train.mean()),
    'note_libomp': 'libomp 설치 후 LightGBM scale_pos_weight=171.8 재학습 권장'
}
with open(os.path.join(WEEK2_DIR, '모델', 'models_meta.json'), 'w', encoding='utf-8') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)
print(f"\n  ✅ 모델 저장: 2주차/모델/fraud_model.pkl + data/fraud_model.pkl")

RESULTS['day10_11'] = {
    'auc': float(auc), 'f1': float(f1),
    'precision': float(precision), 'recall': float(recall),
    'precision_at_5pct': float(precision_at_k),
    'threshold_sweep': threshold_results,
    'elapsed_sec': round(time.time()-t0, 1)
}

# ============================================================
# Day 11: SHAP
# ============================================================
print("\n" + "="*70); print("Day 11: SHAP 피처 중요도"); print("="*70)
t0 = time.time()

explainer = shap.Explainer(model, X_train.sample(200, random_state=42))
shap_values = explainer(X_test[:300], check_additivity=False)
importance = np.abs(shap_values.values).mean(axis=0)
importance_df = pd.DataFrame({'feature': feature_cols, 'shap_importance': importance})
importance_df = importance_df.sort_values('shap_importance', ascending=False)

print("\n  📈 SHAP 기준 피처 중요도 (10개 전부)")
for _, row in importance_df.iterrows():
    print(f"    {row['feature']:25s}  {row['shap_importance']:.4f}")

try:
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_test[:300], feature_names=feature_cols, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(WEEK2_DIR, '차트(분석결과)', 'fig_shap_summary.png'), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  ✅ SHAP plot 저장")
except Exception as e:
    print(f"  ⚠️ SHAP plot 실패: {e}")

RESULTS['day11'] = {
    'feature_importance': importance_df.to_dict('records'),
    'elapsed_sec': round(time.time()-t0, 1)
}

# ============================================================
# Day 12-13: Rule + ML 결합 + 케이스 시뮬레이션
# ============================================================
print("\n" + "="*70); print("Day 12-13: Rule + ML 결합 함수"); print("="*70)

def calculate_final_risk_score(rule_score, ml_score, merchant_risk_score):
    final = rule_score * 0.55 + ml_score * 100 * 0.35 + merchant_risk_score * 0.10
    return min(round(final, 1), 100)

def classify_risk_level(final_score, rule_hits=None):
    if rule_hits:
        hit_ids = {r['rule_id'] for r in rule_hits}
        if {'R004','R005'}.issubset(hit_ids):
            return 'critical', 'temporary_hold'
    if final_score >= 80: return 'critical', 'temporary_hold'
    elif final_score >= 60: return 'high', 'customer_verify'
    elif final_score >= 35: return 'medium', 'monitor'
    else: return 'low', 'approve'

print("\n  --- 케이스 시뮬레이션 ---")
cases = [
    {"name":"케이스 A (정상)",    "rule":0,  "ml":0.04,"merch":0,  "hits":[]},
    {"name":"케이스 B (고객확인)","rule":55, "ml":0.71,"merch":50, "hits":[{'rule_id':'R001'},{'rule_id':'R002'},{'rule_id':'R007'}]},
    {"name":"케이스 C (임시보류)","rule":95, "ml":0.93,"merch":100,"hits":[{'rule_id':'R001'},{'rule_id':'R002'},{'rule_id':'R004'},{'rule_id':'R005'},{'rule_id':'R007'}]},
]
case_results = []
for c in cases:
    score = calculate_final_risk_score(c['rule'], c['ml'], c['merch'])
    level, action = classify_risk_level(score, c['hits'])
    print(f"    {c['name']:25s}  최종={score:5.1f}  등급={level:8s}  조치={action}")
    case_results.append({'name': c['name'], 'score': score, 'level': level, 'action': action})

RESULTS['day12_13'] = {'cases': case_results}

# ============================================================
# Day 14: evaluation_labels.csv 정교화 + 룰 hit 통계
# ============================================================
print("\n" + "="*70); print("Day 14: evaluation_labels 정교화 + 룰 통계"); print("="*70)
t0 = time.time()

fe = features_df.copy()

# 룰 hit 계산 (정의된 룰대로)
# R001: 고객 평균의 5배 이상 (amount_ratio 사용 → 새로 계산)
fe['amount_ratio'] = fe['amount'] / (fe['avg_amount_30d'] + 1)
fe['R001'] = (fe['amount_ratio'] >= 5).astype(int) * 25
# R002: 새벽 시간대 (이정훈 기준 h<6 or h>=22)
fe['R002'] = (fe['is_night_transaction'] == 1).astype(int) * 10
# R003: 평소 도시와 다른 도시 + 고액 (※ 합성 데이터 특성상 항상 0)
# customer_profiles의 home_city로 merge 필요
fe = fe.merge(cp[['cc_num','home_city']], on='cc_num', how='left')
fe['R003'] = ((fe['city'] != fe['home_city']) & (fe['amount_ratio'] >= 2)).astype(int) * 20
# R004: 고위험 가맹점
fe['R004'] = (fe['risk_level']=='high').astype(int) * 25
# R005: 직전 거래 10분 이내
fe = fe.sort_values(['cc_num','trans_date_trans_time'])
fe['time_diff_min'] = fe.groupby('cc_num')['trans_date_trans_time'].diff().dt.total_seconds() / 60
fe['R005'] = ((fe['time_diff_min'] <= 10) & (fe['time_diff_min'].notna())).astype(int) * 20
# R006: 한도 70% 이상
fe['credit_util_ratio'] = fe['amount'] / (fe['credit_limit'] + 1)
fe['R006'] = (fe['credit_util_ratio'] >= 0.7).astype(int) * 15
# R007: 평소 미사용 카테고리
fe = fe.merge(cp[['cc_num','usual_categories']], on='cc_num', how='left')
fe['R007'] = fe.apply(
    lambda r: 5 if str(r['category']) not in str(r['usual_categories']) else 0,
    axis=1)

fe['rule_score'] = fe[['R001','R002','R003','R004','R005','R006','R007']].sum(axis=1)

# 평가 샘플 300건
print("  평가 샘플 300건 라벨링...")
sample_idx = features_df.sample(n=300, random_state=42).index
sample = fe.loc[sample_idx].copy()

sample_X = sample[feature_cols].fillna(0)
sample['ml_score_pred'] = model.predict_proba(sample_X)[:, 1]
mrs_map = {'low':0,'medium':50,'high':100}
sample['mrs'] = sample['risk_level'].map(mrs_map).fillna(0)
sample['final_score'] = (sample['rule_score']*0.55 + sample['ml_score_pred']*100*0.35 + sample['mrs']*0.10).clip(upper=100)

def label_row(row):
    hits = [{'rule_id': r} for r in ['R001','R002','R003','R004','R005','R006','R007'] if row[r] > 0]
    level, action = classify_risk_level(row['final_score'], hits)
    reasons = ','.join([r for r in ['R001','R002','R003','R004','R005','R006','R007'] if row[r] > 0])
    return pd.Series({
        'transaction_id': row['trans_num'],
        'expected_risk_level': level,
        'expected_action': action,
        'expected_reasons': reasons if reasons else 'normal_pattern'
    })

eval_labels = sample.apply(label_row, axis=1)
out_path = os.path.join(DATA_DIR, 'evaluation_labels.csv')
eval_labels.to_csv(out_path, index=False)

print(f"\n  📋 정교화된 분포")
print(eval_labels['expected_risk_level'].value_counts().to_string())
print(f"\n  ✅ 저장: {out_path}")

# 룰 hit 통계 (채주형 요청 검증 마무리)
print("\n  --- 전체 룰 hit 통계 ---")
total = len(fe)
rule_stats = {}
for r in ['R001','R002','R003','R004','R005','R006','R007']:
    hit_cnt = (fe[r] > 0).sum()
    hit_fraud = fe[(fe[r] > 0) & (fe['is_fraud']==1)].shape[0]
    fraud_rate = hit_fraud / hit_cnt if hit_cnt > 0 else 0
    print(f"   {r}: hit {hit_cnt:>9,}건 ({hit_cnt/total*100:5.2f}%) | fraud {hit_fraud:>5,}건 (fraud율 {fraud_rate*100:5.2f}%)")
    rule_stats[r] = {'hit': int(hit_cnt), 'hit_pct': round(hit_cnt/total*100, 2),
                     'fraud': int(hit_fraud), 'fraud_rate_pct': round(fraud_rate*100, 2)}

r004_r005_both = ((fe['R004']>0) & (fe['R005']>0)).sum()
r004_r005_fraud = fe[(fe['R004']>0) & (fe['R005']>0) & (fe['is_fraud']==1)].shape[0]
print(f"\n   R004+R005 동시 hit: {r004_r005_both:,}건, 그중 fraud {r004_r005_fraud}건 ({r004_r005_fraud/r004_r005_both*100:.2f}%)")

RESULTS['day14'] = {
    'eval_label_dist': eval_labels['expected_risk_level'].value_counts().to_dict(),
    'eval_count': len(eval_labels),
    'rule_stats': rule_stats,
    'r004_r005_both': int(r004_r005_both),
    'r004_r005_both_fraud': int(r004_r005_fraud),
    'elapsed_sec': round(time.time()-t0, 1)
}

# 결과 저장
with open(os.path.join(WEEK2_DIR, 'week2_results.json'), 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "="*70)
print("✅ 2주차 v2 완료 (10 features, GitHub 호환)")
print("="*70)
