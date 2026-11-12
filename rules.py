"""AI 없이 코드로 처리하는 업무 규칙. 기준은 data/업무설명_하자보수.md."""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
대장파일 = BASE / "data" / "하자대장.csv"
공사정보파일 = BASE / "data" / "공사정보.csv"

# 업무설명 2번의 열 순서
COLUMNS = [
    "접수번호", "접수일", "원문파일", "위치", "공종", "하자내용", "긴급도", "조치기한",
    "공사번호", "시공업체", "준공일", "보증만료일", "보증판정", "책임구분", "상태", "비고",
]

# 업무설명 4번
조치일수 = {"긴급": 1, "높음": 3, "보통": 7}
만료임박일수 = 30


# ---------- 하자대장 읽기·저장 ----------
def load_ledger() -> pd.DataFrame:
    if not 대장파일.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(대장파일, encoding="utf-8-sig", dtype=str).fillna("")
    return df[COLUMNS]


def save_ledger(df: pd.DataFrame) -> None:
    df[COLUMNS].to_csv(대장파일, index=False, encoding="utf-8-sig")


# ---------- 접수번호 ----------
def make_receipt_no(접수일: str, ledger: pd.DataFrame) -> str:
    """HJ-YYYYMMDD-NN. 같은 접수일의 기존 건 다음 순번 (01부터)."""
    ymd = 접수일.replace("-", "")
    prefix = f"HJ-{ymd}-"
    nums = [int(n[len(prefix):]) for n in ledger["접수번호"] if str(n).startswith(prefix)]
    return f"{prefix}{(max(nums) if nums else 0) + 1:02d}"


# ---------- 조치기한 ----------
def due_date(접수일: str, 긴급도: str) -> str:
    if 긴급도 not in 조치일수:
        return ""
    return (date.fromisoformat(접수일) + timedelta(days=조치일수[긴급도])).isoformat()


# ---------- 보증 판정 ----------
def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 2월 29일 → 2월 28일
        return d.replace(year=d.year + years, day=28)


def load_projects() -> pd.DataFrame:
    df = pd.read_csv(공사정보파일, encoding="utf-8-sig", dtype=str).fillna("")
    df["보증만료일"] = [
        _add_years(date.fromisoformat(d), int(y)).isoformat()
        for d, y in zip(df["준공일"], df["하자보증기간(년)"])
    ]
    return df


def _remaining(접수일: str, 만료일: str) -> int:
    return (date.fromisoformat(만료일) - date.fromisoformat(접수일)).days


def judge_warranty(접수일: str, 위치: str, 공종: str) -> dict:
    """공사정보에서 위치·공종이 같은 공사를 찾아 보증 판정. 접수일 기준."""
    pj = load_projects()
    result = {"공사번호": "", "시공업체": "", "준공일": "", "보증만료일": "",
              "보증판정": "확인필요", "책임구분": "", "비고": []}

    후보공종 = [g.strip() for g in 공종.split("/") if g.strip()]
    same_loc = pj[pj["위치"] == 위치]
    candidates = same_loc[same_loc["공종"].isin(후보공종)]

    if len(후보공종) != 1:
        result["비고"].append(f"공종 미정({공종})")
    elif len(candidates) == 0:
        result["비고"].append("맞는 공사 없음")
    elif len(candidates) > 1:
        result["비고"].append("맞는 공사 2건 이상")
    else:
        p = candidates.iloc[0]
        남은일 = _remaining(접수일, p["보증만료일"])
        result.update({"공사번호": p["공사번호"], "시공업체": p["시공업체"],
                       "준공일": p["준공일"], "보증만료일": p["보증만료일"]})
        if 남은일 >= 0:  # 만료일 당일 포함
            result.update({"보증판정": "보증내", "책임구분": "시공업체"})
            if 남은일 <= 만료임박일수:
                result["비고"].append(f"만료임박({남은일}일 남음)")
        else:
            result.update({"보증판정": "보증만료", "책임구분": "자체보수"})
        return result

    # 확인필요: 후보 공사와 만료임박 여부를 비고에
    for _, p in candidates.iterrows():
        남은일 = _remaining(접수일, p["보증만료일"])
        txt = f"후보 {p['공사번호']} {p['시공업체']}(만료 {p['보증만료일']})"
        if 0 <= 남은일 <= 만료임박일수:
            txt += f" 만료임박({남은일}일 남음)"
        result["비고"].append(txt)
    return result


# ---------- 한 줄 만들기 ----------
def build_row(ai: dict, 원문파일: str, ledger: pd.DataFrame) -> dict:
    """AI가 뽑은 값(접수일·위치·공종·하자내용·긴급도·확인필요)에 규칙을 적용해 대장 한 줄을 만든다."""
    접수일 = ai["접수일"]
    판정 = judge_warranty(접수일, ai.get("위치", ""), ai.get("공종", ""))
    비고 = list(판정.pop("비고"))
    if ai.get("확인필요"):
        비고.insert(0, ai["확인필요"])
    상태 = "확인필요" if 판정["보증판정"] == "확인필요" or ai.get("확인필요") else "판정완료"
    return {
        "접수번호": make_receipt_no(접수일, ledger),
        "접수일": 접수일,
        "원문파일": 원문파일,
        "위치": ai.get("위치", ""),
        "공종": ai.get("공종", ""),
        "하자내용": ai.get("하자내용", "")[:40],
        "긴급도": ai.get("긴급도", ""),
        "조치기한": due_date(접수일, ai.get("긴급도", "")),
        **판정,
        "상태": 상태,
        "비고": " / ".join(비고),
    }
