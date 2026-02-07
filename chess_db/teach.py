from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    name: str
    moves_san: str

    @property
    def tokens(self) -> list[str]:
        return [t for t in self.moves_san.split() if t.strip()]


def longest_common_prefix(seqs: list[list[str]]) -> list[str]:
    if not seqs:
        return []
    prefix: list[str] = []
    for i in range(min(len(s) for s in seqs)):
        t = seqs[0][i]
        if all(s[i] == t for s in seqs[1:]):
            prefix.append(t)
        else:
            break
    return prefix


@dataclass(frozen=True)
class Branch:
    token: str
    count: int
    example_names: list[str]


def branch_by_token(lines: list[Line], idx: int) -> list[Branch]:
    buckets: dict[str, list[Line]] = {}
    for ln in lines:
        tok = ln.tokens[idx] if idx < len(ln.tokens) else "<END>"
        buckets.setdefault(tok, []).append(ln)

    branches: list[Branch] = []
    for tok, bucket in buckets.items():
        branches.append(
            Branch(
                token=tok,
                count=len(bucket),
                example_names=sorted([b.name for b in bucket])[:5],
            )
        )
    branches.sort(key=lambda b: (-b.count, b.token))
    return branches


def chunk_tokens(tokens: list[str], size: int) -> list[str]:
    out: list[str] = []
    for i in range(0, len(tokens), size):
        out.append(" ".join(tokens[i : i + size]))
    return out
