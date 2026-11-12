"""하자 접수 화면 (입점 매장·현장 직원용). 저장은 db.py만 부른다."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

import db

BASE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))  # 웹 서버는 UTC라서 한국 날짜로 맞춘다

st.set_page_config(page_title="하자 접수", page_icon=":material/build:", layout="centered")


@st.cache_data
def location_options() -> list[str]:
    df = pd.read_csv(BASE / "data" / "공사정보.csv", encoding="utf-8-sig", dtype=str)
    return sorted(df["위치"].dropna().unique().tolist())


st.title("하자 접수")
st.caption("시설 하자를 발견하면 아래에 적어 주세요. 시설관리팀이 확인 후 처리합니다.")

with st.form("intake", clear_on_submit=True, border=True):
    발견일 = st.date_input("발견일", value=datetime.now(KST).date(), format="YYYY-MM-DD")
    접수자 = st.text_input("접수자", placeholder="이름")
    부서 = st.text_input("부서·매장", placeholder="예: 3F 패션관 운영파트, 502호 매장")
    위치 = st.selectbox(
        "위치",
        location_options(),
        index=None,
        accept_new_options=True,
        placeholder="목록에서 고르거나 직접 입력 (예: 2F 화장실)",
    )
    내용 = st.text_area("내용", placeholder="어디가 어떻게 이상한지 적어 주세요.", height=150)
    submitted = st.form_submit_button("접수", type="primary", icon=":material/send:", width="stretch")

if submitted:
    빈칸 = [name for name, v in (("접수자", 접수자), ("내용", 내용)) if not (v or "").strip()]
    if 빈칸:
        st.error(f"{'·'.join(빈칸)}을(를) 입력해 주세요. 저장하지 않았습니다.", icon=":material/error:")
    else:
        no = db.add_intake(발견일, 접수자.strip(), 부서.strip(), (위치 or "").strip(), 내용.strip())
        st.success(f"접수 번호 {no}번으로 접수되었습니다.", title="접수 완료", icon=":material/check_circle:")
