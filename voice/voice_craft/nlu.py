"""NLU — `(키워드, 명령)` 규칙 리스트, 동사 + 명사 부분일치 (ADR-018).

STT 가 준 소문자 영어 전사(예: `"produce an scv"`, `"build s c v"`, 잡음
`"the scframework"`)를 정규화한 뒤 규칙을 순서대로 스캔한다. 각 규칙은 동사
집합과 명사 집합을 갖고, 두 집합 모두에서 키워드가 하나라도 부분일치하면
명령을 발화한다(집합 내 any, 집합 간 AND). 무매칭이면 None — 봇에 잡음을
절대 보내지 않는다.

부분일치라 filler 단어("an", "please")를 견딘다. 동사 + 명사 동시 요구는
"cancel scv"·"move scv" 같은 오발화를 막는다(ADR-018 Rationale).
"""
from __future__ import annotations

import re

# (동사 집합, 명사 집합, 명령). 동사 AND 명사가 transcript 에 모두 있으면 발화.
# first-match-wins — 순서가 우선순위 (명령 1개라 지금은 무의미, ADR-018).
RULES: list[tuple[list[str], list[str], str]] = [
    (["produce", "make", "build", "train"], ["scv", "worker"], "produce_scv"),
]

# 점은 제거(empty) — "S.C.V." → "scv" 로 붙인다 (ADR-018). 나머지 비단어 문자는
# 공백으로 바꿔 단어가 서로 붙지 않게 한다("build,scv" → "build scv").
_DOT = re.compile(r"\.")
_SEP = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """소문자화 → 점 제거 → 나머지 구두점 공백화 → 공백 압축 (ADR-018)."""
    text = _DOT.sub("", text.lower())
    return _SEP.sub(" ", text).strip()


def match(transcript: str) -> str | None:
    """전사를 규칙에 매칭해 명령을 돌려준다. 무매칭이면 None (ADR-018).

    정규화 후 부분문자열 스캔 — "produce an scv" 도, 점으로 철자한 "S.C.V."
    (정규화 시 점 제거로 "scv")도 매칭한다.
    """
    norm = _normalize(transcript)
    for verbs, nouns, cmd in RULES:
        if any(v in norm for v in verbs) and any(n in norm for n in nouns):
            return cmd
    return None
