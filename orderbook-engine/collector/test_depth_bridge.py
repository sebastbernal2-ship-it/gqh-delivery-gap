#!/usr/bin/env python3
import gzip
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import binance_depth_collector as collector

SLICE = Path(__file__).parent / "data" / "oci-slice"


def update(first_id, final_id, previous_id):
    return {"U": first_id, "u": final_id, "pu": previous_id}


class DepthBridgeTest(unittest.TestCase):
    def test_accepts_a_bridging_update_and_advances(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(101, 110, 100), "accept")
        self.assertEqual(bridge.current, 110)
        self.assertEqual(bridge.apply(111, 120, 110), "accept")
        self.assertEqual(bridge.current, 120)

    def test_accepts_an_update_that_spans_the_snapshot(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(95, 105, 94), "accept")
        self.assertEqual(bridge.current, 105)

    def test_supersedes_updates_before_the_snapshot(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(90, 95, 89), "before")
        self.assertEqual(bridge.current, 100)

    def test_reports_a_bootstrap_gap(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(120, 130, 119), "gap")

    def test_reports_a_live_gap(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(101, 110, 100), "accept")
        self.assertEqual(bridge.apply(112, 120, 111), "gap")

    def test_reset_starts_a_new_chain(self):
        bridge = collector.DepthBridge()
        bridge.reset(100)
        self.assertEqual(bridge.apply(101, 110, 100), "accept")
        bridge.reset(2000)
        self.assertEqual(bridge.apply(1500, 1800, 1499), "before")
        self.assertEqual(bridge.apply(2001, 2010, 2000), "accept")

    def test_window_segments_are_stable_inside_a_window(self):
        base = datetime(2026, 10, 3, 21, 55, tzinfo=timezone.utc)
        inside = datetime(2026, 10, 3, 21, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 10, 3, 22, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(collector.window_segment(base), collector.window_segment(inside))
        self.assertNotEqual(collector.window_segment(base), collector.window_segment(after))


@unittest.skipUnless(SLICE.exists(), "OCI capture slice is not present")
class RealCaptureReplayTest(unittest.TestCase):
    def updates(self):
        candidates = sorted(
            path for path in SLICE.glob("btcusdt-*.jsonl.gz") if "trades" not in path.name
        )
        self.assertTrue(candidates, "no depth slice found")
        path = candidates[0]
        records = []
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                payload = json.loads(line.split(" ", 1)[1])
                data = payload["data"]
                if data.get("e") == "depthUpdate":
                    records.append(data)
        self.assertGreater(len(records), 1000)
        return records

    def test_real_stream_bridges_from_a_snapshot_and_survives_refresh(self):
        records = self.updates()
        middle = len(records) // 2
        bridge = collector.DepthBridge()
        # Epoch one: the snapshot is fetched while messages buffer, so its last
        # update id sits just before the stream head.
        bridge.reset(int(records[0]["U"]) - 1)
        for data in records[:middle]:
            self.assertEqual(
                bridge.apply(int(data["U"]), int(data["u"]), int(data["pu"])),
                "accept",
            )
        # Epoch two: a refresh snapshot computed during a new buffer lands inside
        # one buffered message's id range, so that message bridges it.
        span = records[middle]
        bridge.reset(int(span["u"]) - 100)
        before = 0
        for data in records[middle:]:
            decision = bridge.apply(int(data["U"]), int(data["u"]), int(data["pu"]))
            if decision == "before":
                before += 1
            else:
                self.assertEqual(decision, "accept", f"unexpected {decision}")
        self.assertEqual(before, 0)

    def test_head_level_snapshot_accepts_the_chain_continuing_update(self):
        # A snapshot taken exactly at the live head is still usable, because the
        # next update continues the chain with pu equal to the snapshot id.
        records = self.updates()
        middle = len(records) // 2
        bridge = collector.DepthBridge()
        bridge.reset(int(records[middle]["u"]))
        self.assertEqual(
            bridge.apply(
                int(records[middle + 1]["U"]),
                int(records[middle + 1]["u"]),
                int(records[middle + 1]["pu"]),
            ),
            "accept",
        )

    def test_skipping_an_update_reports_a_gap(self):
        records = self.updates()
        bridge = collector.DepthBridge()
        bridge.reset(int(records[0]["U"]) - 1)
        self.assertEqual(bridge.apply(int(records[0]["U"]), int(records[0]["u"]), int(records[0]["pu"])), "accept")
        skipped = records[1]
        following = records[2]
        self.assertEqual(
            bridge.apply(int(following["U"]), int(following["u"]), int(following["pu"])),
            "gap",
        )
        self.assertNotEqual(int(skipped["u"]), bridge.current)


if __name__ == "__main__":
    unittest.main()
