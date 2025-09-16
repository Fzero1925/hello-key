#!/usr/bin/env python3
"""
Refresh multi-source trending keywords cache for daily generation.
Outputs: data/trending_keywords_cache.json
Sources: Google Trends (pytrends if available), Reddit, YouTube (if keys provided)
Falls back to simulated data if sources unavailable.
"""
import os
import sys
import json
from datetime import datetime

def _setup_win():
    if sys.platform == "win32":
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        except Exception:
            pass

def main():
    _setup_win()
    # ensure project root is importable
    sys.path.append(os.getcwd())
    try:
        # Lazy import to avoid heavy deps if not installed in some environments
        from modules.keyword_tools.keyword_analyzer import SmartHomeKeywordAnalyzer
    except Exception as e:
        print(f"Unable to import analyzer: {e}")
        return 1

    analyzer = SmartHomeKeywordAnalyzer()

    # Aggregate trends
    print("🔎 Collecting Google Trends (if available)...")
    google_trends = []
    try:
        google_trends = analyzer.analyze_trending_topics(geo='US')
    except Exception as e:
        print(f"⚠️ Google Trends collection failed: {e}")

    print("🧩 Collecting multi-source trends (Reddit/YouTube/Amazon simulated or live)...")
    multi_trends = []
    try:
        multi_trends = analyzer.analyze_multi_source_trends(geo='US')
    except Exception as e:
        print(f"⚠️ Multi-source collection failed: {e}")

    all_items = (google_trends or []) + (multi_trends or [])
    if not all_items:
        print("⚠️ No trends collected; leaving existing cache untouched.")
        return 0

    # Deduplicate by keyword (case-insensitive)
    dedup = {}
    for item in all_items:
        kw = str(item.get('keyword', '')).strip()
        if not kw:
            continue
        key = kw.lower()
        if key not in dedup:
            dedup[key] = item
        else:
            # keep higher trend_score if available
            if item.get('trend_score', 0) > dedup[key].get('trend_score', 0):
                dedup[key] = item

    # Normalize fields for generator consumption
    normalized = []
    for key, item in dedup.items():
        kw = item.get('keyword', key)
        category = item.get('category', 'general')
        trend_score = float(item.get('trend_score', 0) or 0)

        # Use analyzer helpers where possible
        try:
            commercial_intent = analyzer._calculate_commercial_intent(kw)  # type: ignore
        except Exception:
            commercial_intent = 0.5

        difficulty = 'Medium'
        comp_score = float(item.get('competition_score', 0.5)) if isinstance(item.get('competition_score', 0.5), (int, float)) else 0.5
        search_volume = int(item.get('search_volume', 10000)) if str(item.get('search_volume', '')).isdigit() else 10000
        reason = item.get('reason', 'Selected from multi-source trend analysis')

        normalized.append({
            'keyword': kw,
            'category': category,
            'trend_score': trend_score,
            'competition_score': comp_score,
            'commercial_intent': commercial_intent,
            'search_volume': search_volume,
            'difficulty': difficulty,
            'reason': reason
        })

    # Sort by trend_score desc, then commercial_intent desc
    normalized.sort(key=lambda x: (x.get('trend_score', 0), x.get('commercial_intent', 0)), reverse=True)

    out_path = os.path.join('data', 'trending_keywords_cache.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"✅ Refreshed trending cache with {len(normalized)} items → {out_path}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
