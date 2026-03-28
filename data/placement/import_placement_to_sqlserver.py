"""
Seed PlacementQuestions + PlacementOptions from JSON (see ../placement/placement_questions.json).

Uses same env vars as import_vocab_excel_to_sqlserver.py:
  VOCABIFY_SQL_CONNECTION_STRING or VOCABIFY_SQL_SERVER + VOCABIFY_SQL_DATABASE (+ optional USER/PASSWORD).

Default: skip if any active placement question already exists (avoids duplicates).
  --force: delete all PlacementOptions and PlacementQuestions first (only allowed when
           PlacementAttempts has no rows, to protect FK from PlacementAttemptAnswers).

Examples:
  python import_placement_to_sqlserver.py --dry-run
  python import_placement_to_sqlserver.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pyodbc

DEFAULT_JSON = Path(__file__).resolve().parent.parent / "placement" / "placement_questions.json"


def build_connection_string() -> str:
    full = os.environ.get("VOCABIFY_SQL_CONNECTION_STRING", "").strip()
    if full:
        return full
    server = os.environ.get("VOCABIFY_SQL_SERVER", "PT").strip()
    database = os.environ.get("VOCABIFY_SQL_DATABASE", "Vocabify").strip()
    user = os.environ.get("VOCABIFY_SQL_USER", "").strip()
    password = os.environ.get("VOCABIFY_SQL_PASSWORD", "").strip()
    if user:
        return (
            "Driver={ODBC Driver 17 for SQL Server};"
            f"Server={server};Database={database};Uid={user};Pwd={password};"
            "TrustServerCertificate=yes;"
        )
    return (
        "Driver={ODBC Driver 17 for SQL Server};"
        f"Server={server};Database={database};Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def trunc(s: str | None, max_len: int) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    return t if len(t) <= max_len else t[:max_len]


def resolve_level_id(cur, level_code: str) -> int:
    cur.execute(
        """
        SELECT TOP 1 Id FROM dbo.Levels
        WHERE LOWER(LTRIM(RTRIM(Code))) = LOWER(LTRIM(RTRIM(?)))
           OR LOWER(LTRIM(RTRIM(Name))) = LOWER(LTRIM(RTRIM(?)))
        ORDER BY Id
        """,
        (level_code, level_code),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    raise RuntimeError(f"Level not found for code/name {level_code!r}")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_level_block(level_code: str, questions: list) -> None:
    if not questions:
        raise ValueError(f"No questions for level {level_code}")
    for i, q in enumerate(questions):
        opts = q.get("options") or []
        if len(opts) < 2:
            raise ValueError(f"{level_code} Q{i}: need at least 2 options")
        correct = [o for o in opts if o.get("correct")]
        if len(correct) != 1:
            raise ValueError(f"{level_code} Q{i}: exactly one option must have correct=true")


def placement_attempt_count(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM dbo.PlacementAttempts WHERE IsDeleted = 0")
    return int(cur.fetchone()[0])


def active_question_count(cur) -> int:
    cur.execute(
        "SELECT COUNT(*) FROM dbo.PlacementQuestions WHERE IsDeleted = 0 AND IsActive = 1"
    )
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed placement questions into SQL Server")
    parser.add_argument(
        "--json",
        type=Path,
        default=DEFAULT_JSON,
        help="Path to placement_questions.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear PlacementQuestions/Options and re-seed (blocked if PlacementAttempts exist)",
    )
    args = parser.parse_args()

    path = args.json
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    data = load_json(path)
    levels = data.get("levels") or []
    if not levels:
        print("JSON has no 'levels' array.", file=sys.stderr)
        return 1

    total_q = 0
    total_o = 0
    for block in levels:
        code = (block.get("level_code") or "").strip()
        qs = block.get("questions") or []
        validate_level_block(code, qs)
        total_q += len(qs)
        for q in qs:
            total_o += len(q.get("options") or [])

    print(f"JSON: {path}")
    print(f"Levels: {len(levels)} | Questions: {total_q} | Options: {total_o}")

    if args.dry_run:
        return 0

    conn_str = build_connection_string()
    try:
        conn = pyodbc.connect(conn_str, autocommit=False)
    except pyodbc.Error as e:
        print(f"DB connection failed: {e}", file=sys.stderr)
        return 1

    cur = conn.cursor()
    try:
        if active_question_count(cur) > 0 and not args.force:
            print(
                "Placement content already exists. Use --force to replace (only if no placement attempts).",
                file=sys.stderr,
            )
            return 1

        if args.force:
            n_attempts = placement_attempt_count(cur)
            if n_attempts > 0:
                print(
                    f"Refusing --force: {n_attempts} row(s) in PlacementAttempts (would break FK).",
                    file=sys.stderr,
                )
                return 1
            cur.execute("DELETE FROM dbo.PlacementOptions")
            cur.execute("DELETE FROM dbo.PlacementQuestions")

        for block in levels:
            code = (block.get("level_code") or "").strip()
            level_id = resolve_level_id(cur, code)
            for q in block.get("questions") or []:
                qtext = trunc(q.get("question_text"), 1000)
                expl = q.get("explanation")
                expl_s = trunc(expl, 1000) if expl else None
                if not qtext:
                    raise ValueError("Empty question_text")
                cur.execute(
                    """
                    INSERT INTO dbo.PlacementQuestions (
                        LevelId, QuestionText, Explanation, IsActive, IsDeleted
                    )
                    OUTPUT INSERTED.Id
                    VALUES (?, ?, ?, 1, 0)
                    """,
                    (level_id, qtext, expl_s if expl_s else None),
                )
                qid = int(cur.fetchone()[0])
                for sort_order, opt in enumerate(q.get("options") or [], start=1):
                    otext = trunc(opt.get("text"), 500)
                    if not otext:
                        raise ValueError(f"Empty option text for question id {qid}")
                    is_correct = 1 if opt.get("correct") else 0
                    score = int(opt.get("score", 0))
                    cur.execute(
                        """
                        INSERT INTO dbo.PlacementOptions (
                            QuestionId, OptionText, IsCorrect, Score, IsDeleted
                        )
                        VALUES (?, ?, ?, ?, 0)
                        """,
                        (qid, otext, is_correct, score),
                    )

        conn.commit()
        print("Done. PlacementQuestions + PlacementOptions inserted.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
