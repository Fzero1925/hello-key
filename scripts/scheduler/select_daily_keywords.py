#!/usr/bin/env python3
"""
Daily Keyword Scheduler

Selects 2–4 diverse, non-duplicate keywords for today with assigned angles,
using the multi-source trending cache and recent usage history.

Outputs:
- data/daily_lineup_YYYYMMDD.json
- data/daily_lineup_latest.json
"""
import os
import re
import json
import sys
import argparse
from datetime import datetime, timedelta


def load_trending_cache(path="data/trending_keywords_cache.json"):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def recent_used_keywords(days=14, articles_dir="content/articles"):
    used = set()
    if not os.path.exists(articles_dir):
        return used
    cutoff = datetime.now() - timedelta(days=days)
    for name in os.listdir(articles_dir):
        if not name.endswith('.md'):
            continue
        path = os.path.join(articles_dir, name)
        try:
            ts = datetime.fromtimestamp(os.path.getctime(path))
        except Exception:
            continue
        if ts < cutoff:
            continue
        base = name[:-3]
        base = re.sub(r'-\d{8}$', '', base)
        used.add(base.replace('-', ' ').lower())
    return used


def canon_core(keyword: str) -> str:
    # Normalize by sorting deduped tokens; remove punctuation
    kw = re.sub(r"[^a-z0-9\s]", " ", keyword.lower())
    tokens = [t for t in kw.split() if t]
    # remove stop mini-words
    stop = {"for", "with", "and", "the", "a", "an", "to", "in"}
    tokens = [t for t in tokens if t not in stop]
    return " ".join(sorted(set(tokens)))


def choose_angles(keyword: str):
    base = ["best", "alternatives", "setup", "troubleshooting", "use-case", "vs"]
    kw = keyword.lower()
    # avoid vs if no clear comparator
    if " vs " in f" {kw} ":
        return ["vs", "best", "alternatives", "setup", "use-case", "troubleshooting"]
    # prefer use-case for scenario terms
    if any(t in kw for t in ["outdoor", "pet", "apartment", "garage", "dorm", "wireless", "energy"]):
        return ["use-case", "best", "setup", "alternatives", "troubleshooting", "vs"]
    return base


def load_angle_history(path="data/angle_history.json"):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_angle_history(history, path="data/angle_history.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def schedule_today(count=3):
    trends = load_trending_cache()
    if not trends:
        return []

    used = recent_used_keywords(days=14)
    angle_hist = load_angle_history()
    picks = []
    seen_core = set()
    used_cats = set()

    # Sort by trend_score desc then commercial_intent desc
    trends.sort(key=lambda x: (x.get('trend_score', 0.0), x.get('commercial_intent', 0.0)), reverse=True)

    for item in trends:
        kw = str(item.get('keyword', '')).strip()
        if not kw:
            continue
        cat = str(item.get('category', 'general')).replace(' ', '_')

        # recent used filter
        if kw.lower() in used:
            continue
        core = canon_core(kw)
        if not core or core in seen_core:
            continue

        # category diversity: try to avoid duplicates; allow if necessary later
        if cat in used_cats and len(used_cats) < count:
            continue

        angle_order = choose_angles(kw)
        # Rotate angle for same canonical keyword
        last = angle_hist.get(core, [])
        angle = next((a for a in angle_order if a not in last[-3:]), angle_order[0])

        picks.append({
            'keyword': kw,
            'category': cat,
            'angle': angle,
            'trend_score': item.get('trend_score', 0.0),
            'reason': item.get('reason', 'Selected by scheduler')
        })
        seen_core.add(core)
        used_cats.add(cat)
        # update history in-memory (persist later)
        angle_hist.setdefault(core, []).append(angle)
        if len(picks) >= count:
            break

    # If not enough due to diversity, relax category constraint and refill
    if len(picks) < count:
        for item in trends:
            if len(picks) >= count:
                break
            kw = str(item.get('keyword', '')).strip()
            if not kw or kw.lower() in used:
                continue
            core = canon_core(kw)
            if not core or core in seen_core:
                continue
            cat = str(item.get('category', 'general')).replace(' ', '_')
            angle_order = choose_angles(kw)
            last = angle_hist.get(core, [])
            angle = next((a for a in angle_order if a not in last[-3:]), angle_order[0])
            picks.append({
                'keyword': kw,
                'category': cat,
                'angle': angle,
                'trend_score': item.get('trend_score', 0.0),
                'reason': item.get('reason', 'Selected by scheduler (relaxed)')
            })
            seen_core.add(core)
            angle_hist.setdefault(core, []).append(angle)

    # Persist updated angle history for rotation across days
    save_angle_history(angle_hist)
    return picks


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
    parser = argparse.ArgumentParser(description='Select daily diverse keywords')
    parser.add_argument('--count', type=int, default=3, help='Target number of articles (2-4 recommended)')
    args = parser.parse_args()

    picks = schedule_today(max(2, min(4, args.count)))
    if not picks:
        print('⚠️ No picks available from trending cache')
        return 1

    today = datetime.now().strftime('%Y%m%d')
    out_dir = 'data'
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'daily_lineup_{today}.json')
    latest_path = os.path.join(out_dir, 'daily_lineup_latest.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    # Angle history already persisted in schedule_today()

    print(f'✅ Saved daily lineup ({len(picks)} items) → {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
