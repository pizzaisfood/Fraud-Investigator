# ML 팀 인터페이스 가이드

> LightGBM 모델 학습 시 feature 명세를 정의합니다.  
> **feature 순서와 이름이 정확히 일치해야 합니다. 틀리면 에러 없이 잘못된 예측이 나옵니다.**

---

## 모델 파일 위치

```
data/fraud_model.pkl   ← 이 경로에 저장해 주세요
```

파이프라인이 시작될 때 이 파일을 자동으로 로드합니다.  
파일이 없으면 `ml_score = None`으로 처리되고 파이프라인은 정상 진행됩니다.

---

## Feature 목록 (순서 고정)

> **이 순서 그대로 학습해야 합니다.** 순서가 바뀌면 모델이 잘못된 예측을 냅니다.

| 순서 | 이름 | 타입 | 설명 | 기본값 |
|---|---|---|---|---|
| 1 | `amt` | `float` | 거래 금액 | — |
| 2 | `amount_ratio` | `float` | 거래금액 / 고객 30일 평균금액 | `1.0` |
| 3 | `is_unusual_hour` | `int` (0/1) | 새벽 0~5시 거래 여부 | `0` |
| 4 | `is_unusual_city` | `int` (0/1) | 평소와 다른 도시 여부 | `0` |
| 5 | `is_unusual_category` | `int` (0/1) | 평소와 다른 카테고리 여부 | `0` |
| 6 | `merchant_risk_score` | `int` | 가맹점 위험 점수 (low=0, medium=1, high=2) | `0` |
| 7 | `avg_amount_30d` | `float` | 고객 30일 평균 거래금액 | `0.0` |
| 8 | `std_amount_30d` | `float` | 고객 30일 거래금액 표준편차 | `0.0` |
| 9 | `chargeback_rate` | `float` | 가맹점 차지백 비율 (0.0~1.0) | `0.0` |
| 10 | `fraud_report_count` | `float` | 가맹점 사기 신고 건수 | `0.0` |

---

## SHAP Feature 중요도 (참고)

모델 학습 시 참고할 feature 중요도입니다.

| 순위 | Feature | SHAP 값 |
|---|---|---|
| 1 | `amt` | 2.341 |
| 2 | `chargeback_rate` | 1.153 |
| 3 | `fraud_report_count` | 0.593 |
| 4 | `amount_ratio` | 0.487 |
| 5 | `merchant_risk_score` | 0.312 |

---

## 출력 형식

| 항목 | 내용 |
|---|---|
| 파일 형식 | `joblib.dump(model, "data/fraud_model.pkl")` |
| 예측 메서드 | `model.predict_proba(X)` 사용 (확률값 필요) |
| 반환값 | `[[정상확률, 사기확률], ...]` — 파이프라인이 `[:, 1]` (사기 확률)만 사용 |

```python
# 저장 예시
import joblib
joblib.dump(lgbm_model, "data/fraud_model.pkl")

# 파이프라인 내부 사용 방식 (참고)
proba = model.predict_proba([[amt, amount_ratio, ...]])
ml_score = float(proba[0][1])  # 사기 확률 (0.0 ~ 1.0)
```

---

## 학습 데이터 feature 추출 예시

```python
import pandas as pd

df["amount_ratio"] = df["amt"] / df["avg_amount_30d"].replace(0, 1)
df["is_unusual_hour"] = df["hour"].apply(lambda h: 1 if h < 6 else 0).astype(int)
df["merchant_risk_score"] = df["risk_level"].map({"low": 0, "medium": 1, "high": 2})

feature_cols = [
    "amt", "amount_ratio", "is_unusual_hour", "is_unusual_city",
    "is_unusual_category", "merchant_risk_score", "avg_amount_30d",
    "std_amount_30d", "chargeback_rate", "fraud_report_count"
]

X = df[feature_cols]  # 순서 고정
y = df["is_fraud"]
```
