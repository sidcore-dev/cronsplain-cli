import unittest
from datetime import datetime

from cronsplain_cli.core import describe, next_runs, parse_cron, parse_field


class TestParseField(unittest.TestCase):
    def test_star(self) -> None:
        self.assertEqual(parse_field("*", 0, 5), {0, 1, 2, 3, 4, 5})

    def test_list(self) -> None:
        self.assertEqual(parse_field("1,3,5", 0, 10), {1, 3, 5})

    def test_range(self) -> None:
        self.assertEqual(parse_field("2-5", 0, 10), {2, 3, 4, 5})

    def test_star_step(self) -> None:
        self.assertEqual(parse_field("*/15", 0, 59), {0, 15, 30, 45})

    def test_range_step(self) -> None:
        self.assertEqual(parse_field("0-10/5", 0, 59), {0, 5, 10})

    def test_out_of_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_field("99", 0, 59)

    def test_bad_step_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_field("*/0", 0, 59)

    def test_garbage_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_field("nope", 0, 59)


class TestParseCron(unittest.TestCase):
    def test_wrong_field_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_cron("* * * *")

    def test_valid_expression(self) -> None:
        expr = parse_cron("*/15 9-17 * * 1-5")
        self.assertEqual(expr.minute.values, frozenset({0, 15, 30, 45}))
        self.assertEqual(expr.dow.values, frozenset({1, 2, 3, 4, 5}))

    def test_dow_7_normalizes_to_sunday(self) -> None:
        expr = parse_cron("0 0 * * 7")
        self.assertEqual(expr.dow.values, frozenset({0}))

    def test_invalid_field_message_names_field(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_cron("99 0 * * *")
        self.assertIn("minute", str(ctx.exception))


class TestDescribe(unittest.TestCase):
    def test_every_minute(self) -> None:
        expr = parse_cron("* * * * *")
        self.assertEqual(describe(expr), "Every minute.")

    def test_every_n_minutes(self) -> None:
        expr = parse_cron("*/15 * * * *")
        self.assertIn("Every 15 minute(s)", describe(expr))

    def test_fixed_time(self) -> None:
        expr = parse_cron("30 9 * * *")
        self.assertIn("At 09:30", describe(expr))

    def test_weekday_names_used(self) -> None:
        expr = parse_cron("0 9 * * 1-5")
        text = describe(expr)
        self.assertIn("Monday", text)
        self.assertIn("Friday", text)

    def test_month_names_used(self) -> None:
        expr = parse_cron("0 0 1 1,6 *")
        text = describe(expr)
        self.assertIn("January", text)
        self.assertIn("June", text)

    def test_dom_and_dow_restricted_notes_or_semantics(self) -> None:
        expr = parse_cron("0 0 1 * 1")
        text = describe(expr)
        self.assertIn(" or ", text)


class TestNextRuns(unittest.TestCase):
    def test_every_minute_gives_consecutive_minutes(self) -> None:
        expr = parse_cron("* * * * *")
        start = datetime(2026, 1, 1, 12, 0, 0)
        runs = next_runs(expr, start, 3)
        self.assertEqual(
            runs,
            [datetime(2026, 1, 1, 12, 1), datetime(2026, 1, 1, 12, 2), datetime(2026, 1, 1, 12, 3)],
        )

    def test_daily_at_fixed_time(self) -> None:
        expr = parse_cron("30 9 * * *")
        start = datetime(2026, 1, 1, 10, 0, 0)
        runs = next_runs(expr, start, 2)
        self.assertEqual(runs[0], datetime(2026, 1, 2, 9, 30))
        self.assertEqual(runs[1], datetime(2026, 1, 3, 9, 30))

    def test_step_minutes(self) -> None:
        expr = parse_cron("*/15 * * * *")
        start = datetime(2026, 1, 1, 12, 5, 0)
        runs = next_runs(expr, start, 2)
        self.assertEqual(runs, [datetime(2026, 1, 1, 12, 15), datetime(2026, 1, 1, 12, 30)])

    def test_dom_dow_or_semantics(self) -> None:
        # Day-of-month 1 OR day-of-week Monday (1): both being restricted
        # means either condition triggers a run.
        expr = parse_cron("0 0 1 * 1")
        start = datetime(2026, 1, 1, 0, 0, 0)  # Jan 1 2026 is a Thursday
        runs = next_runs(expr, start, 2)
        # Next Monday after Jan 1 2026 is Jan 5; that should fire even
        # though it isn't day-of-month 1.
        self.assertIn(datetime(2026, 1, 5, 0, 0), runs)

    def test_impossible_expression_returns_empty_within_cap(self) -> None:
        expr = parse_cron("0 0 30 2 *")  # February 30th never happens
        start = datetime(2026, 1, 1, 0, 0, 0)
        runs = next_runs(expr, start, 1, max_minutes=60 * 24 * 40)  # ~40 days
        self.assertEqual(runs, [])


if __name__ == "__main__":
    unittest.main()
