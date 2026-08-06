"""F-Score sonuçları için LLM tabanlı yatırımcı yorumu + kural-tabanlı fallback.

app.py bu modülü "AI Yorumu" bölümünde çağırır: önce generate_ai_commentary
denenir; API anahtarı yoksa, paket kurulu değilse veya çağrı herhangi bir
nedenle başarısız olursa None döner ve çağıran taraf generate_fallback_commentary'ye
düşer. Fallback LLM'e bağımlı değildir, her zaman çalışır.
"""
from __future__ import annotations

import os

from scoring.fscore_criteria_definitions import CATEGORIES, CRITERIA_INFO


def _get_config(key: str, default: str = "") -> str:
    """db/connection.py::_get_config ile aynı desen — önce st.secrets, yoksa .env."""
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def _category_summary(f_score_detail: dict) -> dict[str, tuple[int, int]]:
    """Her kategori için (sağlanan kriter sayısı, hesaplanabilen kriter sayısı)."""
    totals: dict[str, list[int]] = {key: [0, 0] for key in CATEGORIES}
    for c in f_score_detail.get("criteria", []):
        category = CRITERIA_INFO.get(c["name"], {}).get("category")
        if category is None or c["score"] is None:
            continue
        totals[category][1] += 1
        if c["score"] == 1:
            totals[category][0] += 1
    return {k: (v[0], v[1]) for k, v in totals.items()}


def generate_fallback_commentary(f_score_detail: dict, ticker: str = "") -> str:
    """Kural tabanlı, şablon yorum — LLM çağrısı YOK, her zaman çalışır."""
    total = f_score_detail.get("total_score", 0)
    calculated = f_score_detail.get("calculated_count", 0)
    unavailable = f_score_detail.get("unavailable_count", 0)

    if calculated == 0:
        return "Bu şirket için F-Score kriterlerinin hiçbiri hesaplanamadı; finansal veri yetersiz."

    if total >= 7:
        verdict = "güçlü bir finansal tablo sergiliyor"
    elif total >= 4:
        verdict = "orta düzeyde, karışık sinyaller veren bir finansal tablo sergiliyor"
    else:
        verdict = "zayıf bir finansal tablo sergiliyor"

    label = ticker or "Bu şirket"
    parts = [f"{label}, {calculated} kriterden {total} tanesini sağlayarak {verdict}."]

    cat_summary = _category_summary(f_score_detail)
    cat_sentences = []
    for key, info in sorted(CATEGORIES.items(), key=lambda kv: kv[1]["order"]):
        passed, cnt = cat_summary.get(key, (0, 0))
        if cnt == 0:
            continue
        cat_sentences.append(f"{info['label']} alanında {cnt} kriterden {passed} tanesi olumlu")
    if cat_sentences:
        parts.append("; ".join(cat_sentences) + ".")

    if unavailable:
        parts.append(f"{unavailable} kriter için yeterli veri bulunamadı.")

    return " ".join(parts)


def generate_ai_commentary(f_score_detail: dict, ticker: str) -> str | None:
    """Anthropic API ile 3-4 cümlelik Türkçe yatırımcı yorumu üretir.

    Herhangi bir hata durumunda (API anahtarı tanımlı değil, paket kurulu
    değil, ağ hatası, vb.) None döner — çağıran taraf generate_fallback_commentary'ye
    düşmeli. Model, ANTHROPIC_MODEL ile override edilebilir (varsayılan: claude-opus-5).
    """
    api_key = _get_config("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    criteria_lines = []
    for c in f_score_detail.get("criteria", []):
        label = CRITERIA_INFO.get(c["name"], {}).get("label", c["name"])
        if c["score"] is None:
            verdict = "eksik veri"
        elif c["score"] == 1:
            verdict = "sağlandı"
        else:
            verdict = "sağlanmadı"
        criteria_lines.append(f"- {label}: {verdict} ({c['notes']})")

    prompt = (
        f"Aşağıda {ticker} hissesi için Piotroski F-Score kriterlerinin sonuçları var "
        f"(toplam skor: {f_score_detail.get('total_score')}/9, "
        f"{f_score_detail.get('calculated_count')} kriter hesaplanabildi, "
        f"{f_score_detail.get('unavailable_count')} kriter için veri eksik):\n\n"
        + "\n".join(criteria_lines)
        + "\n\nBu sonuçlara dayanarak 3-4 cümlelik, Türkçe, yatırımcıya yönelik "
        "objektif bir değerlendirme yaz. Yatırım tavsiyesi verme (\"al\", \"sat\" gibi "
        "ifadeler kullanma), sadece finansal tabloda görülen güçlü ve zayıf noktaları "
        "özetle. Sadece yorum metnini döndür, başlık veya madde işareti kullanma."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        model = _get_config("ANTHROPIC_MODEL", "claude-opus-5")
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in response.content if b.type == "text"), None)
        return text.strip() if text else None
    except Exception:
        return None
