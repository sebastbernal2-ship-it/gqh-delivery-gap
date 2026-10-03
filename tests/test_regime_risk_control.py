#!/usr/bin/env python3
"""Compile and exercise the overlay against synthetic inputs only."""
import csv
import datetime as dt
import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RegimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('c++')
        if not compiler:
            raise RuntimeError('C++17 compiler required for regime regression tests')
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.binary = cls.directory / 'regime'
        subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic',
                        '-Werror', str(ROOT / 'scripts/regime_risk_control.cpp'),
                        '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, entry='2017-02-01', gap=False, history=280, gross=0.03,
                 second=False):
        folder = Path(tempfile.mkdtemp(dir=self.directory))
        strategy = folder / 'strategy.csv'
        with strategy.open('w') as handle:
            handle.write('vintage,signal,position,entry,exit,gross\n')
            handle.write(f'2017-01,test,buildout,{entry},{entry},{gross}\n')
            if second:
                handle.write('2017-02,test,buildout,2017-02-02,2017-02-02,0.03\n')
            # Outside the fence: malformed outcomes must never be parsed.
            handle.write('2023-01,test,buildout,2023-02-01,2023-03-01,SEALED\n')
        end = dt.date(2017, 1, 31)
        dates = []
        day = end
        while len(dates) < history:
            if day.weekday() < 5:
                dates.append(day)
            day -= dt.timedelta(days=1)
        dates.reverse()
        if gap:
            dates = [day for day in dates if not dt.date(2016, 12, 1) <= day <= dt.date(2016, 12, 20)]
        if second:
            dates.append(dt.date(2017, 2, 1))
        bars = folder / 'bars.tsv'
        with bars.open('w') as handle:
            handle.write('date\tsym\tsource_id\tbatch_sha256\tclose_px_e8usd\n')
            for i, day in enumerate(dates):
                price = round(100 * math.exp(0.02 * math.sin(i * 0.7)) * 100000000)
                handle.write(f'{day}\tSPY\tmassive_bars\t{"a" * 64}\t{price}\n')
        periods, summary = folder / 'periods.csv', folder / 'summary.csv'
        run = subprocess.run([str(self.binary), '--strategy', str(strategy), '--bars', str(bars),
                              '--out-periods', str(periods), '--out-summary', str(summary)],
                             capture_output=True, text=True)
        return run, periods, summary

    def read_rows(self, path):
        with path.open() as handle:
            return list(csv.DictReader(handle))

    def test_stale_history_fails_without_outputs(self):
        run, periods, summary = self.run_case(entry='2021-02-01')
        self.assertEqual(run.returncode, 2)
        self.assertIn('stale SPY history', run.stderr)
        self.assertFalse(periods.exists())
        self.assertFalse(summary.exists())

    def test_history_gap_fails(self):
        run, periods, _ = self.run_case(gap=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('history gap', run.stderr)
        self.assertFalse(periods.exists())

    def test_fresh_history_and_sealed_fence(self):
        run, periods, _ = self.run_case()
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = self.read_rows(periods)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['spy_asof'], '2017-01-31')
        self.assertIn(rows[0]['regime'], ['normal_vol', 'high_vol'])

    def test_weekend_allowed_and_seven_day_boundary(self):
        for entry in ['2017-02-06', '2017-02-07']:
            run, _, _ = self.run_case(entry=entry)
            self.assertEqual(run.returncode, 0, run.stderr)
        run, _, _ = self.run_case(entry='2017-02-08')
        self.assertEqual(run.returncode, 2)
        self.assertIn('stale SPY history', run.stderr)

    def test_fresh_warmup_and_empty_subset_metrics(self):
        run, periods, summary = self.run_case(entry='2016-03-01', second=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.read_rows(periods)[0]['regime'], 'warmup')
        rows = self.read_rows(summary)
        metric_columns = ['average_exposure', 'mean_monthly_net', 'annualized_net',
                          'sharpe_monthly', 'max_drawdown', 'average_turnover_factor', 'compounded_net']
        empty = [row for row in rows if row['periods'] == '0']
        self.assertTrue(empty)
        for row in empty:
            self.assertTrue(all(row[column] == '' for column in metric_columns), row)
        for row in rows:
            if int(row['periods']) < 2:
                self.assertEqual(row['sharpe_monthly'], '')

    def test_zero_dispersion_sharpe_undefined(self):
        run, _, summary = self.run_case(second=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [row for row in self.read_rows(summary)
                if row['condition'] == 'all' and row['policy'] == 'unfiltered']
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['periods'], '2')
            self.assertEqual(row['sharpe_monthly'], '')
            self.assertNotEqual(row['annualized_net'], '')

    def test_invalid_calendar_date_rejected(self):
        run, periods, _ = self.run_case(entry='2017-02-30')
        self.assertEqual(run.returncode, 2)
        self.assertIn('invalid calendar date', run.stderr)
        self.assertFalse(periods.exists())


if __name__ == '__main__':
    unittest.main()
