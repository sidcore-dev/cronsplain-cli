import io
import unittest
from contextlib import redirect_stdout

from cronsplain_cli.cli import main


class TestCli(unittest.TestCase):
    def test_exit_code_0_on_valid_expression(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["*/15 * * * *"])
        self.assertEqual(code, 0)
        self.assertIn("Every 15 minute(s)", out.getvalue())

    def test_exit_code_2_on_invalid_expression(self) -> None:
        code = main(["* * * *"])
        self.assertEqual(code, 2)

    def test_exit_code_2_on_bad_count(self) -> None:
        code = main(["* * * * *", "--count", "0"])
        self.assertEqual(code, 2)

    def test_accepts_unquoted_fields(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["0", "9", "*", "*", "1-5"])
        self.assertEqual(code, 0)
        self.assertIn("Monday", out.getvalue())

    def test_count_controls_number_of_runs_printed(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            main(["* * * * *", "--count", "3"])
        lines = [l for l in out.getvalue().splitlines() if l.strip().startswith("2")]
        self.assertEqual(len(lines), 3)

    def test_shows_next_runs_header(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            main(["* * * * *"])
        self.assertIn("Next 5 run time(s):", out.getvalue())


if __name__ == "__main__":
    unittest.main()
