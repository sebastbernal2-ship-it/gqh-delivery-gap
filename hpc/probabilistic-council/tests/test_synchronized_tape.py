"""Adversarial clock, identity, book-state and future-message tests; no market outcomes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synchronized_tape import CausalTape, NS, audit, clock, digest, parse_messages, summarize

START = 1765199520 * NS
SHA = 'a' * 64


def book_message(event, receipt=None, price=100):
    levels = [[{'px': str(price-j/1000), 'sz':'2'} for j in range(1,6)],
              [{'px': str(price+j/1000), 'sz':'3'} for j in range(1,6)]]
    data = {'coin':'BTC', 'time':event//1_000_000, 'levels':levels}
    return 0, receipt if receipt is not None else event, 'BTC', json.dumps({'channel':'l2Book','data':data})


def trade_message(event, receipt=None, tid=1, size='2', side='B'):
    data = {'coin':'BTC', 'time':event//1_000_000, 'tid':tid, 'px':'100', 'sz':size, 'side':side,
            'users':['do-not-retain'], 'hash':'do-not-retain'}
    return 0, receipt if receipt is not None else event, 'BTC', json.dumps({'channel':'trades','data':[data]})


def history():
    books, _ = parse_messages([book_message(START+i*NS) for i in range(81)], 'books', SHA)
    return books


class SynchronizedTapeTests(unittest.TestCase):
    def test_clocks_are_exact_declared_units(self):
        self.assertEqual(clock(START//1_000_000, 1_000_000), START)
        for x in (float(START), START//1_000_000, True):
            with self.assertRaises(ValueError): clock(x, 1)
        with self.assertRaisesRegex(ValueError, 'later'):
            parse_messages([book_message(START+NS,START)], 'books', SHA)

    def test_trade_identity_uses_time_and_tid_and_removes_accounts(self):
        rows=[trade_message(START), trade_message(START,START+NS), trade_message(START+2*NS)]
        events, counts = parse_messages(rows, 'trades', SHA)
        self.assertEqual(len(events),2)
        self.assertEqual(counts['exact_retransmissions'],1)
        self.assertEqual(events[0].recorded_ns, START)
        self.assertNotIn('do-not-retain',repr(events))
        with self.assertRaisesRegex(ValueError,'conflicting'):
            parse_messages(rows+[trade_message(START,size='3')], 'trades', SHA)

    def test_conflicting_book_duplicate_fails(self):
        with self.assertRaisesRegex(ValueError,'conflicting'):
            parse_messages([book_message(START),book_message(START,price=101)],'books',SHA)
        events,counts=parse_messages([book_message(START),book_message(START,START+NS)],'books',SHA)
        self.assertEqual(len(events),1)
        self.assertEqual(counts['exact_retransmissions'],1)

    def test_invalid_book_and_trade_contracts_fail(self):
        for size,side in [('NaN','B'),('-1','B'),('1','buy')]:
            with self.assertRaises(ValueError):parse_messages([trade_message(START,size=size,side=side)],'trades',SHA)
        row=list(book_message(START));data=json.loads(row[3]);data['data']['levels'][0][0]['px']='101';row[3]=json.dumps(data)
        with self.assertRaisesRegex(ValueError,'crossed'):parse_messages([row],'books',SHA)
        data['data']['coin']='ETH';row[3]=json.dumps(data)
        with self.assertRaisesRegex(ValueError,'coin mismatch'):parse_messages([row],'books',SHA)

    def test_future_arrival_does_not_enter_past_flow(self):
        decision=START+40*NS
        # Venue event was already executed, but its message has not arrived yet.
        delayed,_=parse_messages([trade_message(START+35*NS,START+45*NS,size='200')],'trades',SHA)
        before=CausalTape(history(),[]).features_at(decision)
        after=CausalTape(history(),delayed).features_at(decision)
        self.assertEqual(before,after)
        self.assertEqual(CausalTape(history(),delayed).features_at(START+46*NS)['observed_trade_count'],1)

    def test_future_prices_do_not_change_past_features(self):
        decision=START+40*NS
        before=CausalTape(history(),[]).features_at(decision)
        changed,_=parse_messages([book_message(START+i*NS,price=100 if i<=40 else 110) for i in range(81)],'books',SHA)
        self.assertEqual(before,CausalTape(changed,[]).features_at(decision))

    def test_old_late_book_cannot_rewind_current_state(self):
        books=history()
        delayed,_=parse_messages([book_message(START+35*NS,START+40*NS,price=90)],'books',SHA)
        self.assertEqual(CausalTape(books+delayed,[]).book_at(START+40*NS).event_ns,START+40*NS)

    def test_staleness_and_gap_fail_instead_of_forward_fill(self):
        with self.assertRaisesRegex(ValueError,'stale'):
            CausalTape(history()[:20],[]).features_at(START+40*NS)
        books=history();books=books[:20]+books[24:]
        with self.assertRaisesRegex(ValueError,'history gap'):
            CausalTape(books,[]).features_at(START+40*NS)

    def test_observed_window_excludes_old_initial_snapshot_trades(self):
        trades,_=parse_messages([trade_message(START,START+39*NS),trade_message(START+39*NS,tid=2)],'trades',SHA)
        state=CausalTape(history(),trades).features_at(START+40*NS)
        self.assertEqual(state['observed_trade_count'],1)
        self.assertEqual(state['features'][2],1)
        stats=summarize(trades)
        self.assertEqual(stats['recorded_minus_event_ns']['max'],39*NS)

    def test_audit_rejects_short_overlap_and_keeps_receipt_aggregate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            files=[]
            for kind in ('books','trades'):
                source=root/kind;source.write_bytes(kind.encode());sha=digest(source);source.rename(root/sha)
                files.append({'kind':kind,'size':len(kind),'sha256':sha})
            plan=root/'plan.json';plan.write_text(json.dumps({'files':files}))
            rows={files[0]['sha256']:[book_message(START+i*NS) for i in range(81)],
                  files[1]['sha256']:[trade_message(START+i*NS,tid=i) for i in range(81)]}
            with patch('synchronized_tape.parquet_rows',side_effect=lambda p:rows[p.name]):
                receipt=audit(plan,root,root/'output')
            self.assertFalse(receipt['panel_candidate_ready'])
            self.assertFalse(receipt['training_run_performed'])
            self.assertGreater(receipt['causal_states'],0)
            self.assertNotIn('do-not-retain',json.dumps(receipt))
            self.assertNotIn('price',json.dumps(receipt['summaries']))
            self.assertEqual(receipt['states_sha256'],digest(root/'output/states.jsonl'))
            source=root/files[0]['sha256'];source.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'pinned publisher'):
                audit(plan,root,root/'bad')
            self.assertFalse((root/'bad').exists())


if __name__ == '__main__':unittest.main()
