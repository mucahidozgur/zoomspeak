"""Transkripsiyon sonucunu biçimlendirir: konuşmacı turları, TXT, SRT, Markdown.

Tamamı saf fonksiyonlardır; ağ ve Streamlit bağımlılığı yoktur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.utils import format_srt_timestamp, format_timestamp

PAUSE_SPLIT_MS = 2000  # bu süreden uzun sessizlik yeni konuşma turu başlatır
MAX_SRT_CHARS = 80  # bir SRT segmenti için yaklaşık üst karakter sınırı
DEFAULT_SPEAKER = "1"  # "speaker" alanı yoksa kullanılır (tek konuşmacılı kayıt)


def group_tokens_by_speaker(
    tokens: list[dict], max_gap_ms: int = PAUSE_SPLIT_MS
) -> list[dict]:
    """Token'ları konuşmacı turlarına gruplar.

    Aynı konuşmacının, aralarındaki boşluk max_gap_ms'i aşmayan ardışık
    token'ları tek tur sayılır. Konuşmacı değişimi veya uzun sessizlik yeni
    tur başlatır. Tur: {"speaker", "tokens", "start_ms", "end_ms"}.
    """
    turns: list[dict] = []
    current: dict | None = None

    for token in tokens:
        speaker = str(token.get("speaker") or DEFAULT_SPEAKER)
        start_ms = int(token.get("start_ms") or 0)
        end_ms = int(token.get("end_ms") or start_ms)

        new_turn = (
            current is None
            or speaker != current["speaker"]
            or start_ms - current["end_ms"] > max_gap_ms
        )
        if new_turn:
            current = {
                "speaker": speaker,
                "tokens": [],
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
            turns.append(current)
        else:
            current["end_ms"] = max(current["end_ms"], end_ms)
        current["tokens"].append(token)

    return turns


def _join_token_texts(tokens: list[dict]) -> str:
    """Token metinlerini birleştirir.

    Soniox token'ları kelime altı parçalardır (ör. "Mer", " hab", "a") ve
    kelime sınırını token metninin BAŞINDAKİ boşluk karakteriyle işaret eder:
    " hab" yeni bir kelimenin başlangıcı, boşluksuz "a" ise önceki kelimenin
    devamıdır. Bu yüzden token'lar tek tek strip edilip boşlukla
    birleştirilmemelidir — bu "Mer hab a" gibi bölük çıktıya yol açar (bize
    bildirilen hata buydu). Metinler ham haliyle bitiştirilir, böylece gömülü
    boşluklar kelime sınırını korur; ardından boşluklar normalize edilir ve
    noktalama öncesi boşluklar temizlenir. Sonuç, Soniox'un döndürdüğü üst
    seviye `text` alanıyla birebir aynıdır (gerçek veriyle doğrulandı).
    """
    text = "".join(str(t.get("text") or "") for t in tokens)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def _turn_text(turn: dict) -> str:
    """Turun metnini döndürür.

    Token'sız yedek turda (Soniox yalnızca üst seviye `text` döndürdüyse)
    doğrudan o metin kullanılır; normal turlarda token'lar birleştirilir.
    """
    if turn.get("text"):
        return turn["text"]
    return _join_token_texts(turn.get("tokens") or [])


def build_txt(turns: list[dict]) -> str:
    """Konuşmacı etiketli düz metin üretir (TXT indirme formatı)."""
    blocks = []
    for turn in turns:
        label = f"Konuşmacı {turn['speaker']} [{format_timestamp(turn['start_ms'])}]:"
        blocks.append(f"{label}\n{_turn_text(turn)}")
    return "\n\n".join(blocks)


def build_markdown(turns: list[dict]) -> str:
    """Ekranda düzenli gösterim için Markdown üretir (kalın konuşmacı etiketi)."""
    blocks = []
    for turn in turns:
        label = f"**Konuşmacı {turn['speaker']}** — `{format_timestamp(turn['start_ms'])}`"
        blocks.append(f"{label}\n\n{_turn_text(turn)}")
    return "\n\n".join(blocks)


def turns_to_srt_segments(
    turns: list[dict], max_chars: int = MAX_SRT_CHARS
) -> list[dict]:
    """Turları SRT segmentlerine böler; uzun turlar kelime sınırından kırılır.

    Segment: {"speaker", "text", "start_ms", "end_ms"} — zaman damgaları
    kelime seviyesinde korunur.
    """
    segments: list[dict] = []
    for turn in turns:
        buffer: list[dict] = []
        char_count = 0
        for token in turn["tokens"]:
            raw = str(token.get("text") or "")
            text = raw.strip()
            if not text:
                continue
            # Token'lar kelime altı parça olduğundan, bölme yalnızca YENİ kelime
            # başlangıcında (metni boşlukla başlayan token) yapılır; böylece bir
            # kelime iki SRT segmenti arasında parçalanmaz.
            starts_word = raw[:1].isspace()
            add = len(text) + (1 if buffer else 0)
            if buffer and starts_word and char_count + add > max_chars:
                segments.append(_make_segment(turn["speaker"], buffer))
                buffer = []
                char_count = 0
            buffer.append(token)
            char_count += add
        if buffer:
            segments.append(_make_segment(turn["speaker"], buffer))
    return segments


def _make_segment(speaker: str, tokens: list[dict]) -> dict:
    return {
        "speaker": speaker,
        "text": _join_token_texts(tokens),
        "start_ms": int(tokens[0].get("start_ms") or 0),
        "end_ms": int(tokens[-1].get("end_ms") or tokens[-1].get("start_ms") or 0),
    }


def build_srt(segments: list[dict]) -> str:
    """SRT altyazı metni üretir (her segmentte konuşmacı etiketi)."""
    blocks = []
    for i, seg in enumerate(segments, start=1):
        timing = (
            f"{format_srt_timestamp(seg['start_ms'])} --> "
            f"{format_srt_timestamp(seg['end_ms'])}"
        )
        blocks.append(f"{i}\n{timing}\nKonuşmacı {seg['speaker']}: {seg['text']}")
    return "\n\n".join(blocks)


@dataclass
class FormattedResult:
    """Biçimlendirilmiş transkripsiyon sonucu."""

    raw: dict
    turns: list[dict]
    txt: str
    srt: str
    markdown: str
    base_name: str
    txt_path: str | None = None
    srt_path: str | None = None


def format_transcript(transcript: dict, base_name: str) -> FormattedResult:
    """Ham Soniox sonucunu konuşmacı turlarına, TXT, SRT ve Markdown'a çevirir.

    Normal durumda token'lar kullanılır; konuşmacı etiketi ve zaman damgası
    taşıyan tek kaynak onlardır. Soniox token döndürmezse (nadir yedek yol),
    yanıtın doğrudan `text` alanı tek konuşmacılı tam metin olarak kullanılır —
    bu durumda zaman damgası olmadığından SRT boş kalır.
    """
    tokens = transcript.get("tokens") or []
    if tokens:
        turns = group_tokens_by_speaker(tokens)
    else:
        full_text = str(transcript.get("text") or "").strip()
        turns = (
            [{
                "speaker": DEFAULT_SPEAKER,
                "tokens": [],
                "text": full_text,
                "start_ms": 0,
                "end_ms": 0,
            }]
            if full_text
            else []
        )
    return FormattedResult(
        raw=transcript,
        turns=turns,
        txt=build_txt(turns),
        srt=build_srt(turns_to_srt_segments(turns)),
        markdown=build_markdown(turns),
        base_name=base_name,
    )


def write_output_files(fmt: FormattedResult, output_dir: str = "output") -> tuple[str, str]:
    """TXT ve SRT dosyalarını output/ altına yazar, yolları döndürür."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    txt_path = out / f"{fmt.base_name}.txt"
    srt_path = out / f"{fmt.base_name}.srt"
    txt_path.write_text(fmt.txt, encoding="utf-8")
    srt_path.write_text(fmt.srt, encoding="utf-8")
    fmt.txt_path = str(txt_path)
    fmt.srt_path = str(srt_path)
    return str(txt_path), str(srt_path)
