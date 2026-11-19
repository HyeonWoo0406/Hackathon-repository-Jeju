"""데이터셋 카탈로그와 로컬 CSV 로더.

실제 자료는 이용 조건을 확인한 뒤 별도 관리하고 CATALOG에 등록한다.
저장소에 포함된 버스 CSV는 합성 시연 자료다.
"""
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Dataset:
    name: str
    path: str
    source: str
    keywords: list[str] = field(default_factory=list)
    synthetic: bool = False


CATALOG = [
    Dataset(
        name="버스 노선별 이용 현황 (합성 시연 자료)",
        path="data/sample_bus_routes.csv",
        source="합성 시연 데이터 — 실제 제주 버스 통계가 아님 (3-02 형식 예시)",
        keywords=["노선", "버스", "route", "시간대", "시간", "요일", "승차", "하차", "이용자"],
        synthetic=True,
    ),
    Dataset(
        name="버스 정류소별 이용 현황 (합성 시연 자료)",
        path="data/sample_bus_stops.csv",
        source="합성 시연 데이터 — 실제 제주 버스 통계가 아님 (3-04 형식 예시)",
        keywords=["정류소", "정류장", "stop", "시간대", "시간", "요일", "승차", "하차", "이용자"],
        synthetic=True,
    ),
]


def find_dataset(question: str) -> Dataset:
    """정류소 질의에는 정류소 자료를, 그 외 버스 질의에는 노선 자료를 선택한다."""
    if "정류소" in question or "정류장" in question or "stop" in question.lower():
        return CATALOG[1]
    return CATALOG[0]


def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return pd.read_csv(p)
