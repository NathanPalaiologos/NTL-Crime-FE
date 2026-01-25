#!/usr/bin/env python3
"""
USNO 'Fraction of the Moon Illuminated' -> monthly mean (fast; 1 request/year),
with timezone support for demo by state (e.g., Alabama).

Source service: USNO Astronomical Applications - Fraction of the Moon Illuminated.
It allows choosing reference time and the time zone.  :contentReference[oaicite:1]{index=1}

Important:
- This year-table service uses a FIXED time-zone offset (tz hours and tz_sign).
- It does NOT automatically account for DST transitions.
- For Alabama demo: use CST (UTC-6) as fixed offset.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import html as htmllib
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import requests

USNO_URL = "https://aa.usno.navy.mil/calculated/moon/fraction"
MONTHS = list(range(1, 13))

# Minimal state->timezone mapping for demo (expand if needed)
# tz_hours is the absolute magnitude; tz_sign: -1 means west (UTC minus), +1 means east (UTC plus).
STATE_TZ = {
    "AL": {"tz_hours": 6.0, "tz_sign": -1, "tz_label": "true"},  # Alabama: CST fixed (UTC-6)
}


def build_params(year: int, tz_hours: float, tz_sign: int, tz_label: str = "false") -> Dict[str, str]:
    """
    Parameters mirror the USNO "Get Data" form query.
    - tz: hours magnitude (e.g., 6.00)
    - tz_sign: -1 for UTC- offsets (west of Greenwich), +1 for UTC+ offsets (east)
    """
    if tz_sign not in (-1, 1):
        raise ValueError("tz_sign must be -1 (UTC-) or +1 (UTC+).")

    return {
        "submit": "Get Data",
        "task": "00",          # at Midnight
        "tz": f"{tz_hours:.2f}",
        "tz_label": tz_label,  # "true"/"false"
        "tz_sign": str(tz_sign),
        "year": str(year),
    }


def html_to_text_preserve_table(html: str) -> str:
    """
    Convert HTML to parseable text while preserving table cell/row boundaries.
    Critical: convert </td>, </th> to spaces and </tr> to newlines BEFORE stripping tags.
    """
    html = htmllib.unescape(html)

    # Preserve table structure
    html = re.sub(r"(?i)</(td|th)>", " ", html)     # cell boundary -> space
    html = re.sub(r"(?i)</tr>", "\n", html)         # row boundary -> newline
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)

    # Remove scripts/styles
    html = re.sub(r"(?is)<script\b[^>]*>.*?</script>", "", html)
    html = re.sub(r"(?is)<style\b[^>]*>.*?</style>", "", html)

    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)

    # Normalize whitespace
    html = html.replace("\r\n", "\n").replace("\r", "\n")
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{2,}", "\n", html)

    return html.strip()


DAY_START_RE = re.compile(r"^\s*(\d{2})\s+(.*)$")   # "01 0.48 0.58"
TOKEN_RE = re.compile(r"--|\d+\.\d+")              # tokens inside a line


def parse_wrapped_day_rows(lines: List[str], debug: bool = False) -> List[Tuple[int, List[Optional[float]]]]:
    """
    USNO often wraps a single day across multiple lines.
    We reconstruct by collecting 12 tokens total per day (Jan..Dec).
    """
    rows: List[Tuple[int, List[Optional[float]]]] = []

    current_day: Optional[int] = None
    current_tokens: List[str] = []

    def flush_if_complete() -> None:
        nonlocal current_day, current_tokens, rows
        if current_day is None:
            return
        if len(current_tokens) >= 12:
            toks = current_tokens[:12]
            vals: List[Optional[float]] = [None if t == "--" else float(t) for t in toks]
            rows.append((current_day, vals))
            if debug:
                print(f"DEBUG: completed day {current_day:02d} with 12 tokens.")
            current_day = None
            current_tokens = []

    for ln in lines:
        m = DAY_START_RE.match(ln)
        if m:
            if current_day is not None and len(current_tokens) != 12 and debug:
                print(f"DEBUG: dropping incomplete day {current_day:02d} with {len(current_tokens)} tokens.")
            current_day = int(m.group(1))
            current_tokens = TOKEN_RE.findall(m.group(2))
            flush_if_complete()
            continue

        if current_day is not None:
            more = TOKEN_RE.findall(ln)
            if more:
                current_tokens.extend(more)
                flush_if_complete()

    if current_day is not None and debug:
        print(f"DEBUG: dropping trailing incomplete day {current_day:02d} with {len(current_tokens)} tokens.")

    return rows


def fetch_year_html(session: requests.Session, year: int, tz_hours: float, tz_sign: int, tz_label: str,
                    retries: int = 5) -> str:
    params = build_params(year=year, tz_hours=tz_hours, tz_sign=tz_sign, tz_label=tz_label)
    backoff = 1.0
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(USNO_URL, params=params, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            if attempt == retries:
                break
            time.sleep(backoff)
            backoff = min(16.0, backoff * 2)
    raise RuntimeError(f"Failed to fetch year={year}: {last_err}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--out", type=str, default="usno_moon_monthly_2012_2024.csv")
    ap.add_argument("--sleep", type=float, default=0.15, help="Seconds between year requests.")
    ap.add_argument("--debug", action="store_true", help="Print diagnostics for the first year.")

    # Time zone selection
    ap.add_argument("--state", type=str, default=None, help="Two-letter state code for demo TZ, e.g., AL.")
    ap.add_argument("--tz-hours", type=float, default=0.0, help="Absolute TZ offset hours (e.g., 6.0).")
    ap.add_argument("--tz-sign", type=int, default=-1, help="TZ sign: -1 for UTC-, +1 for UTC+.")
    ap.add_argument("--tz-label", type=str, default="false", choices=["true", "false"], help="USNO tz_label param.")

    args = ap.parse_args()

    if args.end < args.start:
        raise ValueError("end year must be >= start year")

    # Resolve timezone
    if args.state is not None:
        st = args.state.strip().upper()
        if st not in STATE_TZ:
            raise ValueError(f"State '{st}' not supported in STATE_TZ mapping. Add it or pass --tz-hours/--tz-sign.")
        tz_hours = STATE_TZ[st]["tz_hours"]
        tz_sign = STATE_TZ[st]["tz_sign"]
        tz_label = STATE_TZ[st]["tz_label"]
    else:
        tz_hours = float(args.tz_hours)
        tz_sign = int(args.tz_sign)
        tz_label = args.tz_label

    # Aggregators
    sum_by_month = defaultdict(float)  # (year, month) -> sum of daily fractions
    n_by_month = defaultdict(int)      # (year, month) -> count of valid days

    with requests.Session() as session:
        for year in range(args.start, args.end + 1):
            raw_html = fetch_year_html(session, year=year, tz_hours=tz_hours, tz_sign=tz_sign, tz_label=tz_label)
            text = html_to_text_preserve_table(raw_html)
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

            if args.debug and year == args.start:
                print("DEBUG: first 40 non-empty lines after HTML->text:")
                for ln in lines[:40]:
                    print(ln)

            day_rows = parse_wrapped_day_rows(lines, debug=(args.debug and year == args.start))
            if len(day_rows) < 28:
                raise RuntimeError(
                    f"Parsing failed for {year}: only {len(day_rows)} day-rows reconstructed. "
                    "Run with --debug to inspect."
                )

            for day, vals in day_rows:
                for month, val in zip(MONTHS, vals):
                    if val is None:
                        continue
                    # Validate date exists
                    try:
                        _ = dt.date(year, month, day)
                    except ValueError:
                        continue
                    if not (0.0 <= val <= 1.0):
                        raise RuntimeError(f"Value out of [0,1] for {year}-{month:02d}-{day:02d}: {val}")
                    sum_by_month[(year, month)] += val
                    n_by_month[(year, month)] += 1

            time.sleep(args.sleep)

    # Completeness checks
    for year in range(args.start, args.end + 1):
        for month in MONTHS:
            expected_days = calendar.monthrange(year, month)[1]
            got_days = n_by_month.get((year, month), 0)
            if got_days != expected_days:
                raise RuntimeError(
                    f"Day count mismatch for {year}-{month:02d}: expected {expected_days}, got {got_days}."
                )

    # Write output
    expected_months = (args.end - args.start + 1) * 12
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("year_month,year,month,moon_fracillum_mean,n_days,tz_hours,tz_sign,state\n")
        state_written = args.state.strip().upper() if args.state else ""
        for year in range(args.start, args.end + 1):
            for month in MONTHS:
                n = n_by_month[(year, month)]
                mean = sum_by_month[(year, month)] / n
                f.write(f"{year}-{month:02d},{year},{month},{mean:.6f},{n},{tz_hours:.2f},{tz_sign},{state_written}\n")

    print(f"Wrote: {args.out}")
    print(f"Coverage: {args.start}-01 through {args.end}-12 ({expected_months} months)")
    if args.state and args.state.strip().upper() == "AL":
        print("Note: AL demo uses fixed CST offset (UTC-6). USNO year-table does not auto-handle DST.")


if __name__ == "__main__":
    main()
