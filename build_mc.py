#!/usr/bin/env python3
"""Build mc_table.json: character -> Qieyun phonological positions (音韻地位).

Source data: rhyme_book.csv shipped inside the `qieyun` PyPI wheel (nk2028).
We read the CSV directly instead of importing the package (it pins an old
networkx that breaks on NumPy 2).

    pip download qieyun --no-deps -d /tmp/q && pip install opencc
    python build_mc.py --wheel /tmp/q/qieyun-*.whl

Output keys:
  readings : char -> sorted list of 最簡描述 strings, e.g. "心一東入"
             indexed under the traditional form AND its OpenCC t2s form,
             because the corpus mixes both scripts.
  t2s      : per-character traditional->simplified map (only where different),
             so yiming.py needs no OpenCC at runtime.
"""
import argparse, csv, io, json, re, zipfile, glob, sys
from collections import defaultdict

MU = '幫滂並明端透定泥知徹澄孃精清從心邪莊初崇生俟章昌常書船見溪羣疑影曉匣云以來日'
PAT = re.compile(rf'^([{MU}])(開|合)?([一二三四])?([AB])?(.)([平上去入])$')

# Graphic variants the rhyme books use where modern texts use another form.
MANUAL_ALIAS = {'䍐': '罕'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wheel', required=True, help='path to qieyun-*.whl')
    ap.add_argument('-o', '--out', default='mc_table.json')
    a = ap.parse_args()

    whl = sorted(glob.glob(a.wheel))[-1]
    with zipfile.ZipFile(whl) as z:
        name = next(n for n in z.namelist() if n.endswith('rhyme_book.csv'))
        text = z.read(name).decode('utf-8')

    try:
        import opencc
        t2s = opencc.OpenCC('t2s').convert
    except ImportError:
        sys.exit('pip install opencc  (needed at build time only)')

    s2t = opencc.OpenCC('s2t').convert

    orig = defaultdict(set)
    bad = 0
    for r in csv.DictReader(io.StringIO(text)):
        d = r['最簡描述']
        if not PAT.match(d):
            bad += 1
            continue
        ch = r['字頭'] or r['字頭覈校前']
        if len(ch) != 1:
            continue
        orig[MANUAL_ALIAS.get(ch, ch)].add(d)

    # A simplified character takes the readings of its standard traditional
    # form (敌 -> 敵), NOT its own rhyme-book entry: many simplified shapes
    # coincide with unrelated archaic characters (廣韻 has a separate 敌 read
    # like 刮), and those readings would poison the match.
    readings = {}
    for c in set(orig) | {chr(cp) for cp in range(0x4E00, 0xA000)}:
        t = s2t(c)
        if len(t) == 1 and t != c and t in orig:
            readings[c] = orig[t]
        elif c in orig:
            readings[c] = orig[c]

    # per-char t2s map over the CJK blocks the corpus actually uses
    t2s_map = {}
    for lo, hi in [(0x3400, 0x4DBF), (0x4E00, 0x9FFF)]:
        for cp in range(lo, hi + 1):
            c = chr(cp)
            s = t2s(c)
            if len(s) == 1 and s != c:
                t2s_map[c] = s

    s2t_map = {}
    for lo, hi in [(0x3400, 0x4DBF), (0x4E00, 0x9FFF)]:
        for cp in range(lo, hi + 1):
            c = chr(cp)
            t = s2t(c)
            if len(t) == 1 and t != c:
                s2t_map[c] = t
    out = {'readings': {k: sorted(v) for k, v in sorted(readings.items())},
           't2s': t2s_map, 's2t': s2t_map,
           'source': whl.split('/')[-1]}
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(out["readings"])} chars, {len(t2s_map)} t2s entries, {bad} unparsed rows -> {a.out}')


if __name__ == '__main__':
    main()
