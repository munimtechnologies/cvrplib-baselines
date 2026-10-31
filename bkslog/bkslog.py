# Turns CVRPLib's public updates page into a machine-readable log of reported best known solutions (BKS).
# MV2 of Munim, Inc. - Apache-2.0 license. Made with AI agents working in MV2's name.
#
# Reads https://galgos.inf.puc-rio.br/cvrplib/en/updates/?page=N one page at a time, at least 2 s apart, keeps the
# raw HTML, and extracts every "<instance> (<value>)" pair for X/XL CVRP instances with the date of its entry and
# the "reported by ..." credit of its paragraph. Then it scores predictions B1-B3 (bkslog/expectations.md).
import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = 'https://galgos.inf.puc-rio.br/cvrplib/en/updates/?page={}'
UA = 'CVRPLib BKS log (research) - MV2 of Munim, Inc. (mv2@munimtech.com)'
MONTHS = ('January February March April May June July August September October November December').split()
# an entry's date header, alone on its line or followed by its byline ("October 30, 2026 by CVRPLib")
DATE = re.compile(r'^\s*(' + '|'.join(MONTHS) + r')\s+(\d{1,2}),\s*(\d{4})\s*(?:(?:by\b|[-|·–]).*)?$')
PAIR = re.compile(r'\b(XL?-n(\d+)-k(\d+))\s*\(\s*([\d,]+(?:\.\d+)?)\s*\)')
# credit = the last "reported by ...:" seen in the same dated entry (paragraphs can wrap across lines)
CREDIT = re.compile(r'reported by\s+(.+?)\s*:', re.I)
BLOCK = re.compile(r'<\s*/?\s*(p|div|br|h[1-6]|li|ul|ol|tr|td|th|table|section|article|header|footer|hr)\b[^>]*>',
                   re.I)
DROP = re.compile(r'<\s*(script|style)\b.*?<\s*/\s*\1\s*>', re.I | re.S)
TAG = re.compile(r'<[^>]+>')
CHALLENGE_END = '2026-02-11'
PERIOD = ('2026-02-12', '2026-09-30')
BANDS = ((1000, 2499), (2500, 4999), (5000, 7499), (7500, 10001))


def text_lines(page_html):
    """Visible text of one page, one line per block element, inline tags removed."""
    s = DROP.sub(' ', page_html)
    s = BLOCK.sub('\n', s)
    s = TAG.sub('', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return [re.sub(r'[ \t\r\f\v]+', ' ', x).strip() for x in s.split('\n') if x.strip()]


def parse(page_html, page=1):
    """Records (date, instance, n, k, value, credit, page) in page order."""
    out, date, credit = [], None, ''
    for line in text_lines(page_html):
        m = DATE.match(line)
        if m:
            date = dt.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))).isoformat()
            credit = ''
            continue
        c = CREDIT.search(line)
        if c:
            credit = c.group(1).strip()
        if date is None:
            continue
        for p in PAIR.finditer(line):
            v = p.group(4).replace(',', '')
            out.append({'date': date, 'instance': p.group(1), 'n': int(p.group(2)), 'k': int(p.group(3)),
                        'value': float(v) if '.' in v else int(v), 'credit': credit, 'page': page})
    return out


def dates_on(page_html):
    return sum(1 for line in text_lines(page_html) if DATE.match(line))


def dedup(records):
    """One row per (instance, value): the earliest date it was reported, ties in page order."""
    best = {}
    for r in records:
        key = (r['instance'], r['value'])
        if key not in best or r['date'] < best[key]['date']:
            best[key] = r
    return sorted(best.values(), key=lambda r: (r['date'], r['instance'], -float(r['value'])))


def monotone(rows):
    """Consecutive pairs per instance (date order, then value descending within a date) and how many go down."""
    by = {}
    for r in rows:
        by.setdefault(r['instance'], []).append(r)
    pairs = down = 0
    bad = []
    for inst, rs in by.items():
        rs = sorted(rs, key=lambda r: (r['date'], -float(r['value'])))
        for a, b in zip(rs, rs[1:]):
            if a['date'] == b['date']:
                continue
            pairs += 1
            if float(b['value']) < float(a['value']):
                down += 1
            else:
                bad.append({'instance': inst, 'earlier': [a['date'], a['value']], 'later': [b['date'], b['value']]})
    return pairs, down, bad


def band(n):
    for lo, hi in BANDS:
        if lo <= n <= hi:
            return f'{lo}-{hi if hi < 10001 else 10001}'
    return 'other'


def summarise(rows):
    xl = [r for r in rows if r['instance'].startswith('XL-')]
    per = {}
    for r in xl:
        p = per.setdefault(r['instance'], {'instance': r['instance'], 'n': r['n'], 'reports': 0,
                                           'first_date': r['date'], 'last_date': r['date'],
                                           'max_value': r['value'], 'min_value': r['value']})
        p['reports'] += 1
        p['first_date'] = min(p['first_date'], r['date'])
        p['last_date'] = max(p['last_date'], r['date'])
        p['max_value'] = max(p['max_value'], r['value'], key=float)
        p['min_value'] = min(p['min_value'], r['value'], key=float)
    for p in per.values():
        p['drop_within_log_pct'] = round(100 * (float(p['max_value']) - float(p['min_value'])) /
                                         float(p['max_value']), 4)
    months, bands = {}, {}
    for r in xl:
        months[r['date'][:7]] = months.get(r['date'][:7], 0) + 1
        b = bands.setdefault(band(r['n']), {'reports': 0, 'instances': set()})
        b['reports'] += 1
        b['instances'].add(r['instance'])
    bands = {k: {'reports': v['reports'], 'instances': len(v['instances'])} for k, v in sorted(bands.items())}
    return sorted(per.values(), key=lambda p: (p['n'], p['instance'])), dict(sorted(months.items())), bands


def predictions(rows):
    """B1-B3 exactly as written in expectations.md."""
    xl = [r for r in rows if r['instance'].startswith('XL-')]
    pairs, down, bad = monotone(xl)
    b1 = {'pairs': pairs, 'down': down, 'share': round(down / pairs, 4) if pairs else None,
          'held': bool(pairs) and down >= 0.95 * pairs, 'not_down': bad}
    span = [r for r in xl if PERIOD[0] <= r['date'] <= PERIOD[1]]
    distinct = sorted({r['instance'] for r in span})
    b2 = {'period': list(PERIOD), 'distinct_instances': len(distinct), 'instances': distinct,
          'held': len(distinct) >= 25}
    big = sum(1 for r in span if r['n'] >= 5000)
    b3 = {'period': list(PERIOD), 'reports': len(span), 'reports_n_ge_5000': big,
          'share': round(big / len(span), 4) if span else None,
          'held': bool(span) and big >= 0.6 * len(span)}
    return {'B1': b1, 'B2': b2, 'B3': b3}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def write_csv(path, rows, cols):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def run(out, pages_html, fetched_at):
    os.makedirs(out, exist_ok=True)
    records, per_page = [], []
    for i, h in enumerate(pages_html, 1):
        recs = parse(h, i)
        per_page.append({'page': i, 'dated_entries': dates_on(h), 'pairs': len(recs)})
        records += recs
    rows = dedup(records)
    per, months, bands = summarise(rows)
    pred = predictions(rows)
    cols = ['date', 'instance', 'n', 'k', 'value', 'credit', 'page']
    write_csv(os.path.join(out, 'log_raw.csv'), records, cols)
    write_csv(os.path.join(out, 'log.csv'), rows, cols)
    write_csv(os.path.join(out, 'per_instance.csv'), per,
              ['instance', 'n', 'reports', 'first_date', 'last_date', 'max_value', 'min_value',
               'drop_within_log_pct'])
    dates = sorted(r['date'] for r in rows)
    summary = {'fetched_at': fetched_at, 'pages': per_page, 'records_raw': len(records), 'records': len(rows),
               'xl_records': sum(r['instance'].startswith('XL-') for r in rows),
               'x_records': sum(r['instance'].startswith('X-') for r in rows),
               'xl_instances': len(per), 'first_date': dates[0] if dates else None,
               'last_date': dates[-1] if dates else None, 'xl_reports_by_month': months,
               'xl_by_size_band': bands, 'challenge_end': CHALLENGE_END, 'predictions': pred}
    with open(os.path.join(out, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: summary[k] for k in ('records_raw', 'records', 'xl_records', 'xl_instances',
                                              'first_date', 'last_date')}))
    print(json.dumps({k: {'held': v['held']} for k, v in pred.items()}))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description='Machine-readable log of BKS reports on CVRPLib\'s updates page.')
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-pages', type=int, default=30)
    ap.add_argument('--pause', type=float, default=2.0)
    ap.add_argument('--html-dir', help='read saved page-N.html files instead of fetching')
    a = ap.parse_args(argv)
    pages = []
    if a.html_dir:
        i = 1
        while os.path.exists(os.path.join(a.html_dir, f'page-{i}.html')):
            with open(os.path.join(a.html_dir, f'page-{i}.html'), encoding='utf-8') as f:
                pages.append(f.read())
            i += 1
    else:
        raw = os.path.join(a.out, 'raw')
        os.makedirs(raw, exist_ok=True)
        seen = set()
        for i in range(1, a.max_pages + 1):
            if i > 1:
                time.sleep(a.pause)
            h = fetch(BASE.format(i))
            with open(os.path.join(raw, f'page-{i}.html'), 'w', encoding='utf-8') as f:
                f.write(h)
            body = '\n'.join(text_lines(h))
            if dates_on(h) == 0 or body in seen:
                print(f'page {i}: no new dated entries, stopping', file=sys.stderr)
                os.rename(os.path.join(raw, f'page-{i}.html'), os.path.join(raw, f'stop-page-{i}.html'))
                break
            seen.add(body)
            pages.append(h)
    fetched_at = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return run(a.out, pages, fetched_at)


if __name__ == '__main__':
    main()
