"""Fast contract tests for optional ledger-based visualizations."""
import datetime
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("reproduce.py")
SPEC = importlib.util.spec_from_file_location("gqh_visualization_reproduce", SCRIPT)
viz = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(viz)


class LedgerVisualizationTests(unittest.TestCase):
    @staticmethod
    def fixture():
        start = datetime.date(2024, 1, 1)
        rows = []
        for i in range(80):
            day = (start + datetime.timedelta(days=i)).isoformat()
            for baseline, multiplier in (("A", 1.0), ("B", 1.2)):
                ret = ((i % 7) - 3) * .001 * multiplier
                rows.append({"date": day, "baseline": baseline, "net_return": str(ret),
                             "turnover": ".2", "gross_return": str(ret + .0001),
                             "costs": ".0001", "sample": "IS" if i < 40 else "OOS"})
        trades = []
        for i in range(24):
            trades.append({"baseline": "A" if i % 2 == 0 else "B",
                           "entry_date": (start + datetime.timedelta(days=i * 3)).isoformat(),
                           "net_pnl": str((i % 5 - 2) * 10), "size": str(100 + i),
                           "costs": "1", "holding_days": "3"})
        return rows, trades

    def test_metrics_use_actual_ledger_inputs(self):
        rows, trades = self.fixture()
        groups = viz.daily_groups(rows)
        metrics = viz.daily_metrics(groups["A"], [t for t in trades if t["baseline"] == "A"])
        self.assertEqual(metrics["observations"], 80)
        self.assertEqual(metrics["trade_count"], 12)
        self.assertIsNotNone(metrics["sharpe"])
        self.assertIsNotNone(metrics["profit_factor"])
        self.assertAlmostEqual(viz.returns_and_nav(groups["A"])[2][0], 99.7)

    def test_full_visual_family_builds_with_ledgers(self):
        rows, trades = self.fixture()
        figures, metrics, _ = viz.ledger_figures(viz.daily_groups(rows), trades)
        titles = {item["title"] for item in figures}
        self.assertEqual(len(metrics), 2)
        for expected in ("Daily equity curves by baseline", "Drawdown from running peak",
                         "Rolling 63-session Sharpe", "Rolling 63-session Sortino",
                         "Trade net-P&L distribution", "Trade frequency by entry month",
                         "Trade size, costs, duration, and outcome correlation",
                         "Circular block-bootstrap paths · observed versus simulated",
                         "Monte Carlo terminal-return distribution",
                         "Monte Carlo maximum-drawdown distribution",
                         "Chronological in-sample versus out-of-sample equity"):
            self.assertIn(expected, titles)

    def test_missing_optional_inputs_are_never_imputed(self):
        card = viz.unavailable("Equity", "Needs a ledger")
        self.assertIn("NO SOURCE LEDGER", str(card["figure"]))
        self.assertIn("Needs a ledger", card["figure"]["layout"]["annotations"][1]["text"])

    def test_nav_anchor_is_not_counted_as_a_zero_return_session(self):
        rows = [{"date": "2024-01-01", "nav": "100"},
                {"date": "2024-01-02", "nav": "90"},
                {"date": "2024-01-03", "nav": "99"}]
        metrics = viz.daily_metrics(rows)
        self.assertEqual(metrics["observations"], 2)
        self.assertEqual(metrics["start"], "2024-01-02")
        self.assertAlmostEqual(metrics["max_drawdown"], -0.1)

    def test_first_daily_return_is_measured_from_starting_capital(self):
        rows = [{"date": "2024-01-01", "net_return": "-0.10"},
                {"date": "2024-01-02", "net_return": "0.05"}]
        _, returns, nav = viz.returns_and_nav(rows)
        self.assertAlmostEqual(min(viz.max_drawdown(nav)), -0.10)
        self.assertEqual(len(returns), 2)


if __name__ == "__main__":
    unittest.main()
