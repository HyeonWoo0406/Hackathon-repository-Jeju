"""질문 -> 데이터셋 탐색 -> 이용량 집계 -> 요약(근거/한계 명시)."""
from dataclasses import dataclass

import pandas as pd

from .data_loader import Dataset, find_dataset, load_data
from .llm import LLMProvider

SYSTEM = "당신은 제주 공공데이터 분석 도우미입니다. 주어진 분석 결과만 근거로 쉬운 한국어로 요약하세요."

@dataclass
class AgentResult:
    summary: str
    dataset: Dataset
    table: pd.DataFrame
    group_col: str
    group_label: str
    chart_col: str
    limitations: list[str]


DIMENSIONS = {
    "base_hour": ("시간대", ("시간대별", "시간대", "시간별", "시간")),
    "day_of_week": ("요일", ("요일별", "요일")),
    "bus_route_name": ("노선", ("노선별", "노선")),
    "stop_name": ("정류소", ("정류소별", "정류소", "정류장")),
    "get_on_off_type": ("승하차 유형", ("승하차 유형별", "승하차", "승차", "하차")),
    "user_category": ("이용자 유형", ("이용자 유형별", "이용자 유형", "이용자 구분", "어린이", "청소년")),
}

LIMITATIONS = [
    "현재 결과는 합성 시연 데이터 기준이며 실제 제주 버스 통계가 아닙니다.",
    "현재 MVP는 선택한 한 차원으로 이용자 수를 합산하며 자연어 기간·조건 필터는 적용하지 않습니다.",
    "태그 기반 이용자 집계만 사용합니다. 차량 정원·잔여 좌석 정보가 없어 혼잡률·혼잡 예측·최적 배차를 제공하지 않습니다.",
    "이용량이 높은 그룹은 검토 후보일 뿐이며 운영 결정을 자동으로 권고하지 않습니다.",
    "요약 품질은 선택한 LLM 제공자에 따라 달라집니다(mock은 계산 사실을 그대로 보여줍니다).",
]


def resolve_group(question: str, dataset: Dataset) -> tuple[str, str]:
    """질문에서 데이터셋에 존재하는 집계 차원을 선택한다."""
    available = set(load_data(dataset.path).columns)
    for column, (label, aliases) in DIMENSIONS.items():
        if column in available and any(alias in question for alias in aliases):
            return column, label
    default_column = "base_hour"
    if default_column not in available:
        raise ValueError(f"{dataset.name} 데이터에 기본 집계 기준 {default_column}이 없습니다.")
    return default_column, DIMENSIONS[default_column][0]


def analyze(df: pd.DataFrame, group_col: str) -> tuple[pd.DataFrame, str]:
    """요청 차원별 이용자 수를 합산하고 최대 그룹을 설명한다."""
    missing = {group_col, "user_count"} - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(sorted(missing))}")
    values = df[[group_col, "user_count"]].dropna()
    if values.empty:
        raise ValueError("분석할 이용량 데이터가 없습니다.")
    values = values.copy()
    values["user_count"] = pd.to_numeric(values["user_count"], errors="raise")
    if (values["user_count"] < 0).any():
        raise ValueError("user_count에는 음수 값을 사용할 수 없습니다.")
    table = (
        values.groupby(group_col, as_index=False)["user_count"]
        .sum()
        .sort_values("user_count", ascending=False)
        .reset_index(drop=True)
    )
    top = table.iloc[0]
    facts = f"합성 시연 자료에서 {top[group_col]}의 이용자 집계가 가장 높았습니다({top['user_count']:,.0f}명)."
    return table, facts


class JejuAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def ask(self, question: str) -> AgentResult:
        unsupported = ("혼잡", "좌석", "배차", "노선 변경", "날씨", "기상", "관광")
        if any(term in question for term in unsupported):
            raise ValueError(
                "현재는 버스 이용량 집계만 지원합니다. 혼잡·좌석·최적 배차·날씨·관광 분석은 제공하지 않습니다."
            )
        ds = find_dataset(question)
        df = load_data(ds.path)
        group_col, group_label = resolve_group(question, ds)
        table, facts = analyze(df, group_col)
        prompt = f"[질문]\n{question}\n\n[분석 결과]\n{facts}"
        summary = self.llm.complete(SYSTEM, prompt)
        return AgentResult(summary, ds, table, group_col, group_label, "user_count", LIMITATIONS)

    @staticmethod
    def render_text(r: AgentResult) -> str:
        lim = "\n".join(f"- {x}" for x in r.limitations)
        rows = "\n".join(
            f"- {row[r.group_col]}: {row[r.chart_col]:,.0f}명"
            for _, row in r.table.iterrows()
        )
        return (
            f"{r.summary}\n\n[분석 기준] {r.group_label}별 이용자 수 합계\n{rows}"
            f"\n\n[근거 데이터] {r.dataset.name}\n출처/자료 유형: {r.dataset.source}"
            f"\n\n[한계]\n{lim}"
        )
