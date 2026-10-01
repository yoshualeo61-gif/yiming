#!/usr/bin/env python3
"""yiming (異名) — read Chinese histories with foreign names made visible.

Chinese histories write foreign names in characters: Sogdian Roxšan becomes 禄山,
and the same name gets different spellings (斡亦剌 / 瓦剌). This tool shows the
original-language form above each name, coloured by language family, and
unifies variant spellings. Names are compared by how they sounded when they
were written (Middle Chinese or an Old-Mandarin approximation), not by
modern Mandarin.

  read     FILE_OR_DIR       reading view (the main command)
  find     WORD --corpus DIR which files mention a word (to pick what to read)
  scan     --corpus DIR      index every transcribed name, with origin if known
  propose  --corpus DIR      LLM proposes originals for unknown names; kept only
                             if the sound matches; ordinary words get filtered
  train    --corpus DIR      learn which characters are typical of transcriptions
  key / match                inspect readings; compare two names (or vs Latin)
  twins    --corpus DIR      same-sounding names spelled differently
  eval     gold_pairs.tsv    accuracy of the sound comparison

Other books (corpora.py):
  setup                      one-time data preparation after cloning
  fetch    TITLE_OR_KR_ID    download from Kanripo; dynasty picks the phonology
  guoyujie                   Qianlong respellings from 《三史國語解》
  align    A_DIR B_DIR       diff two editions (中華本 vs 四庫本), collect renamings
  variants                   異體字 -> 正字 table

Corpus layout is the same as huijian: DIR/<書名>/**/*.txt (cleaned) or the raw
hunterhug/china-history HTML. Vernacular translations are skipped.
"""
import argparse, html, itertools, json, random, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')

# ── phonology ────────────────────────────────────────────────────────────────
MU = '幫滂並明端透定泥知徹澄孃精清從心邪莊初崇生俟章昌常書船見溪羣疑影曉匣云以來日'
DESC = re.compile(rf'^([{MU}])(開|合)?([一二三四])?([AB])?(.)([平上去入])$')

# Onset classes. Coarse on purpose: foreign sounds were squeezed into Chinese
# categories, so we compare at the level of "what kind of consonant".
ONSET = {}
for cls, mus in {'P': '幫滂並', 'M': '明', 'T': '端透定知徹澄', 'N': '泥孃',
                 'C': '精清從莊初崇章昌常船', 'S': '心邪生俟書', 'K': '見溪羣',
                 'G': '疑', 'H': '曉匣', 'L': '來', 'J': '日', '': '影云以'}.items():
    for m in mus:
        ONSET[m] = cls

RHYME_NASAL = {r: 'G' for r in '東冬鍾江陽唐庚耕清青蒸登'}
RHYME_NASAL.update({r: 'N' for r in '眞臻文欣元魂痕寒刪山先仙'})
RHYME_NASAL.update({r: 'M' for r in '侵覃談鹽添咸銜嚴凡'})
STOP_OF = {'G': 'K', 'N': 'T', 'M': 'P'}          # -ŋ/-k, -n/-t, -m/-p

VOWEL = {}
for cls, rs in {'A': '歌麻泰佳皆夬灰咍廢寒刪山元談覃咸銜嚴凡唐陽江庚耕肴豪',
                'I': '支脂之微齊祭先仙鹽添清青眞臻欣蒸侵宵蕭登痕',
                'U': '魚虞模東冬鍾尤侯幽文魂'}.items():
    for r in rs:
        VOWEL[r] = cls

SCHEMES = {
    'mc': 'Middle Chinese (切韻): codas -p -t -k kept, 疑 = ŋ-. Use for Han–Tang transcriptions.',
    'om': 'Old Mandarin approx. (Jin/Yuan/Ming): entering codas lost, 疑 → zero, 日 → r. '
          'Use for Khitan, Jurchen, Mongol names.',
    'qm': 'Qing Mandarin approx.: as om, and -m merged into -n. Initials keep the 尖/团 split '
          '(精 vs 見 before i), which Qing transcribers of Manchu and Mongol still observed.',
}


def syllable(desc, scheme):
    """Qieyun description -> (onset, coda, vowel) classes under a scheme."""
    m = DESC.match(desc)
    mu, _, _, _, rhyme, tone = m.groups()
    onset = ONSET[mu]
    nasal = RHYME_NASAL.get(rhyme, '')
    coda = STOP_OF.get(nasal, '') if tone == '入' else nasal
    if scheme in ('om', 'qm'):
        if scheme == 'qm' and coda == 'M':
            coda = 'N'
        if tone == '入':
            coda = ''
        if onset == 'G':
            onset = ''
        if onset == 'J':
            onset = 'R'
    return onset, coda, VOWEL.get(rhyme, '?')


class Phon:
    def __init__(self, table=HERE / 'mc_table.json'):
        d = json.loads(Path(table).read_text(encoding='utf-8'))
        self.readings = d['readings']
        self.t2s_map = d['t2s']
        self.s2t_map = d.get('s2t', {})
        vp = Path(table).with_name('variants.json')     # 異體字 -> 正字 (corpora.py variants)
        self.variant = json.loads(vp.read_text(encoding='utf-8')) if vp.exists() else {}
        try:
            import pypinyin
            self._py = pypinyin
        except ImportError:
            self._py = None

    def t2s(self, s):
        """Normalise for matching: variant shape -> standard, then traditional -> simplified."""
        v, t = self.variant, self.t2s_map
        return ''.join(t.get(v.get(c, c), v.get(c, c)) for c in s)

    def is_traditional(self, text):
        """Does this passage use traditional characters?"""
        trad = sum(1 for c in text if self.t2s_map.get(c, c) != c)
        simp = sum(1 for c in text if c in self.s2t_map)
        return trad > simp

    def to_script(self, word, traditional):
        """Show a canonical name in the script of the passage around it."""
        if traditional:
            return ''.join(self.s2t_map.get(c, c) for c in word)
        return ''.join(self.t2s_map.get(c, c) for c in word)

    def char_sylls(self, ch, scheme):
        """All distinct (onset, coda, vowel) readings for one character.
        Falls back to modern pinyin (marked '~') for chars missing from the
        rhyme books, and to a wildcard '?' if even that fails."""
        descs = (self.readings.get(ch) or self.readings.get(self.variant.get(ch, ''))
                 or self.readings.get(self.t2s(ch)))
        if descs:
            return sorted({syllable(d, scheme) for d in descs}), 'qieyun'
        if self._py:
            out = set()
            for py in self._py.pinyin(ch, style=self._py.Style.NORMAL, heteronym=True)[0]:
                out.add(pinyin_syll(py))
            if out:
                return sorted(out), 'pinyin~'
        return [('?', '', '?')], 'unknown'

    def variants(self, name, scheme, cap=32):
        """Reading combinations for a whole name, deduplicated, capped."""
        per = [self.char_sylls(c, scheme)[0] for c in name]
        out, seen = [], set()
        for combo in itertools.islice(itertools.product(*per), 4096):
            k = tuple(combo)
            if k not in seen:
                seen.add(k)
                out.append(k)
                if len(out) >= cap:
                    break
        return out


def pinyin_syll(py):
    for ini, cls in [('zh', 'C'), ('ch', 'C'), ('sh', 'S'), ('b', 'P'), ('p', 'P'), ('f', 'P'),
                     ('m', 'M'), ('d', 'T'), ('t', 'T'), ('n', 'N'), ('l', 'L'), ('g', 'K'),
                     ('k', 'K'), ('h', 'H'), ('j', 'C'), ('q', 'C'), ('x', 'S'), ('r', 'R'),
                     ('z', 'C'), ('c', 'C'), ('s', 'S'), ('y', ''), ('w', '')]:
        if py.startswith(ini):
            onset, rest = cls, py[len(ini):]
            break
    else:
        onset, rest = '', py
    coda = 'G' if rest.endswith('ng') else 'N' if rest.endswith('n') else ''
    v = 'A' if 'a' in rest else 'U' if ('u' in rest or 'o' in rest) else 'I'
    return onset, coda, v


def skeleton(sylls):
    """Token string: onset (upper), vowel class (lower a/i/u), coda (upper).
    Vowels are cheap tokens: they help separate 敌鲁 from 合鲁 but a vowel
    mismatch costs far less than a consonant mismatch."""
    return ''.join(o + (v.lower() if v in 'AIU' else '') + c for o, c, v in sylls)


def consonants(sk):
    return ''.join(t for t in sk if not t.islower())


# Latin input (Roxšan, Oirat, Temüjin). Use scholarly values: x = kh.
LATIN = [('tsh', 'C'), ('ts', 'C'), ('dz', 'C'), ('ch', 'C'), ('sh', 'S'), ('zh', 'S'),
         ('kh', 'H'), ('gh', 'H'), ('th', 'T'), ('ph', 'P'), ('ng', 'G')]
LATIN1 = dict(zip('pbfvmtdncčǰjsšzžşkgqŋxhγğḫlr',
                  'PPPPMTTNCCCCSSSSSKKKGHHHHHLR'))


LATIN_V = dict(zip('aáàâāäeéèêēəiíìîīıïoóòôōöøuúùûūüy', 'aaaaaaiiiiiiiiiiiiuuuuuuuuuuuuuuu'))


def latin_skeleton(s):
    s = s.lower()
    out, i = [], 0
    while i < len(s):
        for dg, cls in LATIN:
            if s.startswith(dg, i):
                out.append(cls)
                i += len(dg)
                break
        else:
            c = s[i]
            if c == 'y' and i + 1 < len(s) and s[i + 1] in LATIN_V:
                i += 1                       # glide before a vowel: drop
                continue
            cls = LATIN1.get(c) or LATIN_V.get(c)
            if cls and not (out and out[-1] == cls and cls.islower()):
                out.append(cls)              # long vowels count once; ll = coda + onset
            i += 1
    return ''.join(out)


def is_latin(s):
    return not HAN.search(s)


# Substitution costs between consonant classes (symmetric). Everything not
# listed costs 1. These encode the usual transcription slippages.
_SUB = {('C', 'S'): .3, ('C', 'T'): .6, ('K', 'H'): .3, ('K', 'G'): .3, ('G', 'N'): .5,
        ('N', 'M'): .5, ('L', 'R'): .2, ('T', 'L'): .3, ('T', 'R'): .3, ('J', 'N'): .3,
        ('J', 'C'): .5, ('J', 'R'): .4,
        # Tang north-western Chinese denasalised 明 泥 疑 (m- ≈ b-, n- ≈ d-, ŋ- ≈ g-),
        # so they routinely wrote foreign b d g: 默啜 = Bäg Čor
        ('P', 'M'): .3, ('T', 'N'): .3}
SUB = {**_SUB, **{(b, a): v for (a, b), v in _SUB.items()}}
# Tang transcription writes foreign -r/-l with a -t coda (阙 = kül) or drops it
# (啜 = čor), so those slips are cheap.
INDEL = {'H': .5, 'G': .5, 'R': .4, 'L': .6, '?': .5, 'a': .3, 'i': .3, 'u': .3}


def sub_cost(a, b):
    if a == b:
        return 0.0
    if a.islower() != b.islower():
        return 9.0                            # never align a vowel with a consonant
    if a.islower():
        return .25
    if '?' in (a, b):
        return .5
    return SUB.get((a, b), 1.0)


def weight(sk):
    return sum(INDEL.get(t, 1.0) for t in sk)


def dist(a, b):
    prev = [0.0]
    for ch in b:
        prev.append(prev[-1] + INDEL.get(ch, 1.0))
    for ca in a:
        cur = [prev[0] + INDEL.get(ca, 1.0)]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + INDEL.get(ca, 1.0),
                           cur[j - 1] + INDEL.get(cb, 1.0),
                           prev[j - 1] + sub_cost(ca, cb)))
        prev = cur
    return prev[-1]


def sim(sa, sb):
    n = max(weight(sa), weight(sb))
    return 1.0 if n == 0 else max(0.0, 1 - dist(sa, sb) / n)


def strip_common_prefix(a, b, t2s):
    """耶律敌鲁 vs 耶律合鲁 -> 敌鲁 vs 合鲁: a shared clan name says nothing
    about whether the personal names are variants."""
    sa, sb = t2s(a), t2s(b)
    k = 0
    while k < min(len(sa), len(sb)) and sa[k] == sb[k]:
        k += 1
    if k and len(a) - k >= 2 and len(b) - k >= 2:
        return a[k:], b[k:]
    return a, b


def score(ph, a, b, scheme, strip_prefix=False):
    """Best similarity over reading combinations, 0..1 (weighted edit distance
    on onset/vowel/coda tokens, normalised by the heavier name)."""
    if is_latin(a) and is_latin(b):
        return sim(latin_skeleton(a), latin_skeleton(b)), None
    if is_latin(a):
        a, b = b, a
    va = ph.variants(a, scheme)
    if is_latin(b):
        lb = latin_skeleton(b)
        forms = [(lb, 0.0)]
        if lb and not lb[-1].islower():          # Chinese often drops a final consonant
            forms.append((lb[:-1], .05))
        return max(((sim(skeleton(x), f) - pen, (x, lb)) for x in va for f, pen in forms),
                   key=lambda t: t[0])
    if strip_prefix:
        a, b = strip_common_prefix(a, b, ph.t2s)
        va = ph.variants(a, scheme)
    vb = ph.variants(b, scheme)
    best, arg = -1.0, None
    for x in va:
        sx = skeleton(x)
        for y in vb:
            s = sim(sx, skeleton(y))
            if s > best:
                best, arg = s, (x, y)
    return best, arg


def fmt_sylls(sylls):
    return ' '.join((o or '∅') + ('-' + c if c else '') + f'[{v}]' for o, c, v in sylls)


# ── corpus ───────────────────────────────────────────────────────────────────
SKIP_PARTS = ('白话', '白話', '译文', '譯文', '段译', '段譯')
JUNK = ('←', '首页', '目录', '下一节', '上一节', '阿星星')


def paragraphs(path):
    t = path.read_text(encoding='utf-8', errors='ignore')
    if path.suffix == '.html':
        t = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', t)
        ps = [html.unescape(re.sub(r'<[^>]+>', '', p)).strip()
              for p in re.findall(r'(?is)<p[^>]*>(.*?)</p>', t)]
    else:
        ps = [p.strip() for p in t.splitlines()]
    return [p for p in ps if p and not any(j in p for j in JUNK)]


def corpus_files(root, books=None):
    root = Path(root)
    for f in sorted(root.rglob('*')):
        if f.suffix not in ('.txt', '.html') or not f.is_file():
            continue
        rel = f.relative_to(root)
        if any(s in str(rel) for s in SKIP_PARTS):
            continue
        book = rel.parts[0]
        if books and book not in books:
            continue
        yield book, rel, f


BIO_FILE = re.compile(r'列传|列傳|传/|傳/|世家|外纪|外紀')
HEAD = re.compile(r'^([\u4e00-\u9fff]{2,6})，(.{0,30})')
HEAD_CUE = re.compile(r'字|人也|人。|人，|本名|小字|部人|氏|族|之子|之孫|之孙|之弟|子也|孫也|孙也|世為|世为|其先|初名|一名')
ALIAS = re.compile(r'(本名|小字|一名|又作|亦作|或作|初名)([\u4e00-\u9fff]{2,5})[，。、]')

# Common Han surnames: 2–3 char names starting with these are almost always
# Chinese-style names, and comparing them phonetically floods the output.
HAN_SURNAMES = set('王李張张劉刘陳陈楊杨趙赵黃黄周吳吴徐孫孙胡朱高林何郭馬马羅罗梁宋鄭郑謝谢韓韩唐馮冯于董蕭萧程曹袁鄧邓許许傅沈曾彭呂吕蘇苏盧卢蔣蒋蔡賈贾丁魏薛葉叶閻阎余潘杜戴夏鍾钟汪田任姜范方石姚譚谭廖鄒邹熊金陸陆郝孔白崔康毛邱秦江史顧顾侯邵孟龍龙萬万段雷錢钱湯汤尹黎易常武喬乔賀贺賴赖龔龚文'
                   '戚龐庞項项洪魚鱼章商明邢支寇種种狄向晏范富歐欧陽阳司馬包岳辛滕柴種晁晉晋畢毕褚衛卫尤嚴严華华施翟祝莊庄柳嵇竇窦伍凌燕'
                   '樂乐阮祁舒屈奚游溫温紀纪計计莫童錢鈕钮聶聂穆雍彭蒙苗鮑鲍費费甘沃喻賁贲荀祖路婁娄危')


def bio_heads(root, books=None):
    """Biography subjects: paragraph-initial NAME，... with a biographical cue.
    Native names given as 本名/小字/又作 are attached as aliases."""
    out = []
    for book, rel, f in corpus_files(root, books):
        if not BIO_FILE.search(str(rel).replace('\\', '/') + '/'):
            continue
        for i, p in enumerate(paragraphs(f)):
            m = HEAD.match(p)
            if not m or not HEAD_CUE.search(m.group(2)):
                continue
            name = m.group(1).split('字')[0]           # 宋史 style: 郝戭字伯牙，
            if len(name) < 2 or name.startswith(NOT_NAMES) or DATEISH.search(name) or NONNAME.search(name):
                continue
            if len(name) >= 3 and name[0] in KIN:      # 弟虚列 -> 虚列 (sub-biography)
                name = name[1:]
            aliases = [a for _, a in ALIAS.findall(p[:60])
                       if not DATEISH.search(a) and not NONNAME.search(a)]
            out.append({'name': name, 'aliases': aliases, 'book': book,
                        'file': str(rel), 'para': i, 'snippet': p[:70]})
    return out


# Paragraph openers that look like "NAME，" but are not names.
NOT_NAMES = ('先是', '初', '于是', '於是', '是时', '是時', '明年', '既而', '至是', '已而', '其后',
             '其後', '久之', '未几', '未幾', '赞曰', '贊曰', '论曰', '論曰', '史臣曰', '时', '時')


DATEISH = re.compile(r'[一二三四五六七八九十百]+[年月日]|[年月]$')
KIN = set('弟子兄孙孫侄姪')
NONNAME = re.compile(r'者$|氏$|后$|妃$|^有|[其以为為於是迁遷进進知州闻聞还還曰事]')


def foreign_like(name):
    return not (len(name) <= 3 and name[0] in HAN_SURNAMES)


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_key(a, ph):
    for name in a.names:
        if is_latin(name):
            print(f'{name}\tlatin skeleton: {latin_skeleton(name)}')
            continue
        print(f'{name}  [{a.scheme}]')
        for c in name:
            sy, src = ph.char_sylls(c, a.scheme)
            descs = ph.readings.get(c) or ph.readings.get(ph.t2s(c)) or []
            print(f'  {c}  {src:8} {" / ".join(descs) or "-":24} -> {fmt_sylls(sy)}')
        sk = sorted({skeleton(v) for v in ph.variants(name, a.scheme)})
        print(f'  skeleton(s): {", ".join(sk)}')


def cmd_match(a, ph):
    for scheme in ([a.scheme] if a.scheme != 'both' else ['mc', 'om', 'qm']):
        s, arg = score(ph, a.a, a.b, scheme)
        detail = ''
        if arg and isinstance(arg[1], str):
            detail = f'{skeleton(arg[0])} vs {arg[1]}'
        elif arg:
            detail = f'{fmt_sylls(arg[0])}  vs  {fmt_sylls(arg[1])}'
        print(f'{scheme}: {s:.3f}   {detail}')


CLANS = ('耶律', '移剌', '完颜', '蒲察', '纥石烈', '徒单', '乌古论', '夹谷', '仆散', '术虎',
         '石抹', '孛术鲁', '乌林答', '裴满', '温迪罕', '奥屯', '抹捻', '独吉', '唐括', '阿勒根')


def foreignness_model(heads, ph):
    """Per-character log-odds learned from the corpus itself: characters in
    native names (本名/小字/又作, and names after a Khitan/Jurchen clan) versus
    characters in Han given names (after a common Han surname). A name's score
    is the mean over its characters; > 0 means 'looks transcribed'."""
    import math
    fo, ha = defaultdict(int), defaultdict(int)
    for h in heads:
        for al in h['aliases']:
            for c in ph.t2s(al):
                fo[c] += 1
        n = ph.t2s(h['name'])
        clan = next((c for c in CLANS if n.startswith(c)), None)
        if clan:
            for c in n[len(clan):]:
                fo[c] += 1
        elif len(n) in (2, 3) and n[0] in HAN_SURNAMES:
            for c in n[1:]:
                ha[c] += 1
    tf, th = sum(fo.values()) + 1, sum(ha.values()) + 1

    def score(name):
        cs = ph.t2s(name)
        # characters never seen on either side contribute 0 (no evidence)
        return sum(math.log(((fo[c] + .5) / tf) / ((ha[c] + .5) / th)) if (fo[c] or ha[c]) else 0.0
                   for c in cs) / len(cs)
    return score


def collapse(sk):
    return consonants(sk).translate(str.maketrans({'C': 'S', 'H': 'K', 'G': 'K', 'R': 'L', 'J': 'L',
                                       'M': 'N', '?': None}))


def del1(s):
    return {s} | {s[:i] + s[i + 1:] for i in range(len(s))}


def cmd_twins(a, ph):
    books = set(a.books.split(',')) if a.books else None
    heads = bio_heads(a.corpus, books)
    print(f'{len(heads)} biography subjects', file=sys.stderr)

    # candidate names: native (本名/又作) forms, plus heads that look transcribed
    fscore = foreignness_model(heads, ph)
    cands = []
    for hid, h in enumerate(heads):
        names = list(h['aliases']) or [h['name']]
        for n in names:
            if a.include_han or (foreign_like(n) and fscore(n) > a.min_foreign):
                cands.append((hid, n, ph.t2s(n)))
    print(f'{len(cands)} candidate names', file=sys.stderr)

    # Blocking: consonant skeleton (collapsed) and all its 1-deletions, for the
    # full name and for the name minus its first 1–2 characters (clan names).
    index = defaultdict(set)
    for ci, (_, n, _) in enumerate(cands):
        for k in range(0, 3):
            part = n[k:]
            if len(part) < 2:
                break
            for v in ph.variants(part, a.scheme):
                c = collapse(skeleton(v))
                if len(c) < a.min_skeleton - (1 if k else 0):
                    continue
                for key in del1(c):
                    index[(k > 0, key)].add(ci)

    pairs = set()
    for bucket in index.values():
        if len(bucket) > a.max_bucket:
            continue
        for x, y in itertools.combinations(sorted(bucket), 2):
            hx, nx, sx = cands[x]
            hy, ny, sy = cands[y]
            if hx == hy or sx == sy or sx in sy or sy in sx:
                continue
            if not a.cross_book_only or heads[hx]['book'] != heads[hy]['book']:
                pairs.add((x, y))
    print(f'{len(pairs)} blocked pairs to score', file=sys.stderr)

    rows = []
    for x, y in pairs:
        s, _ = score(ph, cands[x][1], cands[y][1], a.scheme, strip_prefix=True)
        if s >= a.min_score:
            rows.append((s, x, y))
    rows.sort(key=lambda r: (-r[0], cands[r[1]][1]))

    if a.emit_table:
        emit_table(a, ph, heads, cands, rows)

    out = open(a.out, 'w', encoding='utf-8') if a.out else sys.stdout
    print('score\tname_a\tbook_a\tsubject_a\tname_b\tbook_b\tsubject_b\tsnippet_a\tsnippet_b', file=out)
    for s, x, y in rows[:a.limit]:
        ha, hb = heads[cands[x][0]], heads[cands[y][0]]
        print(f'{s:.3f}\t{cands[x][1]}\t{ha["book"]}\t{ha["name"]}\t{cands[y][1]}\t{hb["book"]}\t'
              f'{hb["name"]}\t{ha["snippet"]}\t{hb["snippet"]}', file=out)
    print(f'{len(rows)} pairs >= {a.min_score}', file=sys.stderr)


def emit_table(a, ph, heads, cands, rows):
    """Union high-scoring pairs into clusters and write them as proposed
    equivalence rows. Canonical = most frequent spelling in the corpus.
    Everything is marked confidence=review: you decide what to keep."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s, x, y in rows:
        if s >= a.cluster_min:
            parent[find(cands[x][2])] = find(cands[y][2])
    groups = defaultdict(set)
    for n in list(parent):
        groups[find(n)].add(n)

    books = set(a.books.split(',')) if a.books else None
    text = ''.join(ph.t2s(p) for _, _, f in corpus_files(a.corpus, books) for p in paragraphs(f))
    subjects = defaultdict(set)
    for hid, n, sn in cands:
        subjects[sn].add(heads[hid]['name'])

    with open(a.emit_table, 'w', encoding='utf-8') as f:
        f.write('id\tcanonical_zh\tlatin\tvariants\tforeign\tscheme\tconfidence\tnote\texclude\n')
        for k, g in enumerate(sorted(groups.values(), key=lambda g: -len(g))):
            if len(g) < 2:
                continue
            freq = {v: text.count(v) for v in g}
            canon = max(g, key=lambda v: (freq[v], v))
            flag = 'check: chained cluster; ' if len(g) > 4 else ''
            note = flag + 'freq ' + ', '.join(f'{v}:{freq[v]}' for v in sorted(g, key=lambda v: -freq[v])) \
                + ' | subjects ' + '、'.join(sorted({s for v in g for s in subjects[v]}))
            f.write(f'auto{k:03d}\t{canon}\t\t{"|".join(sorted(g, key=lambda v: -freq[v]))}'
                    f'\t\t{a.scheme}\treview\t{note}\t\n')
    print(f'proposed clusters -> {a.emit_table}', file=sys.stderr)


def read_tsv(path):
    lines = [l.rstrip('\n') for l in Path(path).read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.startswith('#')]
    head = lines[0].split('\t')
    return [dict(zip(head, l.split('\t'))) for l in lines[1:]]


def cmd_eval(a, ph):
    gold = read_tsv(a.gold)
    pos = []
    print(f'{"a":10}{"b":10}{"scheme":7}{"mc":>7}{"om":>7}  note')
    for g in gold:
        s_mc = score(ph, g['a'], g['b'], 'mc')[0]
        s_om = score(ph, g['a'], g['b'], 'om')[0]
        own = s_mc if g['scheme'] == 'mc' else s_om
        pos.append(own)
        print(f'{g["a"]:10}{g["b"]:10}{g["scheme"]:7}{s_mc:7.3f}{s_om:7.3f}  {g.get("note", "")}')

    # negatives: random pairs of distinct transcription-like names
    rng = random.Random(0)
    if a.corpus:
        pool = sorted({n for h in bio_heads(a.corpus, set(a.books.split(',')) if a.books else None)
                       for n in (h['aliases'] or ([h['name']] if foreign_like(h['name']) else []))})
    else:
        pool = sorted({g[k] for g in gold for k in ('a', 'b') if not is_latin(g[k])})
    neg = []
    gold_set = {frozenset((ph.t2s(g['a']), ph.t2s(g['b']))) for g in gold}
    for _ in range(a.n_neg):
        x, y = rng.sample(pool, 2)
        if frozenset((ph.t2s(x), ph.t2s(y))) in gold_set or ph.t2s(x) == ph.t2s(y):
            continue
        neg.append(score(ph, x, y, a.neg_scheme)[0])
    neg.sort()
    print(f'\npositives: {len(pos)}   negatives: {len(neg)} random pairs from '
          f'{"corpus biography names" if a.corpus else "gold names"} ({len(pool)} names), scheme {a.neg_scheme}')
    print(f'{"threshold":>10}{"recall":>9}{"false-pos rate":>16}')
    for t in (.70, .75, .80, .85, .90, .95):
        r = sum(p >= t for p in pos) / len(pos)
        fpr = sum(n >= t for n in neg) / max(1, len(neg))
        print(f'{t:>10.2f}{r:>9.2f}{fpr:>16.4f}')
    print('\nFalse-pos rate is per random pair. In a corpus of N names there are ~N²/2 pairs, '
          'so even 0.1% means many false hits: treat twins output as a review queue, not findings.')

    # Cross-script check (used to verify LLM proposals): Chinese form vs original
    lex = [e for e in read_tsv(a.lexicon) if e.get('original')] if a.lexicon else []
    if lex:
        pos, neg = [], []
        for e in lex:
            for f in e['forms'].split('|'):
                pos.append(score(ph, f, e['original'], e['scheme'])[0])
                for o in lex:
                    if o is not e:
                        neg.append(score(ph, f, o['original'], e['scheme'])[0])
        print(f'\nChinese form vs original ({len(pos)} true pairs from the lexicon, {len(neg)} wrong pairs)')
        print(f'{"threshold":>10}{"recall":>9}{"wrong kept":>12}')
        for t in (.5, .55, .6, .65, .7, .75, .8):
            print(f'{t:>10.2f}{sum(x >= t for x in pos) / len(pos):>9.2f}'
                  f'{sum(x >= t for x in neg) / len(neg):>12.4f}')
        print('This threshold is propose --min-verify: an LLM proposal is kept only above it.')


def load_table(path, ph):
    entries, forms = [], {}
    for e in read_tsv(path):
        e['variants_list'] = [v for v in e.get('variants', '').split('|') if v]
        e['exclude_list'] = [ph.t2s(v) for v in e.get('exclude', '').split('|') if v]
        entries.append(e)
        for v in set(e['variants_list'] + [e['canonical_zh']]):
            if len(v) >= 2:
                forms[ph.t2s(v)] = e
    return entries, forms


MENTION = {'又作', '亦作', '或作', '一作', '讹为', '讹作', '本名', '小字', '亦曰', '一名'}


def cmd_read(a, ph):
    import origin
    src = Path(a.src)
    if src.is_dir() and not a.out.endswith('.html'):
        files = [f for f in sorted(src.rglob('*')) if f.suffix in ('.txt', '.html') and f.is_file()
                 and not any(x in str(f.relative_to(src)) for x in SKIP_PARTS)]
        n, names, tot = origin.render_site(ph, a, files, src, a.out)
        print(f'{n} chapters, {names} names -> {a.out}/index.html  '
              + ' '.join(f'{k}:{v}' for k, v in tot.most_common()), file=sys.stderr)
        return
    files = [f for _, _, f in corpus_files(src)] if src.is_dir() else [src]
    doc, seen = origin.render_html(ph, a, files, src if src.is_dir() else None)
    Path(a.out).write_text(doc, encoding='utf-8')
    fams = defaultdict(int)
    for r in seen.values():
        fams[r['fam']] += sum(r['forms'].values())
    print(f'{sum(fams.values())} name occurrences, {len(seen)} names -> {a.out}  '
          + ' '.join(f'{k}:{v}' for k, v in sorted(fams.items(), key=lambda t: -t[1])), file=sys.stderr)


def cmd_find(a, ph):
    """Which files mention a word? (so you know what to pass to `read`)"""
    books = set(a.books.split(',')) if a.books else None
    w = ph.t2s(a.word)
    hits = []
    for book, rel, f in corpus_files(a.corpus, books):
        n, ex = 0, ''
        for p in paragraphs(f):
            s = ph.t2s(p)
            c = s.count(w)
            if c and not ex:
                i = s.find(w)
                ex = s[max(0, i - 15):i + len(w) + 15]
            n += c
        if n:
            hits.append((n, f, ex))
    hits.sort(key=lambda t: -t[0])
    for n, f, ex in hits[:a.limit]:
        print(f'{n:>5}  {f}\n       …{ex}…')
    if not hits:
        print(f'not found: {a.word}')


def main():
    for stream in (sys.stdout, sys.stderr):      # Windows consoles: avoid UnicodeEncodeError
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--table-json', default=str(HERE / 'mc_table.json'))
    sp = ap.add_subparsers(dest='cmd', required=True)
    sch = dict(choices=['mc', 'om', 'qm'], default='om', help='; '.join(f'{k}: {v}' for k, v in SCHEMES.items()))

    p = sp.add_parser('key'); p.add_argument('names', nargs='+'); p.add_argument('--scheme', **sch)
    p = sp.add_parser('match'); p.add_argument('a'); p.add_argument('b')
    p.add_argument('--scheme', choices=['mc', 'om', 'qm', 'both'], default='both')

    p = sp.add_parser('twins'); p.add_argument('--corpus', required=True)
    p.add_argument('--books', help='comma list, e.g. 辽史,金史,宋史')
    p.add_argument('--scheme', **sch)
    p.add_argument('--min-score', type=float, default=.80)
    p.add_argument('--min-skeleton', type=int, default=3, help='ignore names with fewer consonants')
    p.add_argument('--max-bucket', type=int, default=300)
    p.add_argument('--cross-book-only', action='store_true')
    p.add_argument('--include-han', action='store_true', help='also compare Han-style names')
    p.add_argument('--min-foreign', type=float, default=0.3,
                   help='min transcription-likeness (log-odds, learned from the corpus)')
    p.add_argument('--limit', type=int, default=500); p.add_argument('-o', '--out')
    p.add_argument('--emit-table', help='also write clusters as proposed equivalence.tsv rows')
    p.add_argument('--cluster-min', type=float, default=.95, help='min score to join a cluster')

    p = sp.add_parser('eval'); p.add_argument('gold')
    p.add_argument('--corpus'); p.add_argument('--books')
    p.add_argument('--neg-scheme', choices=['mc', 'om', 'qm'], default='om')
    p.add_argument('--n-neg', type=int, default=20000)
    p.add_argument('--lexicon', default=str(HERE / 'lexicon.tsv'))

    def origin_args(p, corpus_required=False):
        p.add_argument('--table', default=str(HERE / 'equivalence.tsv'), help='variant table (unification)')
        p.add_argument('--lexicon', default=str(HERE / 'lexicon.tsv'), help='curated original forms')
        p.add_argument('--proposed', default=str(HERE / 'lexicon_proposed.tsv'), help='LLM proposals')
        p.add_argument('--model', default=str(HERE / 'foreign_model.json'), help='transcription-character model')
        p.add_argument('--scheme', choices=['mc', 'om', 'qm'], help='override the per-book phonology')
        p.add_argument('--sound', action='store_true',
                       help='also link names to the lexicon by sound alone (weak; off by default)')
        p.add_argument('--cache', default=str(HERE / 'llm_cache.json'), help='LLM verdicts and proposals')
        p.add_argument('--siku', choices=['auto', 'on', 'off'], default='auto',
                       help='undo Qianlong respellings (auto: for 四庫本 books fetched from Kanripo)')
        if corpus_required:
            p.add_argument('--corpus', required=True)
            p.add_argument('--books', help='comma list, e.g. 旧唐书,新唐书')

    p = sp.add_parser('read', help='reading view: originals above names, variants unified')
    p.add_argument('src', help='a .txt/.html file or a book directory')
    origin_args(p)
    p.add_argument('--display', choices=['zh', 'latin'], default='zh',
                   help='latin: show the original form in the line and the Chinese above it')
    p.add_argument('--known-only', action='store_true', help='mark only lexicon/table names')
    p.add_argument('--unknown-mean', type=float, default=2.0,
                   help='how transcription-like an unlisted string must be to be marked')
    p.add_argument('--title')
    p.add_argument('-o', '--out', default='reading.html',
                   help='NAME.html: one page. For a book folder, a name without .html makes a '
                        'browsable site: index, one page per chapter, name index')
    p.add_argument('--index-limit', type=int, default=400, help='max names per family in the name index')

    p = sp.add_parser('fetch', help='download a text from Kanripo by id or title')
    p.add_argument('text', help='KR id (KR2a0039) or title (清史稿 / 大唐西域记)')
    p.add_argument('--corpus', default='corpus'); p.add_argument('--juan', help='e.g. 1-5,12')
    p.add_argument('--name', help='folder name (default: the title)')
    p.add_argument('--scheme', choices=['mc', 'om', 'qm'], help='override the dynasty-based phonology')

    p = sp.add_parser('setup', help='one-time data preparation after cloning (needs internet)')

    p = sp.add_parser('variants', help='build variants.json (異體字 -> 正字) for 四庫本 texts')

    p = sp.add_parser('guoyujie', help='harvest Qianlong respellings from 三史國語解')
    p.add_argument('-o', '--out', default=str(HERE / 'equivalence_siku.tsv'))

    p = sp.add_parser('align', help='compare two editions of a book; collect renamed names')
    p.add_argument('a', help='edition whose spellings are canonical (e.g. corpus/元史)')
    p.add_argument('b', help='other edition (e.g. corpus/元史_四库)')
    p.add_argument('--min-count', type=int, default=1)
    p.add_argument('--min-overlap', type=float, default=.15)
    p.add_argument('-o', '--out', default='equivalence_aligned.tsv')

    p = sp.add_parser('find', help='which files mention a word')
    p.add_argument('word'); p.add_argument('--corpus', required=True); p.add_argument('--books')
    p.add_argument('--limit', type=int, default=20)

    p = sp.add_parser('train', help='learn transcription characters from a corpus')
    p.add_argument('--corpus', required=True)
    origin_args(p)

    p = sp.add_parser('scan', help='index all transcribed names in books, with origins')
    origin_args(p, True)
    p.add_argument('--min-count', type=int, default=2); p.add_argument('-o', '--out')

    p = sp.add_parser('propose', help='LLM proposals for unknown names, kept only if the sound matches')
    origin_args(p, True)
    p.add_argument('--min-count', type=int, default=3)
    p.add_argument('--top', type=int, default=100, help='most frequent unknown names to ask about')
    p.add_argument('--batch', type=int, default=20)
    p.add_argument('--min-verify', type=float, default=.60, help='min sound score to keep a proposal (see eval)')
    p.add_argument('--model-name', default='claude-sonnet-5')
    p.add_argument('--dry-run', action='store_true', help='print the first prompt, call nothing')
    p.add_argument('--mock', help='JSON file of answers instead of calling the API (testing)')

    a = ap.parse_args()
    ph = Phon(a.table_json)
    if a.cmd in ('fetch', 'variants', 'guoyujie', 'align', 'setup'):
        import corpora
        {'fetch': corpora.cmd_fetch, 'variants': corpora.cmd_variants, 'setup': corpora.cmd_setup,
         'guoyujie': corpora.cmd_guoyujie, 'align': corpora.cmd_align}[a.cmd](a, ph)
        return
    if a.cmd in ('train', 'scan', 'propose'):
        import origin
        {'train': origin.cmd_train, 'scan': origin.cmd_scan, 'propose': origin.cmd_propose}[a.cmd](a, ph)
        return
    {'key': cmd_key, 'match': cmd_match, 'twins': cmd_twins, 'eval': cmd_eval, 'read': cmd_read,
     'find': cmd_find}[a.cmd](a, ph)


if __name__ == '__main__':
    main()
