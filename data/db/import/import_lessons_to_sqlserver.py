"""
Generate Lessons + LessonItems + LessonExercises (+ MC options) for any level (default: all levels).

Rules (MVP):
  - Per topic: use vocabulary ordered by Id. Words 1-9 → three lessons (1-3, 4-6, 7-9). Word 10+ skipped for lessons.
  - Each lesson: 3 LessonItems, 15 LessonExercises — layout: 1-6 MC; 7-9 MC+audio; 10-11 PF follow (PromptJson: anchor + slot tokens order randomized); 12 MP (shuffled EN/VI columns); 13-15 SR: ex 1st/2nd/3rd per word by VocabExamples.Id; answer JSON tokens only.
  - ExerciseTypes.Code in DB: MC, SR, MP, PF (see VocabifySchema.sql).

Env (same as vocab import):
  VOCABIFY_SQL_CONNECTION_STRING or VOCABIFY_SQL_SERVER + VOCABIFY_SQL_DATABASE (+ optional USER/PASSWORD).

Examples:
  python import_lessons_to_sqlserver.py --dry-run
  python import_lessons_to_sqlserver.py
  python import_lessons_to_sqlserver.py --level-code M
  python import_lessons_to_sqlserver.py --topic-id 5
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

import pyodbc

WORDS_PER_LESSON = 3
LESSON_COUNT = 3
EXERCISE_COUNT = 15


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


def strip_trailing_period(s: str) -> str:
    t = (s or "").strip()
    if t.endswith("."):
        return t[:-1].rstrip()
    return t


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
    if not row:
        raise RuntimeError(f"Level not found: {level_code!r}")
    return int(row[0])


def load_exercise_type_ids(cur) -> dict[str, int]:
    cur.execute("SELECT Code, Id FROM dbo.ExerciseTypes WHERE IsDeleted = 0")
    m: dict[str, int] = {}
    for code, i in cur.fetchall():
        m[str(code)] = int(i)
    need = {"MC", "SR", "MP", "PF"}
    missing = need - set(m.keys())
    if missing:
        raise RuntimeError(f"ExerciseTypes missing codes: {missing}. Found: {list(m.keys())}")
    return m


def fetch_topic_by_id(cur, topic_id: int) -> dict | None:
    cur.execute(
        """
        SELECT t.Id, t.Name, t.LevelId, l.Code
        FROM dbo.Topics t
        INNER JOIN dbo.Levels l ON l.Id = t.LevelId
        WHERE t.Id = ? AND t.IsDeleted = 0 AND t.IsActive = 1
          AND l.IsDeleted = 0 AND l.IsActive = 1
        """,
        (topic_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "name": row[1] or "",
        "level_id": int(row[2]),
        "level_code": row[3] or "",
    }


def fetch_all_active_topics(cur) -> list[dict]:
    cur.execute(
        """
        SELECT t.Id, t.Name, t.LevelId, l.Code
        FROM dbo.Topics t
        INNER JOIN dbo.Levels l ON l.Id = t.LevelId
        WHERE t.IsDeleted = 0 AND t.IsActive = 1
          AND l.IsDeleted = 0 AND l.IsActive = 1
        ORDER BY l.SortOrder, l.Id, t.SortOrder, t.Id
        """
    )
    return [
        {
            "id": int(r[0]),
            "name": r[1] or "",
            "level_id": int(r[2]),
            "level_code": r[3] or "",
        }
        for r in cur.fetchall()
    ]


def fetch_topics_for_level_with_meta(cur, level_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT t.Id, t.Name, t.LevelId, l.Code
        FROM dbo.Topics t
        INNER JOIN dbo.Levels l ON l.Id = t.LevelId
        WHERE t.LevelId = ? AND t.IsDeleted = 0 AND t.IsActive = 1
        ORDER BY t.SortOrder, t.Id
        """,
        (level_id,),
    )
    return [
        {
            "id": int(r[0]),
            "name": r[1] or "",
            "level_id": int(r[2]),
            "level_code": r[3] or "",
        }
        for r in cur.fetchall()
    ]


def fetch_vocab_for_topic(cur, topic_id: int) -> list[dict]:
    cur.execute(
        """
        SELECT Id, Word, MeaningVi, DefinitionVi, AudioUrl
        FROM dbo.Vocabulary
        WHERE TopicId = ? AND IsDeleted = 0
        ORDER BY Id
        """,
        (topic_id,),
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "id": int(r[0]),
                "word": (r[1] or "").strip(),
                "meaning_vi": (r[2] or "").strip(),
                "def_vi": (r[3] or "").strip(),
                "audio_url": (r[4] or "").strip() or None,
            }
        )
    return rows


def fetch_example_nth(cur, vocabulary_id: int, ordinal: int) -> dict | None:
    """Nth VocabExamples row for a word by Id order (ordinal 1 = first, 2 = second, ...)."""
    if ordinal < 1:
        return None
    offset = ordinal - 1
    cur.execute(
        """
        SELECT Id, ExampleEn, ExampleVi
        FROM dbo.VocabExamples
        WHERE VocabularyId = ? AND IsDeleted = 0
        ORDER BY Id
        OFFSET ? ROWS FETCH NEXT 1 ROWS ONLY
        """,
        (vocabulary_id, offset),
    )
    row = cur.fetchone()
    if not row:
        return None
    eid = int(row[0])
    en = (row[1] or "").strip()
    vi = (row[2] or "").strip()
    if not en:
        return None
    return {"id": eid, "en": en, "vi": vi}


def tokenize_words(s: str) -> list[str]:
    if not (s or "").strip():
        return []
    return [x for x in re.split(r"\s+", s.strip()) if x]


def meaning_display(w: dict) -> str:
    if w["meaning_vi"]:
        return trunc(w["meaning_vi"], 100)
    if w["def_vi"]:
        return trunc(w["def_vi"], 120)
    return w["word"]


def topic_distractor_pool(topic_vocab: list[dict], chunk: list[dict]) -> list[dict]:
    chunk_ids = {x["id"] for x in chunk}
    return [w for w in topic_vocab if w["id"] not in chunk_ids]


def pick_mc_options_en_to_vi(
    correct: dict, chunk: list[dict], topic_vocab: list[dict]
) -> list[tuple[str, bool]]:
    correct_text = meaning_display(correct)
    wrong_src: list[dict] = [w for w in chunk if w["id"] != correct["id"]]
    wrong_src.extend(topic_distractor_pool(topic_vocab, chunk))
    random.shuffle(wrong_src)
    wrong_texts: list[str] = []
    for w in wrong_src:
        t = meaning_display(w)
        if t and t != correct_text and t not in wrong_texts:
            wrong_texts.append(t)
        if len(wrong_texts) >= 3:
            break
    while len(wrong_texts) < 3:
        wrong_texts.append(f"(distractor {len(wrong_texts)})")
    opts = [(correct_text, True)] + [(w, False) for w in wrong_texts[:3]]
    random.shuffle(opts)
    return opts


def pick_mc_options_vi_to_en(
    correct: dict, chunk: list[dict], topic_vocab: list[dict]
) -> list[tuple[str, bool]]:
    prompt = meaning_display(correct)
    correct_word = correct["word"]
    wrong_src = [w for w in chunk if w["id"] != correct["id"]]
    wrong_src.extend(topic_distractor_pool(topic_vocab, chunk))
    random.shuffle(wrong_src)
    wrong_words: list[str] = []
    for w in wrong_src:
        ww = w["word"]
        if ww and ww != correct_word and ww not in wrong_words:
            wrong_words.append(ww)
        if len(wrong_words) >= 3:
            break
    while len(wrong_words) < 3:
        wrong_words.append(f"word{len(wrong_words)}")
    opts = [(correct_word, True)] + [(w, False) for w in wrong_words[:3]]
    random.shuffle(opts)
    return opts, prompt


def pick_mc_options_listen_english(
    correct: dict, chunk: list[dict], topic_vocab: list[dict]
) -> list[tuple[str, bool]]:
    """MC: hear audio, pick the English word (four English options)."""
    correct_word = correct["word"]
    wrong_src = [w for w in chunk if w["id"] != correct["id"]]
    wrong_src.extend(topic_distractor_pool(topic_vocab, chunk))
    random.shuffle(wrong_src)
    wrong_words: list[str] = []
    for w in wrong_src:
        ww = w["word"]
        if ww and ww != correct_word and ww not in wrong_words:
            wrong_words.append(ww)
        if len(wrong_words) >= 3:
            break
    while len(wrong_words) < 3:
        wrong_words.append(f"word{len(wrong_words)}")
    opts = [(correct_word, True)] + [(w, False) for w in wrong_words[:3]]
    random.shuffle(opts)
    return opts


def insert_lesson(
    cur,
    topic_id: int,
    topic_name: str,
    part_index: int,
    chunk: list[dict],
    topic_vocab: list[dict],
    type_ids: dict[str, int],
) -> tuple[int, int]:
    title = trunc(f"{topic_name} — Part {part_index}", 200)
    desc = trunc(
        f"Words: {chunk[0]['word']}, {chunk[1]['word']}, {chunk[2]['word']}", 1000
    )
    cur.execute(
        """
        SELECT COALESCE(MAX(SortOrder), 0) + 1 FROM dbo.Lessons
        WHERE TopicId = ? AND IsDeleted = 0
        """,
        (topic_id,),
    )
    lo = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO dbo.Lessons (TopicId, Title, Description, SortOrder, PassScore, IsActive, IsDeleted)
        OUTPUT INSERTED.Id
        VALUES (?, ?, ?, ?, 80, 1, 0)
        """,
        (topic_id, title, desc, lo),
    )
    lesson_id = int(cur.fetchone()[0])

    for i, w in enumerate(chunk, start=1):
        cur.execute(
            """
            INSERT INTO dbo.LessonItems (LessonId, VocabularyId, SortOrder, IsDeleted)
            VALUES (?, ?, ?, 0)
            """,
            (lesson_id, w["id"], i),
        )

    def insert_exercise(
        sort_order: int,
        code: str,
        vocab_anchor: dict,
        example_id: int | None,
        prompt_lang: str | None,
        answer_lang: str | None,
        prompt_text: str | None,
        prompt_json: dict | None,
        correct_json: dict | None,
        correct_text: str | None,
        mc_options: list[tuple[str, bool]] | None,
        audio_url: str | None = None,
    ) -> None:
        pid = json.dumps(prompt_json, ensure_ascii=False) if prompt_json else None
        cid = json.dumps(correct_json, ensure_ascii=False) if correct_json else None
        ptxt = trunc(prompt_text, 1000) if prompt_text else None
        ctxt = trunc(correct_text, 1000) if correct_text else None
        au = trunc(audio_url, 500) if audio_url else None
        cur.execute(
            """
            INSERT INTO dbo.LessonExercises (
                LessonId, VocabularyId, ExampleId, ExerciseTypeId,
                PromptLanguage, AnswerLanguage, PromptText, PromptJson, AudioUrl,
                CorrectAnswerText, CorrectAnswerJson, SortOrder, Points, IsDeleted
            )
            OUTPUT INSERTED.Id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                lesson_id,
                vocab_anchor["id"],
                example_id,
                type_ids[code],
                prompt_lang,
                answer_lang,
                ptxt,
                pid,
                au,
                ctxt,
                cid,
                sort_order,
            ),
        )
        eid = int(cur.fetchone()[0])
        if mc_options:
            for oi, (otext, is_ok) in enumerate(mc_options, start=1):
                cur.execute(
                    """
                    INSERT INTO dbo.LessonExerciseOptions
                        (ExerciseId, OptionText, IsCorrect, SortOrder, IsDeleted)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (eid, trunc(otext, 500), 1 if is_ok else 0, oi),
                )

    w0, w1, w2 = chunk[0], chunk[1], chunk[2]

    # 1-6 MC alternating En→Vi / Vi→En (AudioUrl + CorrectAnswerText)
    plan_mc = [
        (1, "en_vi", w0),
        (2, "vi_en", w1),
        (3, "en_vi", w2),
        (4, "vi_en", w0),
        (5, "en_vi", w1),
        (6, "vi_en", w2),
    ]
    for sort, mode, w in plan_mc:
        au = w.get("audio_url")
        if mode == "en_vi":
            opts = pick_mc_options_en_to_vi(w, chunk, topic_vocab)
            insert_exercise(
                sort,
                "MC",
                w,
                None,
                "En",
                "Vi",
                w["word"],
                None,
                None,
                meaning_display(w),
                opts,
                au,
            )
        else:
            opts, prompt_vi = pick_mc_options_vi_to_en(w, chunk, topic_vocab)
            insert_exercise(
                sort,
                "MC",
                w,
                None,
                "Vi",
                "En",
                prompt_vi,
                None,
                None,
                w["word"],
                opts,
                au,
            )

    # 7-9 MC: audio — choose the English word you hear
    listen_prompt = "Listen and choose the word."
    for sort, w in ((7, w0), (8, w1), (9, w2)):
        opts_listen = pick_mc_options_listen_english(w, chunk, topic_vocab)
        insert_exercise(
            sort,
            "MC",
            w,
            None,
            "En",
            "En",
            listen_prompt,
            None,
            None,
            w["word"],
            opts_listen,
            w.get("audio_url"),
        )

    def insert_follow_pf(
        sort_order: int,
        vocab_anchor: dict,
        pattern_example: str,
        target_sentence: str,
        anchor_word: str,
        slot_tokens: list[str],
    ) -> None:
        pr_pf = f"Follow the pattern: {pattern_example},"
        shuf_slots = slot_tokens[:]
        random.shuffle(shuf_slots)
        pj_pf = {"anchor": anchor_word, "tokens": shuf_slots}
        cj_pf = {
            "sentence": target_sentence,
            "tokens": tokenize_words(target_sentence),
        }
        insert_exercise(
            sort_order,
            "PF",
            vocab_anchor,
            None,
            None,
            None,
            trunc(pr_pf, 1000),
            pj_pf,
            cj_pf,
            trunc(target_sentence, 1000),
            None,
            None,
        )

    # 10: pattern (w1, w2) → target (w0 with w1)
    pat10 = f"{w1['word']} with {w2['word']}"
    tgt10 = f"{w0['word']} with {w1['word']}"
    insert_follow_pf(10, w0, pat10, tgt10, w0["word"], ["with", w1["word"]])

    # 11: pattern (w0, w1) → target (w1 with w2)
    pat11 = f"{w0['word']} with {w1['word']}"
    tgt11 = f"{w1['word']} with {w2['word']}"
    insert_follow_pf(11, w1, pat11, tgt11, w1["word"], ["with", w2["word"]])

    # 12 MP: PromptJson = token lists; CorrectAnswerJson = pairs only
    pairs_mp = [
        {"en": w0["word"], "vi": meaning_display(w0)},
        {"en": w1["word"], "vi": meaning_display(w1)},
        {"en": w2["word"], "vi": meaning_display(w2)},
    ]
    pr_mp = "Match each English word to its Vietnamese meaning."
    token_en = [w0["word"], w1["word"], w2["word"]]
    token_vi = [meaning_display(w0), meaning_display(w1), meaning_display(w2)]
    en_shuf = token_en[:]
    vi_shuf = token_vi[:]
    random.shuffle(en_shuf)
    random.shuffle(vi_shuf)
    insert_exercise(
        12,
        "MP",
        w0,
        None,
        None,
        None,
        trunc(pr_mp, 1000),
        {"token_en": en_shuf, "token_vi": vi_shuf},
        {"pairs": pairs_mp},
        None,
        None,
        None,
    )

    # 13-15: VocabExamples row 1 / 2 / 3 by Id (per word w0, w1, w2); prompt = full line; bank shuffled;
    # CorrectAnswerJson: tokens only (no sentence).
    def insert_example_sr(
        sort_order: int,
        w: dict,
        mode: str,
        example_ordinal: int,
    ) -> None:
        ex = fetch_example_nth(cur, w["id"], example_ordinal)
        if not ex:
            insert_exercise(
                sort_order,
                "SR",
                w,
                None,
                "En" if mode == "en_vi" else "Vi",
                "Vi" if mode == "en_vi" else "En",
                f"Not enough VocabExamples for this word (need example #{example_ordinal}).",
                None,
                None,
                None,
                None,
                w.get("audio_url"),
            )
            return
        eid = ex["id"]
        en_raw = strip_trailing_period((ex["en"] or "").strip())
        vi_raw = strip_trailing_period((ex["vi"] or "").strip())
        if mode == "en_vi":
            if not en_raw:
                insert_exercise(
                    sort_order,
                    "SR",
                    w,
                    None,
                    "En",
                    "Vi",
                    f"Not enough VocabExamples for this word (need example #{example_ordinal}).",
                    None,
                    None,
                    None,
                    None,
                    w.get("audio_url"),
                )
                return
            ans_ex = vi_raw or meaning_display(w)
            vi_toks = tokenize_words(ans_ex)
            bank_vi = vi_toks[:]
            random.shuffle(bank_vi)
            pj_ex = {"bank": bank_vi}
            cj_ex = {"tokens": vi_toks}
            insert_exercise(
                sort_order,
                "SR",
                w,
                eid,
                "En",
                "Vi",
                trunc(en_raw, 1000),
                pj_ex,
                cj_ex,
                trunc(ans_ex, 1000),
                None,
                w.get("audio_url"),
            )
        else:
            vi_line = vi_raw if vi_raw else meaning_display(w)
            ans_ex = en_raw or w["word"]
            en_toks = tokenize_words(ans_ex)
            bank_en = en_toks[:]
            random.shuffle(bank_en)
            pj_ex = {"bank": bank_en}
            cj_ex = {"tokens": en_toks}
            insert_exercise(
                sort_order,
                "SR",
                w,
                eid,
                "Vi",
                "En",
                trunc(vi_line, 1000),
                pj_ex,
                cj_ex,
                trunc(ans_ex, 1000),
                None,
                w.get("audio_url"),
            )

    insert_example_sr(13, w0, "en_vi", 1)
    insert_example_sr(14, w1, "vi_en", 2)
    insert_example_sr(15, w2, "en_vi", 3)

    return lesson_id, EXERCISE_COUNT


def count_lessons_for_topic(cur, topic_id: int) -> int:
    cur.execute(
        "SELECT COUNT(*) FROM dbo.Lessons WHERE TopicId = ? AND IsDeleted = 0",
        (topic_id,),
    )
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import lessons for one level, all levels, or a single topic (SQL Server)"
    )
    parser.add_argument(
        "--level-code",
        default=None,
        help="Levels.Code (e.g. E, M). Omit to import every active topic on every active level.",
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        default=None,
        help="Only this Topic Id (optional; ignores --level-code when set)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only; no DB writes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Insert even if topic already has lessons (may duplicate SortOrder / titles)",
    )
    args = parser.parse_args()

    conn_str = build_connection_string()
    try:
        conn = pyodbc.connect(conn_str, autocommit=False)
    except pyodbc.Error as e:
        print(f"DB connection failed: {e}", file=sys.stderr)
        return 1

    cur = conn.cursor()
    try:
        type_ids = load_exercise_type_ids(cur)
        if args.topic_id is not None:
            one = fetch_topic_by_id(cur, args.topic_id)
            topics = [one] if one else []
        elif args.level_code:
            level_id = resolve_level_id(cur, args.level_code)
            topics = fetch_topics_for_level_with_meta(cur, level_id)
        else:
            topics = fetch_all_active_topics(cur)
        if not topics:
            print("No topics found for this filter.", file=sys.stderr)
            return 1

        total_lessons = 0
        for t in topics:
            tid = t["id"]
            tname = t["name"]
            lc = t.get("level_code", "")
            vocab = fetch_vocab_for_topic(cur, tid)
            if len(vocab) < 9:
                print(
                    f"Skip topic {tid} ({tname!r}) level {lc!r}: need at least 9 words, has {len(vocab)}"
                )
                continue
            if not args.force and count_lessons_for_topic(cur, tid) > 0:
                print(
                    f"Skip topic {tid} ({tname!r}) level {lc!r}: already has lessons (use --force to add anyway)"
                )
                continue

            chunks = [
                vocab[0:3],
                vocab[3:6],
                vocab[6:9],
            ]
            if args.dry_run:
                print(
                    f"[dry-run] topic {tid} {tname!r} level {lc!r}: 3 lessons x 3 words; word[9+] ignored "
                    f"(total words in topic: {len(vocab)})"
                )
                total_lessons += 3
                continue

            random.seed(42 + tid)
            for part, chunk in enumerate(chunks, start=1):
                lid, n_ex = insert_lesson(
                    cur, tid, tname, part, chunk, vocab, type_ids
                )
                total_lessons += 1
                print(
                    f"Topic {tid} part {part} level {lc!r}: LessonId={lid} exercises={n_ex}"
                )

        if args.dry_run:
            print(f"[dry-run] Would create ~{total_lessons} lessons.")
            return 0

        conn.commit()
        print(f"Done. Lessons created: {total_lessons}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
