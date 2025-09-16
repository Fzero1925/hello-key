# scoring.py — minimal, dependency-light scoring helpers for Keyword Engine v2
# Usage: from modules.keyword_tools.scoring import opportunity_score, estimate_value, estimate_adsense, estimate_amazon

def clamp01(x):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def opportunity_score(T, I, S, F, D, d_penalty=0.6):
    """Return 0-100 opportunity score.
    T,I,S,F,D are in 0..1 (D is difficulty, higher = harder)
    """
    T = clamp01(T); I = clamp01(I); S = clamp01(S); F = clamp01(F); D = clamp01(D)
    base = 0.35*T + 0.30*I + 0.15*S + 0.20*F
    score = 100.0 * base * (1.0 - d_penalty * D)
    if score < 0: score = 0.0
    if score > 100: score = 100.0
    return round(score, 2)

def estimate_adsense(search_volume, ctr_serp=0.25, click_share_rank=0.35, rpm_usd=10.0):
    try:
        sv = max(0.0, float(search_volume))
    except Exception:
        sv = 0.0
    pv = sv * float(ctr_serp) * float(click_share_rank)
    return round((pv / 1000.0) * float(rpm_usd), 2)

def estimate_amazon(search_volume, ctr_to_amazon=0.12, cr=0.04, aov_usd=80.0, commission=0.03):
    try:
        sv = max(0.0, float(search_volume))
    except Exception:
        sv = 0.0
    pv_to_amz = sv * float(ctr_to_amazon)
    revenue = pv_to_amz * float(cr) * float(aov_usd) * float(commission)
    return round(revenue, 2)

def estimate_value(search_volume, opp_score, ads_params=None, aff_params=None, mode='max'):
    ads_params = ads_params or {}
    aff_params = aff_params or {}
    ra = estimate_adsense(search_volume, **ads_params)
    rf = estimate_amazon(search_volume, **aff_params)
    base = max(ra, rf) if mode == 'max' else (ra + rf)
    # stability factor uses opp_score in 0..100
    factor = 0.6 + 0.4 * (max(0.0, min(100.0, float(opp_score))) / 100.0)
    return round(base * factor, 2)

def explain_selection(trend_pct, intent_hits, difficulty_label):
    return {
        "trend": f"Last-30% mean {trend_pct:+.0f}% vs overall",
        "intent": f"Intent hits: {', '.join(intent_hits) if intent_hits else 'N/A'}",
        "difficulty": difficulty_label or "n/a"
    }

def make_revenue_range(point_estimate):
    """Return a human-friendly revenue range like $X–$Y based on a single point estimate."""
    try:
        v = float(point_estimate)
    except Exception:
        v = 0.0
    low = max(0.0, v * 0.75)
    high = v * 1.25
    return {"point": round(v, 2), "range": f"${low:.0f}–${high:.0f}/mo"}