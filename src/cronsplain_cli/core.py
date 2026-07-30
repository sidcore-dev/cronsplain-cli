"""Core parsing, description, and scheduling logic for cronsplain-cli.

Supports standard 5-field cron expressions: minute, hour, day-of-month,
month, day-of-week. Each field accepts `*`, single values, comma-separated
lists, ranges (`a-b`), and steps (`*/n`, `a-b/n`, `a/n`). Named macros like
`@daily` and special characters like `L` or `W` are not supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MONTH_NAMES = [
    None, "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

FIELD_BOUNDS = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day-of-month": (1, 31),
    "month": (1, 12),
    "day-of-week": (0, 7),  # 7 is accepted as a synonym for 0 (Sunday)
}


def parse_field(raw: str, lo: int, hi: int) -> set[int]:
    """Parse a single cron field into the set of integers it matches."""
    values: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty entry in '{raw}'")

        base, sep, step_str = part.partition("/")
        step = 1
        if sep:
            if not step_str.isdigit() or int(step_str) <= 0:
                raise ValueError(f"invalid step '{step_str}' in '{part}'")
            step = int(step_str)

        if base == "*":
            b_lo, b_hi = lo, hi
        elif "-" in base:
            lo_s, _, hi_s = base.partition("-")
            if not (lo_s.lstrip("-").isdigit() and hi_s.isdigit()):
                raise ValueError(f"invalid range '{base}'")
            b_lo, b_hi = int(lo_s), int(hi_s)
            if b_lo > b_hi:
                raise ValueError(f"range start greater than end in '{base}'")
        else:
            if not base.isdigit():
                raise ValueError(f"invalid value '{base}'")
            b_lo = int(base)
            b_hi = hi if sep else b_lo

        if b_lo < lo or b_hi > hi:
            raise ValueError(f"value out of range [{lo}, {hi}] in '{part}'")

        for v in range(b_lo, b_hi + 1, step):
            values.add(v)

    if not values:
        raise ValueError(f"no values parsed from '{raw}'")
    return values


@dataclass(frozen=True)
class FieldSpec:
    raw: str
    values: frozenset[int]


@dataclass(frozen=True)
class CronExpression:
    minute: FieldSpec
    hour: FieldSpec
    dom: FieldSpec
    month: FieldSpec
    dow: FieldSpec


def _parse_named_field(raw: str, name: str) -> set[int]:
    lo, hi = FIELD_BOUNDS[name]
    try:
        return parse_field(raw, lo, hi)
    except ValueError as exc:
        raise ValueError(f"invalid {name} field '{raw}': {exc}") from exc


def parse_cron(expression: str) -> CronExpression:
    """Parse a 5-field cron expression into a CronExpression."""
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError(
            f"expected 5 fields (minute hour day-of-month month day-of-week), got {len(parts)}: '{expression}'"
        )
    minute_raw, hour_raw, dom_raw, month_raw, dow_raw = parts

    minute = FieldSpec(minute_raw, frozenset(_parse_named_field(minute_raw, "minute")))
    hour = FieldSpec(hour_raw, frozenset(_parse_named_field(hour_raw, "hour")))
    dom = FieldSpec(dom_raw, frozenset(_parse_named_field(dom_raw, "day-of-month")))
    month = FieldSpec(month_raw, frozenset(_parse_named_field(month_raw, "month")))

    dow_values = _parse_named_field(dow_raw, "day-of-week")
    dow_values = frozenset(0 if v == 7 else v for v in dow_values)
    dow = FieldSpec(dow_raw, dow_values)

    return CronExpression(minute=minute, hour=hour, dom=dom, month=month, dow=dow)


# --- Plain-English description ---------------------------------------------


def _name(token: str, names: list[str] | None) -> str:
    if names is None:
        return token
    idx = int(token) % len(names)
    return names[idx]


def _describe_token(token: str, names: list[str] | None) -> str:
    base, sep, step = token.partition("/")
    if sep:
        if base == "*":
            return f"every {step}"
        if "-" in base:
            lo, hi = base.split("-", 1)
            return f"every {step} from {_name(lo, names)} to {_name(hi, names)}"
        return f"every {step} starting at {_name(base, names)}"
    if "-" in token:
        lo, hi = token.split("-", 1)
        return f"{_name(lo, names)} through {_name(hi, names)}"
    return _name(token, names)


def _join_and(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _field_phrase(field: FieldSpec, unit: str, names: list[str] | None) -> str:
    tokens = field.raw.split(",")
    if len(tokens) == 1:
        token = tokens[0]
        if token == "*":
            return f"every {unit}"
        step = _pure_step(token)
        if step is not None:
            return f"every {step} {unit}s"
    joined = _join_and([_describe_token(t, names) for t in tokens])
    if len(tokens) == 1 and tokens[0].isdigit():
        return f"{unit} {joined}"
    return f"{unit}(s) {joined}"


def _pure_step(raw: str) -> int | None:
    if raw.startswith("*/") and raw[2:].isdigit():
        return int(raw[2:])
    return None


def _describe_time(minute: FieldSpec, hour: FieldSpec) -> str:
    if minute.raw == "*" and hour.raw == "*":
        return "Every minute"

    if hour.raw == "*":
        step = _pure_step(minute.raw)
        if step is not None:
            return f"Every {step} minute(s)"
        return f"At {_field_phrase(minute, 'minute', None)} past every hour"

    if minute.raw == "*":
        step = _pure_step(hour.raw)
        if step is not None:
            return f"Every minute during every {step} hour(s)"
        return f"Every minute during {_field_phrase(hour, 'hour', None)}"

    if minute.raw.isdigit() and hour.raw.isdigit():
        return f"At {int(hour.raw):02d}:{int(minute.raw):02d}"

    return f"At {_field_phrase(minute, 'minute', None)} past {_field_phrase(hour, 'hour', None)}"


def describe(expr: CronExpression) -> str:
    """Return a plain-English description of a parsed cron expression."""
    sentence = [_describe_time(expr.minute, expr.hour)]

    dom_restricted = expr.dom.raw != "*"
    dow_restricted = expr.dow.raw != "*"

    if dom_restricted and dow_restricted:
        dom_phrase = _field_phrase(expr.dom, "day-of-month", None)
        dow_phrase = _field_phrase(expr.dow, "weekday", WEEKDAY_NAMES)
        sentence.append(
            f"on {dom_phrase} or {dow_phrase} "
            "(cron runs on either match when both day fields are restricted)"
        )
    elif dom_restricted:
        sentence.append(f"on {_field_phrase(expr.dom, 'day-of-month', None)}")
    elif dow_restricted:
        sentence.append(f"on {_field_phrase(expr.dow, 'weekday', WEEKDAY_NAMES)}")

    if expr.month.raw != "*":
        sentence.append(f"in {_field_phrase(expr.month, 'month', MONTH_NAMES)}")

    return ", ".join(sentence) + "."


# --- Next run time computation ----------------------------------------------

_DEFAULT_MAX_MINUTES = 4 * 366 * 24 * 60  # about 4 years


def next_runs(
    expr: CronExpression,
    start: datetime,
    count: int,
    max_minutes: int = _DEFAULT_MAX_MINUTES,
) -> list[datetime]:
    """Return up to `count` datetimes after `start` matching `expr`.

    Search proceeds minute-by-minute, which keeps the matching logic (and
    the standard cron day-of-month/day-of-week OR quirk) simple and
    obviously correct, at the cost of being a brute-force scan. If no
    match is found within `max_minutes`, returns whatever was found
    (possibly an empty list) rather than searching forever.
    """
    dom_restricted = expr.dom.raw != "*"
    dow_restricted = expr.dow.raw != "*"

    results: list[datetime] = []
    current = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    steps = 0

    while len(results) < count and steps < max_minutes:
        if (
            current.minute in expr.minute.values
            and current.hour in expr.hour.values
            and current.month in expr.month.values
        ):
            dow_val = current.isoweekday() % 7  # Mon=1..Sat=6, Sun=0 (matches cron)
            if dom_restricted and dow_restricted:
                day_ok = current.day in expr.dom.values or dow_val in expr.dow.values
            elif dom_restricted:
                day_ok = current.day in expr.dom.values
            elif dow_restricted:
                day_ok = dow_val in expr.dow.values
            else:
                day_ok = True
            if day_ok:
                results.append(current)
        current += timedelta(minutes=1)
        steps += 1

    return results
