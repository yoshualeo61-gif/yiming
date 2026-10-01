"""corpora — bring any Chinese history text into yiming.

  fetch     download a text from Kanripo (漢籍リポジトリ, ~9,000 titles) by
            ID or title, cleaned into corpus/<書名>/NNN.txt, with the
            compiler's dynasty saved in meta.json (used to pick the phonology)
  variants  build variants.json: 異體字 -> 正字 (竒 -> 奇, 圗 -> 圖), so 四庫本
            texts match the lexicon
  guoyujie  harvest 《欽定遼金元三史國語解》: Qianlong's respellings of every
            Liao/Jin/Yuan name (托克托 for 脫脫, 巴圖 for 拔都) -> equivalence
            rows, so 四庫本 texts show the original spelling

Kanripo's base edition is mostly 文淵閣四庫全書 (WYG). In the Liao, Jin and
Yuan histories, and in many other 四庫 texts, those carry Qianlong's altered
names. Without `guoyujie` the names in them will not match anything.
"""
import json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = 'https://raw.githubusercontent.com/kanripo/{repo}/master/{file}'
CATALOG = 'https://raw.githubusercontent.com/kanripo/KR-Catalog/master/KR/{sec}.txt'
CACHE = HERE / 'cache'

# Which phonology fits a dynasty's transcriptions.
DYNASTY_SCHEME = {}
for d in '先秦 周 秦 漢 前漢 後漢 東漢 西漢 三國 魏 蜀 吳 晉 西晉 東晉 南朝宋 宋南朝 齊 南齊 梁 陳 北魏 北齊 北周 隋 唐 後梁 後唐 後晉 後漢 後周 五代'.split():
    DYNASTY_SCHEME[d] = 'mc'
for d in '宋 北宋 南宋 遼 金 元 明'.split():
    DYNASTY_SCHEME[d] = 'om'
for d in '清 民國'.split():
    DYNASTY_SCHEME[d] = 'qm'


def get(url, retries=3):
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + k)
        except urllib.error.URLError:
            time.sleep(1 + k)
    return None


# ── catalog ──────────────────────────────────────────────────────────────────
SECTIONS = [f'KR{n}{c}' for n in '123456' for c in 'abcdefghijklmnopq']


def catalog(sections=None):
    """[(kr_id, title, dynasty, author)] from the Kanripo catalog (cached)."""
    CACHE.mkdir(exist_ok=True)
    out = []
    for sec in sections or SECTIONS:
        f = CACHE / f'catalog_{sec}.txt'
        if not f.exists():
            t = get(CATALOG.format(sec=sec))
            f.write_text(t or '', encoding='utf-8')
        for m in re.finditer(r'^\*\*\* (KR\w+) (\S+)', f.read_text(encoding='utf-8'), re.M):
            parts = m.group(2).split('-')
            out.append((m.group(1), parts[0], parts[1] if len(parts) > 1 else '',
                        parts[2] if len(parts) > 2 else ''))
    return out


def resolve(query, ph=None):
    """KR id or title (繁/简) -> (kr_id, title, dynasty, author)."""
    if re.fullmatch(r'KR\d[a-z]\d{4}', query):
        sec = query[:4]
        for row in catalog([sec]):
            if row[0] == query:
                return row
        return (query, query, '', '')
    norm = (lambda s: ph.t2s(s)) if ph else (lambda s: s)
    q = norm(query)
    secs = ['KR2a', 'KR2b', 'KR2c', 'KR2d', 'KR2e', 'KR2g', 'KR2i', 'KR2k'] + SECTIONS
    seen = set()
    for sec in secs:
        if sec in seen:
            continue
        seen.add(sec)
        rows = catalog([sec])
        exact = [r for r in rows if norm(r[1]) == q]
        if exact:
            return exact[0]
    return None


# ── fetch ────────────────────────────────────────────────────────────────────
def clean_mandoku(text):
    """Kanripo mandoku text -> list of paragraphs. 四庫 texts have no paragraph
    marks, so a page break (<pb:…>) also starts a new paragraph."""
    text = re.sub(r'<pb:[^>]*>', '\n\n', text)
    text = re.sub(r'&KR\d+;', '〓', text)          # glyph not in Unicode
    paras, cur = [], ''
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        line = line.replace('¶', '').replace('\u3000', '').strip()
        if not line:
            if cur:
                paras.append(cur)
                cur = ''
        else:
            cur += line
    if cur:
        paras.append(cur)
    paras = [p.replace('欽定四庫全書', '') for p in paras]
    return [p for p in paras if p]


def parse_range(r):
    if not r:
        return None
    out = set()
    for part in r.split(','):
        if '-' in part:
            a, b = part.split('-')
            out |= set(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def cmd_fetch(a, ph):
    row = resolve(a.text, ph)
    if not row:
        sys.exit(f'not found in the Kanripo catalog: {a.text}  (try the KR id, e.g. KR2a0036)')
    kr, title, dynasty, author = row
    out = Path(a.corpus) / (a.name or title)
    out.mkdir(parents=True, exist_ok=True)
    juans = parse_range(a.juan)
    got, miss, n = 0, 0, (juans[0] if juans else 0)
    while True:
        if juans and n > juans[-1]:
            break
        if juans and n not in juans:
            n += 1
            continue
        t = get(RAW.format(repo=kr, file=f'{kr}_{n:03d}.txt'))
        if t is None:
            miss += 1
            if not juans and (miss >= 3 and got or miss >= 5):
                break
        else:
            miss = 0
            paras = clean_mandoku(t)
            (out / f'{n:03d}.txt').write_text('\n'.join(paras) + '\n', encoding='utf-8')
            got += 1
            print(f'\r{title} 卷{n:03d}', end='', file=sys.stderr)
        n += 1
    if got == 0 and juans and get(RAW.format(repo=kr, file=f'{kr}_001.txt')) is None:
        # single-卷 texts are stored as _000 (only then: a missing 卷 is not a single-file text)
        t = get(RAW.format(repo=kr, file=f'{kr}_000.txt'))
        if t is not None:
            (out / '000.txt').write_text('\n'.join(clean_mandoku(t)) + '\n', encoding='utf-8')
            got = 1
            print(f'{title}: no 卷 {a.juan}; this text is a single file (000), downloaded that', file=sys.stderr)
    meta = {'kr_id': kr, 'title': title, 'dynasty': dynasty, 'author': author,
            'edition': 'Kanripo master (mostly 文淵閣四庫全書)',
            'scheme': a.scheme or DYNASTY_SCHEME.get(dynasty, '')}
    (out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n{got} 卷 -> {out}  ({dynasty} {author}; scheme {meta["scheme"] or "?"})', file=sys.stderr)
    if got == 0:
        print('nothing downloaded: the text may not be published on Kanripo (e.g. 清史稿), '
              'or the 卷 range is wrong', file=sys.stderr)


# ── variant characters ───────────────────────────────────────────────────────
CJKVI = 'https://raw.githubusercontent.com/cjkvi/cjkvi-variants/master/{f}'
# frequent 四庫 forms the tables miss
MANUAL_VARIANTS = dict(zip('歳逺㡬䝉濓昻巻賫竒圗従徳逥埓', '歲遠幾蒙濂昂卷賚奇圖從德迴埒'))


def cmd_variants(a, ph):
    """variants.json: variant -> standard form, from 漢語大字典 (via cjkvi)
    plus a few Japanese-table and manual mappings."""
    vmap = {}
    t = get(CJKVI.format(f='hydzd-variants.txt')) or ''
    for line in t.splitlines():
        if line.startswith('#') or line.count(',') != 2:
            continue
        std, kind, var = line.split(',')
        if kind == 'hydzd/variant' and len(std) == 1 and len(var) == 1 and var != std:
            vmap.setdefault(var, std)
    for f in ('jp-old-style.txt', 'joyo-variants.txt', 'jinmei-variants.txt'):
        t = get(CJKVI.format(f=f)) or ''
        for line in t.splitlines():
            if line.startswith('#'):
                continue
            cols = re.split(r'[\t,]', re.sub(r'[\U000E0100-\U000E01EF]', '', line))
            cols = [c for c in cols if len(c) == 1 and '\u3400' <= c <= '\U0002FFFF']
            if len(cols) == 2 and cols[0] != cols[1]:
                new, old = cols        # Japanese new form -> traditional form
                vmap.setdefault(new, old)
    # Only map rare shapes. A character in GB2312 or Big5 is a normal character
    # in its own right (于/於, 干/乾): mapping it would merge different words.
    def common(c):
        for enc in ('gb2312', 'big5'):
            try:
                c.encode(enc)
                return True
            except UnicodeEncodeError:
                pass
        return False
    vmap = {k: v for k, v in vmap.items() if not common(k)}
    vmap.update(MANUAL_VARIANTS)
    (HERE / 'variants.json').write_text(json.dumps(vmap, ensure_ascii=False), encoding='utf-8')
    print(f'{len(vmap)} variant mappings -> variants.json', file=sys.stderr)


# ── 三史國語解 ───────────────────────────────────────────────────────────────
ENTRY = re.compile(r'^([^\s(（]{1,12})\s*[(（](.*)[)）]$')
OLD = re.compile(r'(?:卷[一二三四五六七八九十百]+|原)作([\u3400-\u9fff\U00020000-\U0002ffff]{1,10}?)(?=[遼金元，。、之為係實乃即並其今按卷作因又]|$)')
MORE = re.compile(r'(?:或書為|或書作|又訛作|又作|亦作|或作)([\u3400-\u9fff]{1,10}?)(?=[，。、又或實故已按因卷]|$)')
LANG = re.compile(r'(滿洲語|蒙古語|䝉古語|索倫語|唐古特語|回語|梵語)')


TITLE_SUFFIX = re.compile(r'(?<=.{2})(?:(?:[太德懿玄肅肃睿世穆景昭宣獻献簡简]祖|[太世聖圣仁英神哲徽欽钦高孝光寧宁理度睿憲宪]宗)[字名]?'
                          r'|(?:山|河|水|城|部|地|人|官|國|国|寺|軍|军|寨|泊|嶺|岭|川)名|[併并]改|名|字|又|又訛'
                          r'|..帝|..后|..尊號|萬[户戶]|百官志|以下皆.'
                          r'|(?:.祖|.宗|海陵|世宗|太子)(?:妃|子|女|次室|娘子|孫|弟|兄|母|父|姊|妹))$')


DESCRIPTORS = {'國名', '地名', '人名', '部名', '山名', '河名', '官名', '城名', '軍名', '寨名', '姓氏', '姓名'}


def trim_title(o):
    """卷一作薩剌德懿祖 -> 薩剌德; 拖雷睿宗名 -> 拖雷; 勃突山名 -> 勃突; X併改 -> X.
    (What follows the old spelling in 國語解 is a description, not part of it.)"""
    prev = None
    while prev != o:
        prev, o = o, TITLE_SUFFIX.sub('', o)
    return o


def cmd_guoyujie(a, ph):
    """Harvest 國語解: every Qianlong form (新譯) with the old form(s) (舊譯)."""
    kr = 'KR2a0037'
    rows, n = [], 0
    for j in range(1, 47):
        t = get(RAW.format(repo=kr, file=f'{kr}_{j:03d}.txt'))
        if t is None:
            continue
        paras = clean_mandoku(t)
        section = ''
        for p in paras:
            if re.match(r'^欽定(遼|金|元)史語解', p):
                section = p[2]
            # 莽賚呼圖(克)(…) : a small bracketed character belongs to the name
            p = re.sub(r'[(（]([^()（）]{1,2})[)）](?=[^)）]*[(（])', r'\1', p)
            m = ENTRY.match(p)
            if not m:
                continue
            new, body = m.group(1), m.group(2)
            olds = [o for o in OLD.findall(body) if o != new]
            olds += [o for o in MORE.findall(body) if o != new and o not in olds]
            olds = [trim_title(o) for o in olds]
            olds = [o for o in olds if 1 < len(o) <= 10 and o not in DESCRIPTORS]
            if not olds or len(new) < 2:
                continue
            lang = LANG.search(body)
            rows.append((section, new, olds, lang.group(1) if lang else ''))
            n += 1
        print(f'\r卷{j:02d}: {n} entries', end='', file=sys.stderr)
    print(file=sys.stderr)

    # A "new" spelling that is itself an old spelling elsewhere (欽察) must not be
    # mapped back: in a normal edition it is simply the name.
    all_old = {ph.t2s(o) for _, _, olds, _ in rows for o in olds}
    rows = [r for r in rows if ph.t2s(r[1]) not in all_old]

    out = Path(a.out)
    with out.open('w', encoding='utf-8') as f:
        f.write('# Harvested from 《欽定遼金元三史國語解》 (Kanripo KR2a0037) by `yiming.py guoyujie`.\n'
                '# canonical = the pre-Qianlong spelling (as in the 中華書局 editions); the Qianlong respelling\n'
                '# found in 四庫本 texts is a variant. Qianlong\'s "Manchu/Mongol meanings" are often\n'
                '# re-interpretations and are NOT kept as etymologies.\n')
        f.write('id\tcanonical_zh\tlatin\tvariants\tforeign\tscheme\tconfidence\tnote\texclude\tscope\n')
        seen = set()
        for k, (sec, new, olds, lang) in enumerate(rows):
            key = (ph.t2s(olds[0]), ph.t2s(new))
            if key in seen:
                continue
            seen.add(key)
            std = lambda w: ''.join(ph.variant.get(c, c) for c in w)
            variants = [std(o) for o in olds] + [std(new)]
            f.write(f'gyj{k:05d}\t{std(olds[0])}\t\t{"|".join(dict.fromkeys(variants))}\t\tom\thigh\t'
                    f'{sec}史; 四庫本改譯作{std(new)}{"（乾隆稱" + lang + "）" if lang else ""}\t\t{sec}\n')
    print(f'{len(seen)} rows -> {out}', file=sys.stderr)


def dynasty_scheme(book_dir):
    """Scheme from a fetched book's meta.json, if any."""
    m = Path(book_dir) / 'meta.json'
    if m.exists():
        d = json.loads(m.read_text(encoding='utf-8'))
        return d.get('scheme') or DYNASTY_SCHEME.get(d.get('dynasty', ''), '')
    return ''


# ── align two editions ───────────────────────────────────────────────────────
def _plain(ph, text):
    return ''.join(c for c in ph.t2s(text) if '\u3400' <= c <= '\u9fff' or c > '\uffff')


def cmd_align(a, ph):
    """Align two editions of one book (e.g. 中華本 from hunterhug and 四庫本 from
    Kanripo) and collect every short span that differs: these are the renamings.
    Output rows use the first edition's spelling as canonical."""
    import difflib
    from collections import Counter, defaultdict
    import yiming as Y

    def load(d):
        out = {}
        for _, rel, f in Y.corpus_files(Path(d).parent, {Path(d).name}):
            out[str(rel)] = _plain(ph, ''.join(Y.paragraphs(f)))
        return out

    import origin
    mp = HERE / 'foreign_model.json'
    fm = origin.ForeignModel.load(mp) if mp.exists() else (lambda c: 0.0)
    A, B = load(a.a), load(a.b)
    print(f'{len(A)} files in A, {len(B)} in B', file=sys.stderr)

    def grams(s, k=5, step=1):
        return {s[i:i + k] for i in range(0, max(0, len(s) - k), step)}
    ga = {f: grams(t) for f, t in A.items() if t}
    pairs, where = Counter(), defaultdict(set)
    for fb, tb in B.items():
        gb = grams(tb)
        if not gb:
            continue
        fa, best = max(((f, len(g & gb) / (len(gb) or 1)) for f, g in ga.items()), key=lambda t: t[1])
        if best < a.min_overlap:
            continue
        ta = A[fa]
        sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
        ops = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != 'replace':
                continue
            if max(i2 - i1, j2 - j1) > 10 and max(i2 - i1, j2 - j1) <= 80:
                # several renamings close together get merged into one block: split it
                sub = difflib.SequenceMatcher(None, ta[i1:i2], tb[j1:j2], autojunk=False)
                ops += [(i1 + a1, i1 + a2, j1 + b1, j1 + b2)
                        for o, a1, a2, b1, b2 in sub.get_opcodes() if o == 'replace']
            else:
                ops.append((i1, i2, j1, j2))
        # 斡羅思 vs 俄羅斯 differs in two places around a shared 羅: merge replace
        # ops separated by at most 2 identical characters into one span
        ops.sort()
        merged = []
        for i1, i2, j1, j2 in ops:
            if merged:
                pi1, pi2, pj1, pj2 = merged[-1]
                gap_a, gap_b = ta[pi2:i1], tb[pj2:j1]
                if 0 <= i1 - pi2 <= 2 and gap_a == gap_b and all(fm(c) > .5 for c in gap_a):
                    merged[-1] = (pi1, i2, pj1, j2)
                    continue
            merged.append((i1, i2, j1, j2))
        for i1, i2, j1, j2 in merged:
            # the edition diff cuts at the first differing character: 阿里海牙 vs
            # 阿爾哈雅 gives 里海牙/爾哈雅. Pull shared transcription characters back in.
            for _ in range(2):
                if i1 and j1 and ta[i1 - 1] == tb[j1 - 1] and fm(ta[i1 - 1]) > .5:
                    i1, j1 = i1 - 1, j1 - 1
                if i2 < len(ta) and j2 < len(tb) and ta[i2] == tb[j2] and fm(ta[i2]) > .5:
                    i2, j2 = i2 + 1, j2 + 1
            x, y = ta[i1:i2], tb[j1:j2]
            if 2 <= len(x) <= 10 and 2 <= len(y) <= 10:
                pairs[(x, y)] += 1
                where[(x, y)].add(fb)
        print(f'\r{fb} <- {fa} ({best:.2f})', end='', file=sys.stderr)
    print(file=sys.stderr)

    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(f'# Aligned {a.a} (canonical) with {a.b} by `yiming.py align`.\n'
                '# Each row: a span spelled differently in the two editions. Most are renamings of\n'
                '# foreign names (四庫本 respellings); some are ordinary textual variants — check.\n')
        f.write('id\tcanonical_zh\tlatin\tvariants\tforeign\tscheme\tconfidence\tnote\texclude\tscope\tcount\n')
        k = 0
        alltext_a = '\n'.join(A.values())
        for (x, y), n in pairs.most_common():
            if n < a.min_count:
                continue
            # a real respelling does not occur in the canonical edition itself;
            # if it does, this is an ordinary textual variant or an alignment slip
            if y in alltext_a:
                continue
            # 恟恟/汹汹-type variants: neither side looks like a transcription
            if n < 3 and max(sum(fm(c) for c in w) / len(w) for w in (x, y)) < .5:
                continue
            f.write(f'aln{k:05d}\t{x}\t\t{x}|{y}\t\tom\t{"high" if n >= 3 else "review"}\t'
                    f'另一版本作{y}（{n}處，{len(where[(x, y)])}卷）\t\t{Path(a.a).name}\t{n}\n')
            k += 1
    print(f'{k} differing spans (>= {a.min_count}x) -> {a.out}', file=sys.stderr)


def cmd_setup(a, ph):
    """One-time data preparation after cloning: the variant-character table
    (built from cjkvi, not redistributed) and, if missing, the 國語解 table."""
    cmd_variants(a, ph)
    if not (HERE / 'equivalence_siku.tsv').exists():
        a.out = str(HERE / 'equivalence_siku.tsv')
        cmd_guoyujie(a, ph)
    print('setup done', file=sys.stderr)
