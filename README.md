# cronsplain-cli

A small, dependency-free command-line tool that explains a standard
5-field cron expression in plain English and prints its next few
run times.

## Why

Cron syntax is compact and easy to get subtly wrong — is `*/15 9-17 * * 1-5`
"every 15 minutes" or "every 15th minute during business hours on
weekdays"? `cronsplain-cli` translates the expression into a sentence and
shows you concrete upcoming timestamps, so you can sanity-check a
schedule before it goes live.

## Install

```bash
pip install .
```

This installs a `cronsplain-cli` command on your PATH.

## Usage

```bash
cronsplain-cli '*/15 9-17 * * 1-5'
```

Example output:

```
At every 15 minutes past hour(s) 9 through 17, on weekday(s) Monday through Friday.

Next 5 run time(s):
  2026-07-30 09:00 (Thursday)
  2026-07-30 09:15 (Thursday)
  2026-07-30 09:30 (Thursday)
  2026-07-30 09:45 (Thursday)
  2026-07-30 10:00 (Thursday)
```

You can quote the expression or pass its 5 fields as separate arguments:

```bash
cronsplain-cli 0 9 1 * * --count 3
```

### Options

| Flag       | Description                                          |
|------------|-------------------------------------------------------|
| `--count`  | Number of upcoming run times to show (default: 5)     |

### Supported syntax

Each of the 5 fields (minute, hour, day-of-month, month, day-of-week)
accepts:

- `*` — every value
- a single number, e.g. `5`
- a list, e.g. `1,2,3`
- a range, e.g. `1-5`
- a step, e.g. `*/15`, `1-30/5`, or `10/15`

Day-of-week is `0`-`6` (`0` = Sunday); `7` is also accepted as a synonym
for Sunday. When both day-of-month and day-of-week are restricted
(neither is `*`), standard cron semantics apply: the job runs when
*either* field matches, not when both match — `cronsplain-cli` follows
that rule and calls it out in the explanation.

**Not supported:** named macros like `@daily`/`@hourly`, month/weekday
names (`JAN`, `MON`), and special characters like `L` (last day) or `W`
(nearest weekday). Passing any of these produces a parse error rather
than a wrong answer.

### Exit codes

- `0` — expression parsed successfully
- `2` — the expression is invalid (wrong number of fields, out-of-range
  value, bad syntax) or `--count` is less than 1

## Development

```bash
pip install -e .
python -m unittest discover -s tests -v
```

## License

All rights reserved. This code is public for viewing and reference only —
no license is granted to use, copy, modify, or redistribute it. See
[LICENSE](LICENSE) for details.
