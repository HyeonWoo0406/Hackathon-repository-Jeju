import sys

from dotenv import load_dotenv

from src.agent import JejuAgent
from src.llm import get_provider

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv()
    q = " ".join(sys.argv[1:]) or "시간대별 노선 이용량을 보여줘"
    try:
        result = JejuAgent(get_provider()).ask(q)
    except ValueError as exc:
        print(f"분석할 수 없습니다: {exc}", file=sys.stderr)
        sys.exit(2)
    print(JejuAgent.render_text(result))
