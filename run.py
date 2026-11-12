"""입력 모으기 → AI 정리 → 규칙 판정 → 하자대장 저장. 실행 순서만 맡는다."""
import re
import sys
from pathlib import Path

import pandas as pd

import ai
import rules

BASE = Path(__file__).resolve().parent
접수함 = BASE / "data" / "접수함"
지침 = "지침/접수정리.md"


def date_from_filename(name: str) -> str:
    m = re.search(r"(\d{4})(\d{2})(\d{2})", name)
    return f"{m[1]}-{m[2]}-{m[3]}" if m else ""


def process_folder(ledger: pd.DataFrame) -> pd.DataFrame:
    done = set(ledger["원문파일"])
    for path in sorted(접수함.glob("*.txt")):
        if path.name in done:
            continue
        원문 = path.read_text(encoding="utf-8")
        print(f"  정리 중: {path.name}")
        result = ai.ask_json(지침, f"파일명: {path.name}\n\n{원문}")
        if not result.get("접수일"):
            result["접수일"] = date_from_filename(path.name)
        row = rules.build_row(result, path.name, ledger)
        ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    return ledger


def main():
    ledger = rules.load_ledger()
    before = len(ledger)
    ledger = process_folder(ledger)
    rules.save_ledger(ledger)

    new = ledger.iloc[before:]
    print(f"\n새로 등록 {len(new)}건 / 대장 전체 {len(ledger)}건")
    if len(new):
        with pd.option_context("display.max_columns", None, "display.width", 250):
            print(new[["접수번호", "위치", "공종", "긴급도", "조치기한", "공사번호",
                       "보증만료일", "보증판정", "책임구분", "상태", "비고"]].to_string(index=False))
    print("\n보증판정:", ledger["보증판정"].value_counts().to_dict())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
