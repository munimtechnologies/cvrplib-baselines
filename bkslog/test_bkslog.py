# Tests for bkslog.py on made-up pages shaped like CVRPLib's updates page. Every expected value is worked by hand.
# MV2 of Munim, Inc. - Apache-2.0 license. Made with AI agents working in MV2's name.
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bkslog as bl  # noqa: E402

PAGE1 = """<html><head><style>p{color:red}</style><script>var x = "XL-n1-k1 (5)";</script></head><body>
<nav><a href="?page=2">2</a></nav>
<article><h3><strong>October 30, 2026</strong></h3><div class="by">by CVRPLib</div>
<p>One improved solution reported by Ana B&oacute;n (Uni A): <strong>XL-n2961-k55 (107,934)</strong>.
Report by Ana, using a modified HGS.</p>
<p>Two improved solutions reported by Team&nbsp;C: <strong>XL-n5288-k1246 (1,957,944)</strong>
and <b>XL-n10001-k1570 (2,329,417)</b> using AILS.</p></article>
<article><h3>October 29, 2026 by CVRPLib</h3>
<p>One improved solution reported by Ana B&oacute;n (Uni A): <strong>XL-n2961-k55 (107,936)</strong>.</p>
<p>A classic one: <strong>X-n1001-k43 (72,355)</strong>.</p></article>
</body></html>"""

PAGE2 = """<html><body>
<article><h3>September 10, 2026</h3><p>One improved solution reported by D: <strong>XL-n2354-k631 (940,632)</strong>.</p>
<p>One improved solution reported by D: <strong>XL-n5288-k1246 (1,958,000)</strong>.</p></article>
<article><h3>March 2, 2026</h3><p>Reported by E: <strong>XL-n2961-k55 (107,950)</strong> and again
<strong>XL-n2961-k55 (107,936)</strong>.</p>
<p>Repeated paragraph reported by D: <strong>XL-n2354-k631 (940,632)</strong>.</p></article>
<article><h3>February 1, 2026</h3><p>During the challenge, reported by F: <strong>XL-n7000-k10 (5,000)</strong>.</p>
</article></body></html>"""


class TestParse(unittest.TestCase):
    def test_text_lines_drop_script_and_join_inline(self):
        lines = bl.text_lines(PAGE1)
        self.assertNotIn('var x', '\n'.join(lines))
        self.assertTrue(any(x.startswith('One improved solution reported by Ana Bón (Uni A): XL-n2961-k55 (107,934)')
                            for x in lines))

    def test_page1(self):
        recs = bl.parse(PAGE1, 1)
        self.assertEqual([(r['date'], r['instance'], r['value']) for r in recs], [
            ('2026-10-30', 'XL-n2961-k55', 107934),
            ('2026-10-30', 'XL-n5288-k1246', 1957944),
            ('2026-10-30', 'XL-n10001-k1570', 2329417),
            ('2026-10-29', 'XL-n2961-k55', 107936),
            ('2026-10-29', 'X-n1001-k43', 72355),
        ])
        self.assertEqual(recs[0]['credit'], 'Ana Bón (Uni A)')
        self.assertEqual(recs[1]['credit'], 'Team C')
        self.assertEqual(recs[2]['credit'], 'Team C')
        self.assertEqual(recs[4]['credit'], 'Ana Bón (Uni A)')   # carried within the entry
        recs2 = bl.parse(PAGE2, 2)
        self.assertEqual([r['credit'] for r in recs2], ['D', 'D', 'E', 'E', 'D', 'F'])
        self.assertEqual(bl.parse('<h3>May 5, 2026</h3><p>reported by Z: x</p><h3>May 4, 2026</h3>'
                                  '<p>XL-n1000-k5 (9)</p>')[0]['credit'], '')   # reset at each date header
        self.assertEqual((recs[2]['n'], recs[2]['k']), (10001, 1570))
        self.assertEqual(bl.dates_on(PAGE1), 2)

    def test_date_with_byline_and_no_date_prose(self):
        self.assertTrue(bl.DATE.match('October 29, 2026 by CVRPLib'))
        self.assertTrue(bl.DATE.match('October 29, 2026'))
        self.assertFalse(bl.DATE.match('October 29, 2026 was a good day'))

    def test_decimal_value(self):
        recs = bl.parse('<h3>May 5, 2026</h3><p>reported by Z: <b>XL-n1000-k5 (1,234.5)</b></p>')
        self.assertEqual(recs[0]['value'], 1234.5)

    def test_nothing_before_first_date(self):
        self.assertEqual(bl.parse('<p>XL-n1000-k5 (99)</p><h3>May 5, 2026</h3>'), [])


class TestAnalysis(unittest.TestCase):
    def rows(self):
        return bl.dedup(bl.parse(PAGE1, 1) + bl.parse(PAGE2, 2))

    def test_dedup_keeps_earliest(self):
        rows = self.rows()
        # PAGE1 5 + PAGE2 6 = 11 raw pairs; (XL-n2961-k55, 107936) and (XL-n2354-k631, 940632) appear twice -> 9
        self.assertEqual(len(bl.parse(PAGE1, 1) + bl.parse(PAGE2, 2)), 11)
        self.assertEqual(len(rows), 9)
        d = {(r['instance'], r['value']): r['date'] for r in rows}
        self.assertEqual(d[('XL-n2961-k55', 107936)], '2026-03-02')
        self.assertEqual(d[('XL-n2354-k631', 940632)], '2026-03-02')

    def test_monotone(self):
        xl = [r for r in self.rows() if r['instance'].startswith('XL-')]
        pairs, down, bad = bl.monotone(xl)
        # XL-n2961-k55: 03-02 (107950, 107936 same day: skipped pair), then 10-30 107934 -> sorted by date then
        # value desc: [03-02 107950, 03-02 107936, 10-30 107934] -> one cross-date pair, down.
        # XL-n5288-k1246: 09-10 1958000 -> 10-30 1957944: down. Others single. pairs 2, down 2.
        self.assertEqual((pairs, down, bad), (2, 2, []))

    def test_monotone_flags_rise(self):
        rows = [{'instance': 'XL-a', 'date': '2026-03-01', 'value': 10},
                {'instance': 'XL-a', 'date': '2026-04-01', 'value': 11}]
        pairs, down, bad = bl.monotone(rows)
        self.assertEqual((pairs, down, len(bad)), (1, 0, 1))

    def test_predictions(self):
        p = bl.predictions(self.rows())
        self.assertTrue(p['B1']['held'])
        # period 02-12..09-30: XL-n2354-k631 (03-02... earliest kept), XL-n2961-k55 x2 (03-02), XL-n5288 (09-10)
        self.assertEqual(p['B2']['instances'], ['XL-n2354-k631', 'XL-n2961-k55', 'XL-n5288-k1246'])
        self.assertFalse(p['B2']['held'])
        self.assertEqual((p['B3']['reports'], p['B3']['reports_n_ge_5000']), (4, 1))
        self.assertFalse(p['B3']['held'])

    def test_bands(self):
        self.assertEqual(bl.band(1000), '1000-2499')
        self.assertEqual(bl.band(4999), '2500-4999')
        self.assertEqual(bl.band(10001), '7500-10001')

    def test_run_from_saved_pages(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'html')
            os.makedirs(src)
            for i, h in enumerate((PAGE1, PAGE2), 1):
                with open(os.path.join(src, f'page-{i}.html'), 'w', encoding='utf-8') as f:
                    f.write(h)
            out = os.path.join(d, 'out')
            s = bl.main(['--out', out, '--html-dir', src])
            self.assertEqual((s['records_raw'], s['records'], s['x_records'], s['xl_records']), (11, 9, 1, 8))
            self.assertEqual(s['xl_instances'], 5)
            self.assertEqual((s['first_date'], s['last_date']), ('2026-02-01', '2026-10-30'))
            self.assertEqual(s['pages'], [{'page': 1, 'dated_entries': 2, 'pairs': 5},
                                          {'page': 2, 'dated_entries': 3, 'pairs': 6}])
            with open(os.path.join(out, 'per_instance.csv'), encoding='utf-8') as f:
                per = {r['instance']: r for r in csv.DictReader(f)}
            self.assertEqual(per['XL-n2961-k55']['reports'], '3')
            self.assertEqual(per['XL-n2961-k55']['max_value'], '107950')
            self.assertEqual(per['XL-n2961-k55']['min_value'], '107934')
            with open(os.path.join(out, 'summary.json'), encoding='utf-8') as f:
                self.assertIn('B3', json.load(f)['predictions'])


if __name__ == '__main__':
    unittest.main()
