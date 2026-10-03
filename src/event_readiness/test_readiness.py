"""Adversarial contract tests using synthetic bytes and no remote connections."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from event_readiness.archive import canonical_hash, digest_file, reconcile, stage_key
from event_readiness.collect import collect, reconcile_sources, QUERIES
from event_readiness.features import Fact, build_features, next_session_close, exact
from event_readiness.run import fixture, main, read_json


class Features(unittest.TestCase):
    def setUp(self):
        self.facts, self.documents = fixture()

    def build(self):
        return build_features(self.facts, self.documents)

    def reason(self, fact_id, reason):
        row = next(r for r in self.build()["exclusions"] if r["fact_id"] == fact_id)
        self.assertIn(reason, row["reasons"])

    def test_exact_revision_and_source_hash(self):
        out = self.build()
        self.assertFalse(out["strategy_ready"])
        self.assertEqual(len(out["features"]), 2)
        self.assertEqual(out["features"][0]["revision_abs"], "10.000000000001")
        self.assertEqual(out["features"][1]["n_prior_events"], 1)
        self.assertIsNone(out["features"][1]["past_mad_z"])
        self.assertEqual(out["features"][1]["history_fact_ids"], ["synthetic-1"])
        self.assertNotIn("raw_return", out["features"][0])

    def test_missing_prior_is_excluded(self):
        self.reason("synthetic-0", "no_comparable_prior_expectation")

    def test_unknown_label_column_fails(self):
        self.facts[1]["future_return"] = "0.9"
        with self.assertRaises(ValueError):
            self.build()

    def test_source_bytes_and_exact_quote_are_required(self):
        digest = self.facts[1]["document_sha256"]
        self.documents[digest] = b"tampered"
        self.reason("synthetic-1", "document_hash_mismatch")
        self.reason("synthetic-2", "prior_document_hash_mismatch")

    def test_span_must_match_even_with_correct_document_hash(self):
        self.facts[1]["source_span_start"] = 1
        self.reason("synthetic-1", "source_span_mismatch")

    def test_unreviewed_and_ambiguous_exposure_abstain(self):
        self.facts[1]["review_status"] = "unreviewed"
        self.facts[1]["exposure_status"] = "ambiguous"
        self.reason("synthetic-1", "human_review_missing")
        self.reason("synthetic-1", "exposure_not_verified")

    def test_unit_scope_target_definition_and_security_mismatch(self):
        for name in ("unit", "scope", "target_period", "definition_version", "security_id", "comparability_group"):
            with self.subTest(field=name):
                original = self.facts[1][name]
                self.facts[1][name] = "changed"
                self.reason("synthetic-1", "expectation_definition_scope_or_target_mismatch")
                self.facts[1][name] = original

    def test_balances_are_not_management_guidance(self):
        self.facts[0]["fact_kind"] = self.facts[1]["fact_kind"] = "backlog_balance"
        self.reason("synthetic-1", "unsupported_expectation_family")

    def test_future_expectation_is_forbidden(self):
        self.facts[1]["expectation_id"] = "synthetic-2"
        self.reason("synthetic-1", "expectation_not_strictly_earlier")

    def test_skipping_intermediate_guidance_is_forbidden(self):
        self.facts[2]["expectation_id"] = "synthetic-0"
        self.reason("synthetic-2", "prior_expectation_superseded")

    def test_future_in_window_does_not_change_prior_features(self):
        before = build_features(self.facts[:2], self.documents)["features"]
        after = self.build()["features"][:1]
        self.assertEqual(before, after)

    def test_sealed_adversary_is_fenced_before_numeric_parsing(self):
        before = self.build()["features"]
        self.facts.append({"publication_basis": "verified_public_time", "published_at": "2023-01-01T00:00:00Z",
                           "value_decimal": "THIS IS NOT A NUMBER", "future_return": "lookahead"})
        after = self.build()
        self.assertEqual(after["features"], before)
        self.assertEqual(after["fenced_rows"], 1)

    def test_naive_timestamp_and_retrieval_clock_rejected(self):
        self.facts[1]["published_at"] = "2021-02-05T21:05:00"
        with self.assertRaises(ValueError):
            self.build()
        self.facts[1]["publication_basis"] = "retrieved_at"
        with self.assertRaises(ValueError):
            self.build()

    def test_date_upper_bound_observes_dst(self):
        f = dict(self.facts[1], publication_basis="date_upper_bound", published_at="2021-03-14")
        self.assertEqual(Fact.from_dict(f).available_at().isoformat(), "2021-03-15T04:00:00+00:00")

    def test_equivalent_timezone_times_do_not_change_output(self):
        before = self.build()["features"][0]["available_at_utc"]
        self.facts[1]["published_at"] = "2021-02-05T16:05:00-05:00"
        self.assertEqual(before, self.build()["features"][0]["available_at_utc"])

    def test_decimal_binary_float_nonfinite_and_overflow_rejected(self):
        for value in (0.1, "NaN", "Infinity", "1e26", "0.0000000000001"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                exact(value)

    def test_zero_negative_prior_keep_absolute_revision_pct_null(self):
        for value in ("0", "-1"):
            facts, documents = fixture()
            quote = f"SYNTHETIC guidance {value} USD"
            digest = hashlib.sha256(quote.encode()).hexdigest()
            facts[0].update(value_decimal=value, value_text=value, source_quote=quote,
                            source_span_end=len(quote), document_sha256=digest)
            documents[digest] = quote.encode()
            out = build_features(facts, documents)["features"][0]
            self.assertIsNone(out["revision_pct"])
            self.assertEqual(out["revision_pct_null_reason"], "nonpositive_prior")

    def test_duplicate_idempotence_and_conflict(self):
        before = self.build()["features"]
        self.facts.append(dict(self.facts[1]))
        self.assertEqual(before, self.build()["features"])
        self.assertEqual(self.build()["duplicate_rows_removed"], 1)
        self.facts[-1]["value_decimal"] = "555"
        with self.assertRaises(ValueError):
            self.build()

    def test_current_cluster_never_counts_as_independent_history(self):
        self.facts[2]["event_cluster_id"] = self.facts[1]["event_cluster_id"]
        self.assertEqual(self.build()["features"][-1]["n_prior_events"], 0)

    def test_amendment_requires_earlier_same_cluster(self):
        self.facts[2]["supersedes_id"] = "synthetic-1"
        self.reason("synthetic-2", "invalid_amendment_lineage")
        self.facts[2]["event_cluster_id"] = self.facts[1]["event_cluster_id"]
        self.assertEqual(len(self.build()["features"]), 2)

    def test_no_missing_acceptance_needed_for_verified_press_release(self):
        self.assertEqual(len(self.build()["features"]), 2)
        self.assertNotIn("accepted_at", self.facts[1])

    def test_duplicate_accession_metric_with_new_id_rejected(self):
        duplicate = dict(self.facts[1], fact_id="another-extractor-id")
        self.facts.append(duplicate)
        with self.assertRaises(ValueError):
            self.build()

    def test_numeric_source_and_explicit_scale_must_reconcile(self):
        self.facts[1]["value_decimal"] = "999"
        with self.assertRaises(ValueError):
            self.build()
        self.facts, self.documents = fixture()
        self.facts[1]["value_scale_decimal"] = "1000"
        self.facts[1]["value_decimal"] = "110000.000000002"
        self.assertEqual(len(self.build()["features"]), 2)

    def test_same_time_statements_cannot_establish_prior(self):
        self.facts[1]["published_at"] = self.facts[0]["published_at"]
        self.reason("synthetic-1", "expectation_not_strictly_earlier")

    def test_same_accession_is_not_an_earlier_publication(self):
        self.facts[1]["accession"] = self.facts[0]["accession"]
        with self.assertRaises(ValueError):
            self.build()

    def history_fixture(self, values):
        template = self.facts[0]
        facts, documents = [], {}
        for i, value in enumerate(values):
            quote = "SYNTHETIC guidance " + str(value)
            digest = hashlib.sha256(quote.encode()).hexdigest()
            documents[digest] = quote.encode()
            facts.append(dict(template, fact_id=f"h-{i}", event_cluster_id=f"cluster-{i}",
                accession=f"0000000001-21-{i:06d}", published_at=f"2021-{i+1:02d}-05T21:00:00Z",
                reviewed_at="2022-01-01T00:00:00Z", value_text=str(value), value_decimal=str(value),
                source_quote=quote, source_span_end=len(quote), document_sha256=digest,
                expectation_id=f"h-{i-1}" if i else None))
        return facts, documents

    def test_zero_mad_after_minimum_history_stays_null(self):
        facts, documents = self.history_fixture([100, 110, 120, 130, 140, 150, 160])
        row = build_features(facts, documents)["features"][-1]
        self.assertEqual(row["n_prior_events"], 5)
        self.assertIsNone(row["past_mad_z"])
        self.assertEqual(row["normalizer_null_reason"], "zero_mad")

    def test_nonzero_mad_uses_only_prior_clusters(self):
        facts, documents = self.history_fixture([100, 110, 130, 160, 200, 250, 310])
        row = build_features(facts, documents)["features"][-1]
        self.assertEqual(row["revision_vs_past_median"], "30.000000000000")
        self.assertAlmostEqual(float(row["past_mad_z"]), 30 / 14.826, places=10)
        self.assertEqual(len(row["history_lineage"]), 5)

    def test_order_invariance(self):
        before = self.build()
        self.facts.reverse()
        self.assertEqual(before, self.build())


class Sessions(unittest.TestCase):
    def setUp(self):
        self.sessions = [
            {"date": "2021-07-02", "open": "2021-07-02T13:30:00Z", "close": "2021-07-02T20:00:00Z"},
            {"date": "2021-07-06", "open": "2021-07-06T13:30:00Z", "close": "2021-07-06T20:00:00Z"},
            {"date": "2021-11-26", "open": "2021-11-26T14:30:00Z", "close": "2021-11-26T18:00:00Z"}]

    def test_after_close_weekend_and_holiday(self):
        self.assertEqual(next_session_close("2021-07-02T21:00:00Z", self.sessions), "2021-07-06T20:00:00Z")
        self.assertEqual(next_session_close("2021-07-04T21:00:00Z", self.sessions), "2021-07-06T20:00:00Z")

    def test_preopen_still_lags_full_daily_bar(self):
        self.assertEqual(next_session_close("2021-07-02T10:00:00Z", self.sessions), "2021-07-06T20:00:00Z")

    def test_half_day_and_exhausted_calendar(self):
        self.assertEqual(next_session_close("2021-11-25T21:00:00Z", self.sessions), "2021-11-26T18:00:00Z")
        self.assertIsNone(next_session_close("2021-11-26T21:00:00Z", self.sessions))

    def test_reordered_duplicate_or_wrong_timezone_calendar_fails(self):
        with self.assertRaises(ValueError):
            next_session_close("2021-07-01T00:00:00Z", list(reversed(self.sessions)))
        self.sessions[0]["date"] = "2021-07-01"
        with self.assertRaises(ValueError):
            next_session_close("2021-07-01T00:00:00Z", self.sessions)


class Archive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        content = b"synthetic filing"
        self.accession = "0000000001-21-000001"
        document_sha = hashlib.sha256(content).hexdigest()
        package = self.folder / "build.zip"
        with ZipFile(package, "w") as archive:
            archive.writestr("index.json", "{}")
            archive.writestr("documents/release.htm", content)
        self.sha = digest_file(package)
        self.package = self.folder / (self.sha + ".zip")
        package.rename(self.package)
        self.stage = "accession=000000000121000001/000000000121000001.zip"
        manifest = {"accession": self.accession, "package_sha256": self.sha,
                    "package_stage_path": "@VECTOR_RESEARCH.RAW.SEC_FILING_ARCHIVE/" + self.stage,
                    "package_size_bytes": self.package.stat().st_size, "document_count": 1,
                    "documents": [{"name": "release.htm", "sha256": document_sha, "size_bytes": len(content)}]}
        doc = {"accession": self.accession, "package_sha256": self.sha,
               "package_stage_path": manifest["package_stage_path"], "document_name": "release.htm",
               "document_sha256": document_sha, "document_size_bytes": len(content)}
        self.snapshot = {"manifests": [manifest], "documents": [doc],
                         "stage_objects": [{"name": "sec_filing_archive/" + self.stage, "size": 1, "md5": "not-source-hash"}]}

    def report(self, packages=True):
        return reconcile(self.snapshot, [self.accession], self.folder if packages else None)

    def test_end_to_end_bytes_required_and_list_md5_not_source_hash(self):
        self.assertTrue(self.report()["archive_ready"])
        self.assertFalse(self.report(False)["archive_ready"])

    def test_missing_accession_is_explicit(self):
        self.snapshot["manifests"] = []
        report = self.report()
        self.assertEqual(report["missing_accessions"], [self.accession])
        self.assertFalse(report["archive_ready"])
        self.assertIn("orphan_document_version", [p["code"] for p in report["problems"]])

    def test_manifest_and_document_duplicates_fail(self):
        self.snapshot["manifests"].append(deepcopy(self.snapshot["manifests"][0]))
        self.snapshot["documents"].append(deepcopy(self.snapshot["documents"][0]))
        codes = {p["code"] for p in self.report()["problems"]}
        self.assertIn("duplicate_manifest_key", codes)
        self.assertIn("document_table_count_mismatch", codes)

    def test_versioned_manifests_reusing_mutable_object_fail(self):
        second = deepcopy(self.snapshot["manifests"][0])
        second["package_sha256"] = "b" * 64
        self.snapshot["manifests"].append(second)
        self.assertIn("mutable_stage_path_multiple_versions", {p["code"] for p in self.report()["problems"]})

    def test_tampered_bytes_and_missing_stage_fail(self):
        self.package.write_bytes(b"bad")
        self.snapshot["stage_objects"] = []
        codes = {p["code"] for p in self.report()["problems"]}
        self.assertTrue({"package_hash_mismatch", "stage_missing_or_duplicate"} <= codes)

    def test_matching_counts_do_not_hide_wrong_document_hash(self):
        self.snapshot["documents"][0]["document_sha256"] = "c" * 64
        self.assertIn("document_table_content_mismatch", {p["code"] for p in self.report()["problems"]})

    def test_document_bytes_independently_verified(self):
        self.snapshot["manifests"][0]["documents"][0]["sha256"] = "c" * 64
        self.snapshot["documents"][0]["document_sha256"] = "c" * 64
        self.assertIn("document_bytes_mismatch:release.htm", {p["code"] for p in self.report()["problems"]})

    def test_path_traversal_and_wrong_stage_rejected(self):
        for path in ("../x.zip", "@OTHER.STAGE/x.zip", "accession=000000000121000001/../x.zip"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                stage_key(path)

    def test_wrong_accession_path_rejected(self):
        self.snapshot["manifests"][0]["package_stage_path"] = self.snapshot["manifests"][0]["package_stage_path"].replace("121000001", "121000002")
        self.assertIn("path_accession_mismatch", {p["code"] for p in self.report()["problems"]})

    def test_source_batches_not_blended(self):
        snap = {"source_inventory": [{"source_id": "bars", "batch_sha256": "a", "row_count": 20, "distinct_row_index_count": 20}],
                "source_manifests": [{"source_id": "bars", "batch_sha256": "b", "row_count": 20}]}
        self.assertFalse(reconcile_sources(snap)["counts_reconciled"])
        snap["source_manifests"][0]["batch_sha256"] = "a"
        self.assertTrue(reconcile_sources(snap)["counts_reconciled"])
        snap["source_inventory"][0]["distinct_row_index_count"] = 19
        self.assertFalse(reconcile_sources(snap)["counts_reconciled"])

    def test_queries_do_not_read_market_payloads(self):
        self.assertTrue(all(q.strip().upper().startswith("SELECT") for q in QUERIES.values()))
        self.assertFalse(any("PAYLOAD_JSON" in q for q in QUERIES.values()))
        self.assertIn("EIA860M_FILE_MANIFESTS", QUERIES["eia_manifests"])


class Collector(unittest.TestCase):
    def test_readonly_collector_preserves_failures_and_removes_text_contexts(self):
        accession = "0000000001-21-000001"
        class Cursor:
            sfqid = "synthetic-query"
            description = []
            data = []
            queries = []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, sql, params=None):
                self.queries.append(sql)
                assert sql.strip().startswith(("SELECT", "LIST"))
                if "EIA860M_FILE_MANIFESTS" in sql:
                    raise PermissionError("synthetic sensitive error must not enter receipt")
                if "SEC_FILING_PACKAGE_MANIFESTS" in sql:
                    assert params == [accession]
                    self.description = [("DOCUMENTS_JSON",)]
                    self.data = [(json.dumps([{"name":"x", "sha256":"a"*64, "size_bytes":1,
                                               "matched_text_contexts":["PRIVATE TEXT"]}]),)]
                else:
                    self.description, self.data = [], []
                return self
            def fetchall(self):
                return self.data
        class Connection:
            def cursor(self):
                return Cursor()
        out = collect(Connection(), [accession])
        self.assertFalse(out["inventory_complete"])
        self.assertEqual(out["query_failures"], [{"name":"eia_manifests", "error_type":"PermissionError"}])
        self.assertNotIn("PRIVATE TEXT", json.dumps(out))
        self.assertNotIn("sensitive error", json.dumps(out))
        self.assertEqual(len(out["query_receipts"]), 5)


class CLI(unittest.TestCase):
    def test_demo_receipt_and_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "report.json"
            self.assertEqual(main(["demo", "--out", str(target)]), 0)
            value = read_json(target)
            self.assertTrue(value["synthetic"])
            self.assertFalse(value["strategy_ready"])
            self.assertEqual(len(value["features"]), 2)
            self.assertIn("component_sha256", value["run"])
            with self.assertRaises(SystemExit):
                main(["demo", "--out", str(target)])

    def test_features_cli_consumes_exact_private_document_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            facts, documents = fixture()
            for digest, content in documents.items():
                (base / digest).write_bytes(content)
            inputs = base / "facts.json"
            inputs.write_text(json.dumps({"schema_version": 1, "partition": "development", "facts": facts}))
            out = base / "report.json"
            self.assertEqual(main(["features", "--facts", str(inputs), "--documents", str(base), "--out", str(out)]), 0)
            report = read_json(out)
            self.assertFalse(report["synthetic"])
            self.assertEqual(report["features"], build_features(facts, documents)["features"])
            self.assertFalse(report["strategy_ready"])

    def test_duplicate_json_keys_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "bad.json"
            target.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError):
                read_json(target)


if __name__ == "__main__":
    unittest.main()
