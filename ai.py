"""Claude API 호출은 이 파일에서만 한다. 키·모델은 .env에서 읽는다."""
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

PLACEHOLDER = "여기에_강사가_준_키를_붙여넣기"


def _client():
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip().strip('"').strip("'")
    if not key or key == PLACEHOLDER:
        raise SystemExit(
            "[안내] .env 파일에 ANTHROPIC_API_KEY가 없습니다.\n"
            "  .env를 메모장으로 열어 ANTHROPIC_API_KEY= 뒤에 강사가 준 키를 붙여넣고 저장하세요."
        )
    import anthropic

    return anthropic.Anthropic(api_key=key)


def _model():
    return (os.getenv("MODEL") or "claude-haiku-5-5").strip()


def _extract_json(text: str) -> dict:
    """답에서 JSON 부분만 꺼낸다 (코드블록이나 앞뒤 설명이 붙어도 처리)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"AI 답에서 JSON을 찾지 못했습니다: {text[:200]}")
    return json.loads(text[start : end + 1])


def ask_json(지침파일, 입력: str) -> dict:
    """지침을 시스템 프롬프트로, 입력을 사용자 메시지로 보내고 답의 JSON을 딕셔너리로 돌려준다."""
    system = Path(BASE / 지침파일).read_text(encoding="utf-8")
    try:
        msg = _client().messages.create(
            model=_model(),
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": 입력}],
        )
    except SystemExit:
        raise
    except Exception as e:  # 한글 안내
        name = type(e).__name__
        if "Authentication" in name:
            raise SystemExit("[안내] API 키가 맞지 않습니다. .env의 키 앞뒤 공백·따옴표를 확인하세요.")
        if "NotFound" in name:
            raise SystemExit(f"[안내] 모델을 찾지 못했습니다. .env의 MODEL 값(지금: {_model()})을 확인하세요.")
        if "Connection" in name:
            raise SystemExit("[안내] 인터넷 연결 또는 회사망 차단을 확인하세요.")
        raise
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)


if __name__ == "__main__":
    # 사용: python ai.py data/접수함/01_....txt
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1])
    입력 = f"파일명: {path.name}\n\n{path.read_text(encoding='utf-8')}"
    print(json.dumps(ask_json("지침/접수정리.md", 입력), ensure_ascii=False, indent=2))
