import json
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None


OUTPUT_EXCEL = Path("vocab_upper_intermediate_10topics_10words.xlsx")
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LEVEL = "upper-intermediate"
WORDS_PER_TOPIC = 10

TOPICS_IN_ORDER = [
    "economy",
    "politics",
    "law",
    "psychology",
    "science",
    "technology advanced",
    "global issues",
    "ethics",
    "philosophy",
    "career & work (advanced)",
]

# Larger pools to replace words that miss required API fields.
TOPIC_WORD_POOLS = {
    "economy": [
        "inflation", "recession", "growth", "productivity", "investment", "unemployment", "wages", "interest",
        "budget", "deficit", "surplus", "taxation", "subsidy", "commodity", "trade", "import", "export",
        "currency", "exchange", "consumer", "demand", "supply", "market", "profit", "revenue", "asset",
        "liability", "industry", "finance", "economy",
    ],
    "politics": [
        "election", "campaign", "candidate", "vote", "ballot", "parliament", "senate", "government",
        "policy", "reform", "democracy", "republic", "constitution", "minister", "cabinet", "opposition",
        "coalition", "ideology", "debate", "protest", "diplomacy", "treaty", "sanction", "legislation",
        "governance", "corruption", "lobby", "mandate", "regulation", "authority",
    ],
    "law": [
        "legal", "lawsuit", "plaintiff", "defendant", "evidence", "verdict", "appeal", "jury", "witness",
        "trial", "court", "judge", "attorney", "contract", "liability", "fraud", "theft", "sentence",
        "punishment", "rights", "justice", "criminal", "civil", "lawful", "regulation", "compliance",
        "dispute", "settlement", "case", "statute",
    ],
    "psychology": [
        "behavior", "cognition", "perception", "emotion", "motivation", "personality", "stress", "anxiety",
        "depression", "therapy", "counseling", "trauma", "memory", "attention", "habit", "addiction",
        "resilience", "empathy", "self-esteem", "mindset", "bias", "attachment", "conflict", "identity",
        "well-being", "disorder", "symptom", "diagnosis", "treatment", "psychology",
    ],
    "science": [
        "hypothesis", "experiment", "data", "analysis", "evidence", "method", "variable", "theory",
        "observation", "measurement", "accuracy", "precision", "sample", "laboratory", "research",
        "scientist", "biology", "chemistry", "physics", "genetics", "molecule", "atom", "enzyme",
        "radiation", "gravity", "evolution", "discovery", "innovation", "scientific", "peer",
    ],
    "technology advanced": [
        "artificial", "intelligence", "machine", "learning", "neural", "algorithm", "encryption", "cybersecurity",
        "authentication", "authorization", "vulnerability", "exploit", "malware", "ransomware", "firewall",
        "cloud", "infrastructure", "microservice", "container", "virtualization", "distributed", "scalable",
        "latency", "bandwidth", "protocol", "blockchain", "automation", "analytics", "database", "server",
    ],
    "global issues": [
        "poverty", "inequality", "migration", "refugee", "pandemic", "conflict", "warfare", "terrorism",
        "sanction", "humanitarian", "crisis", "famine", "drought", "climate", "pollution", "deforestation",
        "biodiversity", "sustainability", "globalization", "diplomacy", "security", "stability",
        "violence", "displacement", "epidemic", "outbreak", "water", "shortage", "peace", "justice",
    ],
    "ethics": [
        "morality", "integrity", "honesty", "fairness", "justice", "responsibility", "accountability",
        "consent", "privacy", "harm", "benefit", "duty", "virtue", "rights", "freedom", "respect",
        "bias", "discrimination", "corruption", "transparency", "conflict", "principle",
        "ethical", "unethical", "values", "norms", "empathy", "trust", "misconduct", "ethics",
    ],
    "philosophy": [
        "reason", "logic", "truth", "belief", "knowledge", "mind", "consciousness", "existence",
        "identity", "meaning", "purpose", "virtue", "justice", "freedom", "ethics", "morality",
        "metaphysics", "epistemology", "aesthetics", "argument", "premise", "conclusion",
        "skepticism", "paradox", "theory", "principle", "philosophy", "reflect", "doubt", "wisdom",
    ],
    "career & work (advanced)": [
        "promotion", "performance", "responsibility", "leadership", "management", "strategy", "stakeholder",
        "negotiation", "deliverable", "deadline", "initiative", "ownership", "collaboration", "conflict",
        "feedback", "evaluation", "productivity", "efficiency", "professional", "competency",
        "expertise", "specialist", "consultant", "executive", "supervisor", "workload",
        "workplace", "compliance", "reputation", "career",
    ],
}


def translate_en_to_vi(text: str) -> str:
    if not text:
        return ""
    if GoogleTranslator is None:
        return ""
    try:
        return GoogleTranslator(source="en", target="vi").translate(text)
    except Exception:
        return ""


def meaning_vi_from_word(word: str) -> str:
    return translate_en_to_vi(word).strip()


def fetch_required_dictionary_fields(word: str) -> dict:
    if not word or " " in word.strip():
        return {}
    try:
        encoded = quote(word.strip())
        res = requests.get(DICTIONARY_API.format(encoded), timeout=20)
        payload = res.json()
    except Exception:
        return {}

    if not isinstance(payload, list) or not payload:
        return {}

    entry = payload[0]

    phonetic = (entry.get("phonetic") or "").strip()
    audio = ""
    phonetics = entry.get("phonetics", []) or []

    for p in phonetics:
        if p.get("text") and not phonetic:
            phonetic = (p.get("text") or "").strip()
    for p in phonetics:
        if p.get("audio"):
            audio = (p.get("audio") or "").strip()
            if not phonetic and p.get("text"):
                phonetic = (p.get("text") or "").strip()
            break

    meanings = entry.get("meanings", []) or []
    part_of_speech = ""
    definition_en = ""
    if meanings:
        part_of_speech = (meanings[0].get("partOfSpeech") or "").strip()
        defs = meanings[0].get("definitions", []) or []
        if defs:
            definition_en = (defs[0].get("definition") or "").strip()

    if not (word and phonetic and audio and part_of_speech and definition_en):
        return {}

    return {
        "word": word,
        "phonetic": phonetic,
        "audio": audio,
        "part_of_speech": part_of_speech,
        "definition_en": definition_en,
    }


def build_inflection(word: str, part_of_speech: str) -> dict:
    pos = (part_of_speech or "").lower()
    if pos == "noun":
        plural = word + "s" if not word.endswith("s") else word
        return {"noun": {"singular": word, "plural": plural}}
    if pos == "verb":
        third = word + "s" if not word.endswith("s") else word
        past = word + "ed" if not word.endswith("e") else word + "d"
        ing = word + "ing" if not word.endswith("e") else word[:-1] + "ing"
        return {
            "verb": {
                "base": word,
                "third_person_singular": third,
                "past_simple": past,
                "present_participle": ing,
            }
        }
    if pos == "adjective":
        return {"adjective": {"base": word}}
    return {pos or "other": {"base": word}}


def build_word_family(word: str) -> dict:
    base_meaning = meaning_vi_from_word(word)
    return {"base": {"word": word, "meaning_vi": base_meaning}}


def build_distractors(word: str, pool: list, k: int = 3) -> list:
    candidates = [w for w in pool if w != word and " " not in w.strip()]
    random.shuffle(candidates)
    return candidates[:k]


def build_examples(word: str, topic: str) -> list:
    if topic == "economy":
        sents = [
            f"{word.capitalize()} affects how much people can buy with their income.",
            f"The central bank raised rates to control {word}.",
            f"In a downturn, {word} can rise quickly in some industries.",
        ]
    elif topic == "politics":
        sents = [
            f"The candidate focused on {word} during the campaign.",
            f"The new {word} was introduced after months of debate.",
            f"Citizens demanded more {word} from public officials.",
        ]
    elif topic == "law":
        sents = [
            f"The judge reviewed the {word} before making a decision.",
            f"The lawyer filed an {word} to challenge the verdict.",
            f"They reached a {word} to avoid a long trial.",
        ]
    elif topic == "psychology":
        sents = [
            f"Chronic {word} can affect both sleep and concentration.",
            f"Therapy helped him manage his {word} over time.",
            f"Her {word} changed after a major life event.",
        ]
    elif topic == "science":
        sents = [
            f"The team tested their {word} with a controlled experiment.",
            f"Good {word} requires careful measurement and records.",
            f"Researchers published the {word} in a peer-reviewed journal.",
        ]
    elif topic == "technology advanced":
        sents = [
            f"The system uses {word} to protect sensitive data.",
            f"A single {word} can expose the entire network to attack.",
            f"They optimized the service to reduce {word} in real-time requests.",
        ]
    elif topic == "global issues":
        sents = [
            f"Many families were affected by the {word} and needed support.",
            f"International organizations responded to the {word} with aid.",
            f"Long-term {word} requires cooperation between countries.",
        ]
    elif topic == "ethics":
        sents = [
            f"Leaders should be judged by their {word}, not just their results.",
            f"Privacy is a major {word} issue in modern technology.",
            f"Fairness and {word} are important in the workplace.",
        ]
    elif topic == "philosophy":
        sents = [
            f"The debate raised questions about {word} and what we can truly know.",
            f"Some philosophers argue that {word} is shaped by language and culture.",
            f"He offered a clear {word} to support his conclusion.",
        ]
    elif topic == "career & work (advanced)":
        sents = [
            f"She took {word} for the project and delivered on time.",
            f"Strong {word} skills help teams work through conflict.",
            f"His {word} improved after he learned to prioritize tasks.",
        ]
    else:
        sents = [
            f"I learned the word '{word}' today.",
            f"Can you explain what '{word}' means?",
            f"Let's use '{word}' in a sentence.",
        ]

    examples = []
    for en in sents[:3]:
        vi = translate_en_to_vi(en).strip()
        if en.strip() and vi:
            examples.append({"en": en.strip(), "vi": vi})
    return examples


def complete_row(row: dict) -> bool:
    for k in ("word", "phonetic", "audio", "part_of_speech", "definition_en", "definition_vi", "meaning_vi"):
        v = row.get(k)
        if not isinstance(v, str) or not v.strip():
            return False
    if not isinstance(row.get("inflection"), dict) or not row["inflection"]:
        return False
    if not isinstance(row.get("word_family"), dict) or not row["word_family"]:
        return False
    examples = row.get("examples")
    if not isinstance(examples, list) or len(examples) != 3:
        return False
    distractors = row.get("distractors")
    if not isinstance(distractors, list) or len(distractors) != 3:
        return False
    for ex in examples:
        if not isinstance(ex, dict):
            return False
        if not ex.get("en") or not ex.get("vi"):
            return False
    return True


def try_build_row(word: str, topic: str, pool_for_distractors: list) -> dict:
    dic = fetch_required_dictionary_fields(word)
    if not dic:
        return {}

    definition_vi = translate_en_to_vi(dic["definition_en"]).strip()
    meaning_vi = meaning_vi_from_word(word)
    if not definition_vi or not meaning_vi:
        return {}

    inflection = build_inflection(word, dic["part_of_speech"])
    word_family = build_word_family(word)
    distractors = build_distractors(word, pool_for_distractors, k=3)
    if len(distractors) != 3:
        return {}

    examples = build_examples(word, topic)
    if len(examples) != 3:
        return {}

    row = {
        "word": dic["word"],
        "phonetic": dic["phonetic"],
        "audio": dic["audio"],
        "part_of_speech": dic["part_of_speech"],
        "definition_en": dic["definition_en"],
        "definition_vi": definition_vi,
        "meaning_vi": meaning_vi,
        "inflection": inflection,
        "word_family": word_family,
        "distractors": distractors,
        "examples": examples,
        "topic": topic,
        "level": LEVEL,
    }
    return row if complete_row(row) else {}


def main() -> None:
    rows = []
    skipped_topics = []

    for topic in TOPICS_IN_ORDER:
        pool = TOPIC_WORD_POOLS.get(topic, [])
        pool = [w.strip() for w in pool if isinstance(w, str) and w.strip()]
        pool = [w for w in pool if " " not in w]

        if len(pool) < WORDS_PER_TOPIC + 3:
            skipped_topics.append(topic)
            continue

        pool_shuffled = pool[:]
        random.shuffle(pool_shuffled)

        accepted = []
        for w in pool_shuffled:
            if len(accepted) >= WORDS_PER_TOPIC:
                break
            row = try_build_row(w, topic, pool)
            if not row:
                continue
            accepted.append(row)

        if len(accepted) < WORDS_PER_TOPIC:
            skipped_topics.append(topic)
            continue

        rows.extend(accepted)

    if not rows:
        raise RuntimeError("No topics generated any valid rows.")

    excel_rows = []
    for r in rows:
        rr = dict(r)
        rr["inflection"] = json.dumps(rr["inflection"], ensure_ascii=False)
        rr["word_family"] = json.dumps(rr["word_family"], ensure_ascii=False)
        rr["distractors"] = json.dumps(rr["distractors"], ensure_ascii=False)
        rr["examples"] = json.dumps(rr["examples"], ensure_ascii=False)
        excel_rows.append(rr)

    df = pd.DataFrame(excel_rows)
    preferred_cols = [
        "word",
        "phonetic",
        "audio",
        "part_of_speech",
        "definition_en",
        "definition_vi",
        "meaning_vi",
        "inflection",
        "word_family",
        "distractors",
        "examples",
        "topic",
        "level",
    ]
    df = df[[c for c in preferred_cols if c in df.columns]]

    try:
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f"DONE! Saved: {OUTPUT_EXCEL} | rows: {len(df)}")
    except PermissionError:
        fallback = Path(
            f"{OUTPUT_EXCEL.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{OUTPUT_EXCEL.suffix}"
        )
        df.to_excel(fallback, index=False)
        print(f"DONE! Saved fallback: {fallback} | rows: {len(df)}")

    if skipped_topics:
        print("SKIPPED_TOPICS:", ", ".join(skipped_topics))


if __name__ == "__main__":
    main()

