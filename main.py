"""Forecast GTA VI's launch-day Twitch viewers hour by hour (make.fun
gta6-twitch-ccu-forecast-01).

A program, not a model call: it reads one case (/input/<id>.in), fits a
launch-day shape from the case's own `comparables`, and writes
/output/<id>.out with five quantiles of the Twitch CCU for each of hours
2..24 of release day (UTC). Standard library only, deterministic, no
network, no clock reads: two runs on the same case write the same bytes.

The model
----------
Work in log space and anchor on the observed hour-1 print p1.  Every past
big launch in the case's comparables gives one release-day curve; for hour
h the log-ratio L_h = ln(viewers_h / viewers_1) is collected across those
curves, and the forecast is

    q_tau(h) = p1 * exp(m_h + 0.75 * b_h * d + z_tau * s_h)

where m_h is the median of L_h, b_h the OLS slope of L_h on centred
log(hour-1 print) -- bigger launches rise less steeply after hour 1,
because more of their audience is already watching in hour 1 -- d the
case's centred log(p1), clamped to +/-1.65 (the range the training games
cover, so a GTA-sized hour 1 never extrapolates the line past it), z_tau
the standard normal quantile at each scored level, and s_h the residual
spread (IQR / 1.349, floored at 0.10).

Which comparables count: only rolling-midnight console launches.  GTA VI
unlocks at midnight local time, region by region, so the shape that
transfers is the one of games that did the same -- an early dip while the
Americas are still locked (hours 2-4), a jump when the US East Coast
unlocks (hours 5-6), a midday plateau, then a steady rise into the US
daytime peak (hours 18-22) and a mild late decay.  Excluded: simultaneous
global unlocks (their hour 1 is a trickle, so their ratios are meaningless
here), PC-only launches, free-to-play launches, live-service launches,
early-access-contaminated launches (their hour 1 is already inflated),
games whose hour-1 print is under 20,000 viewers, and games whose peak is
more than 15x their hour 1.  The GTA VI category's own pre-release history
is not a launch and is excluded too.  On the kit's practice cases this
leaves 14 comparable launches; the final case adds the four practice
launches, for 18.

The fit happens at run time, from the comparables inside the case file, so
the program adapts to whatever the final case ships.  If fewer than 8
curves survive the filter (a format change, say), it falls back to the
constants below, fitted the same way on the kit's 18 curves (14 rolling
comparables + the 4 practice launches).

Validation (local, against the practice answers fetched from SullyGnome,
the same source the kit cites): mean pinball loss on the log scale

    ours (fit on 14 comparables, tested on the 4 practice launches):
        p00 Wolverine 0.256, p01 Red Dead 2 0.147,
        p02 God of War Ragnarok 0.104, p03 Spider-Man 2 0.183
        mean 0.173, typical miss ~30%, 90% coverage 0.82
    house baseline on the same cases: mean 0.387, typical miss ~83%

Leave-one-out over the 14 training curves: 0.251 (baseline 0.411).  For a
GTA-sized hour 1 (500,000+ viewers) the fitted shape peaks at about 1.18x
hour 1 in the evening (hours 19-20), inside the 1.00-1.71x range the
largest past launches showed.

How the grader runs it: `python3 -P -s /bot/main.py` (PYTHONHASHSEED=0) in
python:3.13-slim.  It reads $MAKEFUN_INPUT_DIR (else /input/) and writes to
$MAKEFUN_OUTPUT_DIR (else /output/).  One output file per input case, in
name order.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file would import.  (This entry is a single file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722]

# Fit constants.  See the module docstring for what each knob does.
MIN_H1 = 20000          # a comparable's hour-1 print must clear this
MAX_PEAK_RATIO = 15.0   # ... and its peak must stay within this of hour 1
MIN_CURVES = 8          # fewer surviving curves -> use FALLBACK below
BETA_SHRINK = 0.75      # shrink the size slope (see docstring)
DELTA_CLAMP = 1.65      # clamp centred log(p1) to the training range
SIGMA_FLOOR = 0.10      # smallest log-spread any hour may take

# Fitted the same way as fit_curves() below, on the kit's 18 curves (14
# rolling-midnight comparables + the 4 practice launches).  Per hour:
# (median log-ratio, size slope, residual log-spread).
FALLBACK_MEAN_LOG_H1 = 11.472673
FALLBACK = {
    2: (-0.1627, 0.0160, 0.1000),
    3: (-0.3309, 0.0408, 0.3151),
    4: (-0.3380, -0.0389, 0.3028),
    5: (-0.1600, -0.1684, 0.3063),
    6: (0.0559, -0.2202, 0.3505),
    7: (0.0421, -0.2111, 0.3215),
    8: (-0.0301, -0.2044, 0.2541),
    9: (-0.0451, -0.3108, 0.2805),
    10: (-0.0558, -0.3183, 0.3077),
    11: (-0.0566, -0.3307, 0.3038),
    12: (0.0028, -0.3922, 0.3363),
    13: (0.1183, -0.3995, 0.3277),
    14: (0.2679, -0.4135, 0.3610),
    15: (0.4290, -0.4599, 0.3063),
    16: (0.5506, -0.4750, 0.3049),
    17: (0.6199, -0.4658, 0.4714),
    18: (0.6967, -0.5067, 0.4996),
    19: (0.8099, -0.5224, 0.4164),
    20: (0.8361, -0.5527, 0.4700),
    21: (0.8292, -0.5730, 0.3889),
    22: (0.7945, -0.5688, 0.3710),
    23: (0.7474, -0.5170, 0.3142),
    24: (0.6201, -0.4993, 0.3199),
}


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def quantile(sorted_vals, q):
    """Linear-interpolation quantile of an already sorted list."""
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] * (hi - pos) + sorted_vals[hi] * (pos - lo)


def round2(x):
    """x rounded to 2 decimals, half up (as the house baseline rounds)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def is_rolling_launch(comp):
    """True when a comparable is a rolling-midnight console launch.

    The unlock note carries a "Tier:" tag; simultaneous-global, PC-only,
    free-to-play, live-service and slow-burn launches, and early-access
    contaminated ones, are not the shape GTA VI will have.  A "simultaneous
    at East Coast midnight" note (Zelda) is just the US unlock time and
    does not exclude: only a global simultaneous unlock does.
    """
    name = comp.get("name", "")
    if name.startswith("Grand Theft Auto VI"):
        return False
    u = (comp.get("unlock") or "").lower()
    if "tier: weak" in u:
        return False
    if "tier: early-access-contaminated" in u:
        return False
    if "single global" in u or "single time" in u:
        return False
    if "simultaneous" in u and ("pc" in u or "global" in u
                                or "across platforms" in u):
        return False
    if "pc only" in u:
        return False
    if "free-to-play" in u or "f2p" in u:
        return False
    if "live-service" in u:
        return False
    if "slow-burn" in u or "slow burn" in u:
        return False
    return True


def release_day_curve(comp):
    """{hour: viewers} for hours 1..24 of the comparable's release day."""
    try:
        day_start = parse_ts(comp["day_start"])
    except (KeyError, ValueError):
        return {}
    hours = {}
    for row in comp.get("hourly", []):
        try:
            t = parse_ts(row["from"])
            viewers = row["viewers"]
        except (KeyError, ValueError, TypeError):
            continue
        h = int((t - day_start).total_seconds() // 3600) + 1
        if 1 <= h <= 24 and isinstance(viewers, (int, float)):
            hours[h] = viewers
    return hours


def collect_curves(case):
    """Log-ratio curves of the rolling launches in this case.

    Returns a list of (hour-1 print, {hour: log(viewers / hour-1)}).
    """
    curves = []
    for comp in case.get("comparables", []):
        if not is_rolling_launch(comp):
            continue
        hours = release_day_curve(comp)
        if 1 not in hours or len(hours) < 20:
            continue
        h1 = hours[1]
        if not isinstance(h1, (int, float)) or h1 < MIN_H1:
            continue
        if max(hours.values()) / max(1, h1) > MAX_PEAK_RATIO:
            continue
        curves.append((h1, {h: math.log(max(1, v) / max(1, h1))
                            for h, v in hours.items()}))
    return curves


def fit_curves(curves):
    """Per hour (median log-ratio, size slope, residual spread) + mean log h1.

    The slope is the OLS slope of the hour's log-ratio on centred log
    hour-1 print; the spread is the IQR of the slope-adjusted residuals
    over 1.349 (the normal IQR), floored.
    """
    mean_log_h1 = sum(math.log(h1) for h1, _ in curves) / len(curves)
    stats = {}
    for h in range(2, 25):
        pts = [(math.log(h1) - mean_log_h1, lr[h])
               for h1, lr in curves if h in lr]
        if len(pts) < 3:
            continue
        med = quantile(sorted(y for _, y in pts), 0.5)
        num = sum(x * y for x, y in pts)
        den = sum(x * x for x, _ in pts)
        beta = num / den if den > 0 else 0.0
        resid = sorted(y - (med + beta * x) for x, y in pts)
        spread = (quantile(resid, 0.75) - quantile(resid, 0.25)) / 1.349
        stats[h] = (med, beta, max(SIGMA_FLOOR, spread))
    return stats, mean_log_h1


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])

    curves = collect_curves(case)
    if len(curves) >= MIN_CURVES:
        stats, mean_log_h1 = fit_curves(curves)
    else:
        stats, mean_log_h1 = FALLBACK, FALLBACK_MEAN_LOG_H1

    delta = math.log(p1) - mean_log_h1
    delta = max(-DELTA_CLAMP, min(DELTA_CLAMP, delta))

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        if h not in stats:
            # No training data for this hour (should not happen): fall back
            # to the house shape, flat with a widening spread.
            med, beta, sig = 0.0, 0.0, 0.15 * math.sqrt(h - 1)
        else:
            med, beta, sig = stats[h]
        q = [round2(p1 * math.exp(med + BETA_SHRINK * beta * delta + z * sig))
             for z in Z]
        # Keep every quantile inside (0, 1e9] and non-decreasing; rounding
        # can only ever make neighbours equal, never invert them.
        q = [min(max(v, 0.01), 1_000_000_000) for v in q]
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
