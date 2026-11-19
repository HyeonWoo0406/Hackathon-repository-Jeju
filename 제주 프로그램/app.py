import streamlit as st
from dotenv import load_dotenv

from src.agent import JejuAgent
from src.llm import get_provider

load_dotenv()
st.title("제주 버스 노선·시간대 수요 분석 에이전트")
st.caption("버스 노선·시간대·요일·정류소별 이용자 집계를 탐색합니다. 이용량이 높은 결과는 검토 후보이며 배차·혼잡 판단이 아닙니다.")
st.warning("현재 화면은 합성 시연 데이터만 사용합니다. 결과는 실제 제주 버스 통계가 아닙니다.")

q = st.text_input("질문", "시간대별 노선 이용량을 보여줘")
if st.button("분석하기"):
    try:
        r = JejuAgent(get_provider()).ask(q)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.subheader("요약")
        st.write(r.summary)
        st.subheader(f"{r.group_label}별 이용자 수 (합계)")
        st.bar_chart(r.table.set_index(r.group_col)[r.chart_col])
        st.dataframe(r.table, use_container_width=True, hide_index=True)
        st.subheader("근거 데이터")
        st.write(f"{r.dataset.name} — {r.dataset.source}")
        st.subheader("한계")
        for x in r.limitations:
            st.write(f"- {x}")
