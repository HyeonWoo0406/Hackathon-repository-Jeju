import unittest

import pandas as pd

from src.agent import JejuAgent, analyze, resolve_group
from src.data_loader import find_dataset, load_data
from src.llm import MockProvider


class BusDemandAgentTests(unittest.TestCase):
    def test_selects_stop_dataset_for_stop_question(self):
        dataset = find_dataset("정류소별 하차 이용량")

        self.assertIn("정류소", dataset.name)
        self.assertTrue(dataset.synthetic)

    def test_resolves_supported_dimensions(self):
        route_dataset = find_dataset("노선별 이용량")
        stop_dataset = find_dataset("정류소별 이용량")

        self.assertEqual(resolve_group("노선별 이용량", route_dataset)[0], "bus_route_name")
        self.assertEqual(resolve_group("시간대별 이용량", route_dataset)[0], "base_hour")
        self.assertEqual(resolve_group("요일별 이용량", route_dataset)[0], "day_of_week")
        self.assertEqual(resolve_group("승하차별 이용량", route_dataset)[0], "get_on_off_type")
        self.assertEqual(resolve_group("이용자 유형별 이용량", route_dataset)[0], "user_category")
        self.assertEqual(resolve_group("정류소별 이용량", stop_dataset)[0], "stop_name")

    def test_sums_counts_by_requested_dimension(self):
        frame = pd.DataFrame(
            {
                "group": ["A", "B", "A"],
                "user_count": [4, 7, 3],
            }
        )

        table, facts = analyze(frame, "group")

        self.assertEqual(table.set_index("group")["user_count"].to_dict(), {"A": 7, "B": 7})
        self.assertIn("합성 시연 자료", facts)

    def test_reports_invalid_count_data(self):
        with self.assertRaisesRegex(ValueError, "음수"):
            analyze(pd.DataFrame({"group": ["A"], "user_count": [-1]}), "group")

    def test_agent_labels_sample_and_rejects_out_of_scope_requests(self):
        result = JejuAgent(MockProvider()).ask("시간대별 노선 이용량")
        rendered = JejuAgent.render_text(result)

        self.assertTrue(result.dataset.synthetic)
        self.assertIn("실제 제주 버스 통계가 아님", rendered)
        self.assertIn("혼잡률", rendered)
        with self.assertRaisesRegex(ValueError, "혼잡"):
            JejuAgent(MockProvider()).ask("혼잡도를 알려줘")

    def test_sample_csvs_use_expected_dimensions(self):
        routes = load_data("data/sample_bus_routes.csv")
        stops = load_data("data/sample_bus_stops.csv")

        self.assertTrue({"base_hour", "day_of_week", "bus_route_name", "get_on_off_type", "user_category", "user_count"}.issubset(routes.columns))
        self.assertTrue({"base_hour", "day_of_week", "stop_name", "get_on_off_type", "user_category", "user_count"}.issubset(stops.columns))


if __name__ == "__main__":
    unittest.main()
