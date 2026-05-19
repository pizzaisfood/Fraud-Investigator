import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from services.investigate import investigate, sample_transaction

st.title("사기 거래 조사")

use_sample = st.sidebar.checkbox("샘플 거래", value=True)

if use_sample:
    tx = sample_transaction()
else:
    tx = {
        "trans_num": st.sidebar.text_input("거래번호", "abc123"),
        "trans_date_trans_time": st.sidebar.text_input("시각", "2020-06-21 03:14:25"),
        "cc_num": int(st.sidebar.number_input("카드번호", value=123456789)),
        "merchant": st.sidebar.text_input("가맹점", "fraud_Shop_Name"),
        "amt": st.sidebar.number_input("금액", value=1500.0),
        "category": st.sidebar.text_input("카테고리", "shopping_net"),
        "city": st.sidebar.text_input("도시", "Seoul"),
        "state": st.sidebar.text_input("state", "KR"),
    }

st.write("입력")
st.json(tx)

if st.button("조사"):
    try:
        res = investigate(tx)
    except Exception as e:
        st.error(str(e))
        st.stop()

    st.write("위험등급:", res.get("risk_level"))
    st.write("조치:", res.get("action_decision"))
    st.write("룰 점수:", res.get("rule_score"), "/ hits:", res.get("rule_hits"))

    ml = res.get("ml_score")
    if ml is not None:
        st.write("ML:", round(ml * 100, 1), "%")
    else:
        st.write("ML: (모델 없음)")

    st.subheader("리포트")
    st.markdown(res.get("report") or "(없음)")

    if st.checkbox("전체 state 보기"):
        st.json(res)
