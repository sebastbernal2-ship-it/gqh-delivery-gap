#!/usr/bin/env python3
"""Contract tests against the checked-in fixture_report output from the OCaml engine."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest_engine_report as writer  # noqa: E402


REPORT_PATH = HERE.parents[1] / "examples" / "io-contract" / "report-sample.json"


class EngineReportWriterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = REPORT_PATH.read_bytes()
        cls.prepared = writer.prepare_report(
            cls.raw,
            simulator_build="test-build-abc123",
            venue="synthetic-fixture",
            symbol="TEST",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report-sample.json",
        )

    def test_reads_actual_fixture_report_contract_and_checksums(self):
        report = json.loads(self.raw)
        self.assertEqual(self.prepared.report_sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.prepared.fixture_sha256, report["manifest"]["fixture_sha256"])
        self.assertEqual(self.prepared.config_sha256, report["manifest"]["config_sha256"])
        self.assertEqual(self.prepared.event_count, 5)
        self.assertEqual(self.prepared.venue, "synthetic-fixture")
        self.assertEqual(self.prepared.symbol, "TEST")
        self.assertEqual(self.prepared.run_status, "complete")

    def test_run_key_is_stable_for_fixture_config_and_build(self):
        again = writer.prepare_report(
            self.raw,
            simulator_build="test-build-abc123",
            venue="synthetic-fixture",
            symbol="TEST",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report-sample.json",
        )
        self.assertEqual(self.prepared.run_key, again.run_key)
        changed_build = writer.prepare_report(
            self.raw,
            simulator_build="test-build-different",
            venue="synthetic-fixture",
            symbol="TEST",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report-sample.json",
        )
        self.assertNotEqual(self.prepared.run_key, changed_build.run_key)

    def test_scalar_metrics_preserve_modes_and_units(self):
        indexed = {(m.output_kind, m.liquidity_mode, m.metric_name): m for m in self.prepared.metrics}
        fees = indexed[("liquidity_mode", "optimistic", "modes.fees")]
        self.assertEqual(fees.metric_value, 169488000)
        self.assertEqual(fees.unit, "money_units_1e-8")
        best_bid = indexed[("liquidity_mode", "optimistic", "modes.book_best_bid")]
        self.assertEqual(best_bid.metric_value, 847440500)
        self.assertEqual(best_bid.unit, "price_ticks_1e-4")
        self.assertEqual(indexed[("replay", "", "events")].metric_value, 5)
        self.assertNotIn("Binance", self.prepared.venue)

    def test_quality_failure_is_a_rejected_run_not_dropped(self):
        report = json.loads(self.raw)
        report["chain_gaps"] = 1
        prepared = writer.prepare_report(
            json.dumps(report, separators=(",", ":")).encode(),
            simulator_build="test-build-abc123",
            venue="synthetic-fixture",
            symbol="TEST",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report-rejected.json",
        )
        self.assertEqual(prepared.run_status, "rejected")
        self.assertEqual(prepared.chain_gaps, 1)

    def test_manifest_quality_caveat_survives_successful_structural_replay(self):
        report = json.loads(self.raw)
        report["manifest"]["quality"] = "healthy_capture_suspect_for_fifo"
        prepared = writer.prepare_report(
            json.dumps(report, separators=(",", ":")).encode(),
            simulator_build="test-build-abc123",
            venue="hyperliquid-perps",
            symbol="BTC",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report-limited.json",
        )
        self.assertEqual(prepared.run_status, "complete")
        self.assertEqual(prepared.metadata["quality"], "healthy_capture_suspect_for_fifo")

    def test_binance_is_rejected_and_report_uri_is_required(self):
        args = dict(
            simulator_build="test-build-abc123",
            symbol="BTCUSDT",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/report.json",
        )
        with self.assertRaisesRegex(ValueError, "Binance"):
            writer.prepare_report(self.raw, venue="binance-futures", **args)
        with self.assertRaisesRegex(ValueError, "report_uri"):
            writer.prepare_report(
                self.raw,
                simulator_build="test-build-abc123",
                venue="synthetic-fixture",
                symbol="TEST",
                report_uri="",
            )

    def test_rejects_incomplete_or_invalid_provenance(self):
        report = json.loads(self.raw)
        report["manifest"]["fixture_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "fixture_sha256"):
            writer.prepare_report(
                json.dumps(report).encode(),
                simulator_build="build",
                venue="synthetic-fixture",
                symbol="TEST",
                report_uri="snowflake://artifact",
            )

    def test_missing_manifest_config_uses_explicit_execution_config_json(self):
        report = json.loads(self.raw)
        report["manifest"].pop("config_sha256")
        report["manifest"].pop("source_hashes")
        report["manifest"]["source_sha256"] = "a" * 64
        encoded = json.dumps(report).encode()
        execution_config = {"decision_latency_ns": 25000000, "fee_bps": 4}
        prepared = writer.prepare_report(
            encoded,
            simulator_build="test-build-abc123",
            venue="hyperliquid-perps",
            symbol="BTC",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/hl-report.json",
            execution_config_json=execution_config,
        )
        expected_hash = hashlib.sha256(
            json.dumps(execution_config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        self.assertEqual(prepared.config_sha256, expected_hash)
        self.assertEqual(prepared.metadata["config_hash_source"], "explicit_execution_config_json")
        self.assertEqual(prepared.source_hashes, ["a" * 64])
        self.assertNotEqual(prepared.run_key, self.prepared.run_key)

    def test_explicit_execution_hash_is_validated_and_changes_run_identity(self):
        report = json.loads(self.raw)
        report["manifest"].pop("config_sha256")
        encoded = json.dumps(report).encode()
        override = "b" * 64
        prepared = writer.prepare_report(
            encoded,
            simulator_build="test-build-abc123",
            venue="hyperliquid-perps",
            symbol="BTC",
            report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/hl-report.json",
            execution_config_sha256=override,
        )
        self.assertEqual(prepared.config_sha256, override)
        self.assertEqual(prepared.metadata["config_hash_source"], "explicit_execution_config_sha256")
        with self.assertRaisesRegex(ValueError, "execution_config_sha256"):
            writer.prepare_report(
                encoded,
                simulator_build="test-build-abc123",
                venue="hyperliquid-perps",
                symbol="BTC",
                report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/hl-report.json",
                execution_config_sha256="not-a-hash",
            )

    def test_missing_execution_config_requires_explicit_override(self):
        report = json.loads(self.raw)
        report["manifest"].pop("config_sha256")
        with self.assertRaisesRegex(ValueError, "manifest.config_sha256 or explicit execution config override"):
            writer.prepare_report(
                json.dumps(report).encode(),
                simulator_build="test-build-abc123",
                venue="hyperliquid-perps",
                symbol="BTC",
                report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/hl-report.json",
            )

    def test_invalid_execution_config_json_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            writer.prepare_report(
                self.raw,
                simulator_build="test-build-abc123",
                venue="hyperliquid-perps",
                symbol="BTC",
                report_uri="snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/hl-report.json",
                execution_config_json="{bad json",
            )


if __name__ == "__main__":
    unittest.main()
