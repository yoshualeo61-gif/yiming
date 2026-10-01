"""origin — show what a transcribed name was in its own language.

禄山 hides Sogdian Roxšan; 速不台 hides Mongolic Sübe'etei. This module adds,
on top of yiming's variant unification:

  train    learn which characters are typical of transcriptions (per corpus)
  scan     index every transcribed name in a book, with its origin if known
  propose  ask an LLM for the original of unknown names; keep only proposals
           whose sound actually matches (phonetic verification), mark them
  read     (via yiming.py read) reading view: original form above each name,
           coloured by language family

Trust levels, visible in the reading view:
  attested   curated lexicon (scholarly identification)       solid line
  proposed   LLM proposal that passed the sound check          dashed line
  sound      only a sound match to a lexicon entry             dashed, thin
  unknown    looks transcribed, origin not known               dotted grey
"""
import html, json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

import yiming as Y

HERE = Path(__file__).resolve().parent

FAMILIES = ['Iranian', 'Turkic', 'Mongolic', 'Para-Mongolic', 'Tungusic', 'Tibetic', 'Indic', 'Dravidian',
            'Semitic', 'Austronesian', 'European', 'Other']

# Transcription phonology by the period the book's sources were written in.
# By the era of the SOURCES, not the compiler: 明史 was compiled under the Qing
# from Ming records (om); 旧唐书 under the Later Jin from Tang records (mc).
# Books not listed fall back to the dynasty in meta.json (from `fetch`), else mc.
BOOK_SCHEME = {b: 'mc' for b in '史记 汉书 前汉书 后汉书 三国志 晋书 宋书 南齐书 梁书 陈书 魏书 北齐书 周书 '
               '隋书 南史 北史 旧唐书 新唐书 旧五代史 新五代史 资治通鉴 通典 唐会要 册府元龟 太平广记 '
               '大唐西域记 高僧传 续高僧传 法显传 佛国记 洛阳伽蓝记 大慈恩寺三藏法师传 酉阳杂俎 '
               '元和郡县图志 太平寰宇记 唐六典 贞观政要 安禄山事迹'.split()}
BOOK_SCHEME.update({b: 'om' for b in '宋史 辽史 金史 元史 明史 续资治通鉴长编 续资治通鉴 契丹国志 大金国志 '
                    '三朝北盟会编 蒙鞑备录 黑鞑事略 元朝秘史 圣武亲征录 长春真人西游记 诸蕃志 岭外代答 '
                    '岛夷志略 瀛涯胜览 星槎胜览 西洋番国志 明实录 职方外纪 西域番国志 殊域周咨录'.split()})
BOOK_SCHEME.update({b: 'qm' for b in '清史稿 清实录 异域录 钦定皇舆西域图志 西域图志 圣武记 海国图志 海国闻见录 '
                    '蒙古游牧记 朔方备乘 瀛寰志略 西域水道记 卫藏通志 平定准噶尔方略 八旗通志 '
                    '清朝文献通考 东华录'.split()})
EDITION_SUFFIX = re.compile(r'[_\-·(（]?(四库|四庫|wyg|WYG|kanripo|中华|中華|本)[)）]?$')

# 昭武九姓: surnames Sogdian families took from their home city.
SOGDIAN_SURNAMES = {'安': 'Bukhara', '康': 'Samarkand', '石': 'Chach (Tashkent)', '米': 'Maymurgh',
                    '何': 'Kushaniya', '史': 'Kesh', '曹': 'Kabudhan'}

# Characters widely used in transcription (Yuan–Ming, Tang Turkic, Buddhist).
# They only seed the model; corpus statistics decide the final weights.
SEED_CHARS = ('阿八巴拔伯孛卜不察赤答达歹迭朵哥忽花火吉剌刺里鲁罗马蛮木那纳帖铁秃脱兀斡失撒速塔台也牙伊亦'
              '哈罕合黑忙乞怯儿思斯沙都灰啜咄突骨默颉利伽毗苾阙特勤叶护设俟斤乙匐延陀葛逻禄悉密仆'
              '般若婆摩诃耶迦提萨埵弥勒槃鸠什')
HZ = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]+')


def book_title(book, ph=None):
    b = EDITION_SUFFIX.sub('', book)
    return ph.t2s(b) if ph else b


def book_meta(root, book):
    import corpora
    if not root:
        return {}
    m = Path(root) / book / 'meta.json'
    return json.loads(m.read_text(encoding='utf-8')) if m.exists() else {}


def scheme_for(book, override=None, root=None, ph=None):
    if override:
        return override
    t = book_title(book, ph)
    if t in BOOK_SCHEME:
        return BOOK_SCHEME[t]
    meta = book_meta(root, book)
    import corpora
    return meta.get('scheme') or corpora.DYNASTY_SCHEME.get(meta.get('dynasty', ''), 'mc')


# ── edition tables (四庫本 respellings) ──────────────────────────────────────
def is_siku(root, book, a):
    if getattr(a, 'siku', None) == 'on':
        return True
    if getattr(a, 'siku', None) == 'off':
        return False
    # Qing texts were written in Qianlong-era spellings to begin with: nothing to undo
    if scheme_for(book, None, root) == 'qm':
        return False
    return '四庫' in book_meta(root, book).get('edition', '') or book_title(book) != book and '四' in book


def edition_table(a, ph, book, cache={}):
    """Qianlong respellings (三史國語解 + aligned editions) for a 四庫本 book:
    variant (Qianlong form) -> row whose canonical is the older spelling.
    Rows are scoped: 元史 uses 元史 rows first. A Qianlong form that maps to
    several different old spellings is ambiguous and is left alone."""
    title = book_title(book, ph)
    if title in cache:
        return cache[title]
    rows = []
    for f in sorted(HERE.glob('equivalence_siku*.tsv')) + sorted(HERE.glob('equivalence_aligned*.tsv')):
        rows += Y.read_tsv(f)
    scope = {'辽史': '遼', '金史': '金', '元史': '元'}.get(title)
    by_new = defaultdict(list)
    for r in rows:
        r['variants_list'] = [v for v in r.get('variants', '').split('|') if v]
        r['exclude_list'] = []
        r['edition'] = True
        sc = r.get('scope', '')
        pri = 0 if (scope and sc in (scope, title)) else 1
        # key ONLY the Qianlong spelling (last in the row). The other old spellings in a
        # 國語解 row are Qianlong's own claims of identity, and some are conflations
        # (兀魯思 ulus and 斡羅思 Orus both became 俄羅斯).
        v = r['variants_list'][-1] if r['variants_list'] else ''
        if ph.t2s(v) != ph.t2s(r['canonical_zh']) and len(v) >= 2:
            by_new[ph.t2s(v)].append((pri, r))
    table = {}
    for v, lst in by_new.items():
        best = min(p for p, _ in lst)
        weight, row = defaultdict(int), {}
        for p, r in lst:
            if p == best:
                c = ph.t2s(r['canonical_zh'])
                weight[c] += int(r.get('count') or 1)      # aligned rows: occurrences
                row.setdefault(c, r)
        ranked = sorted(weight.items(), key=lambda t: -t[1])
        # Qianlong sometimes gave several old names one new spelling (俄羅斯 for both
        # 斡羅思 Orus and 兀魯思 ulus). Only a clear winner is restored; otherwise the
        # form stays as written and the tooltip lists the candidates.
        if len(ranked) == 1 or ranked[0][1] >= 3 * ranked[1][1]:
            table[v] = row[ranked[0][0]]
        else:
            table[v] = {'canonical_zh': v, 'variants_list': [v], 'exclude_list': [], 'edition': True,
                        'ambiguous': [(row[c]['canonical_zh'], w) for c, w in ranked[:4]], 'id': 'amb-' + v}
    cache[title] = table
    return table


# ── lexicon ──────────────────────────────────────────────────────────────────
def load_lexicon(ph, paths):
    entries, by_form = [], {}
    for p in paths:
        if not Path(p).exists():
            continue
        for e in Y.read_tsv(p):
            e['forms_list'] = [f for f in e.get('forms', '').split('|') if f]
            e['exclude_list'] = [ph.t2s(x) for x in (e.get('exclude') or '').split('|') if x]
            e.setdefault('status', 'attested')
            if e.get('family') not in FAMILIES:
                e['family'] = 'Other'
            entries.append(e)
            for f in e['forms_list']:
                # a curated row wins over a proposal for the same form
                key = ph.t2s(f)
                if key not in by_form or by_form[key]['status'] != 'attested':
                    by_form[key] = e
    return entries, by_form


def lexicon_paths(a):
    return [a.lexicon, a.proposed]


def load_rejected(a, ph):
    """Forms an LLM judged to be ordinary Chinese (is_transcription=false)."""
    p = Path(getattr(a, 'cache', '') or HERE / 'llm_cache.json')
    if not p.exists():
        return set()
    return {ph.t2s(k) for k, v in json.loads(p.read_text(encoding='utf-8')).items()
            if v.get('is_transcription') is False}


# ── transcription-character model ───────────────────────────────────────────
class ForeignModel:
    """score(c) = log P(c | transcribed names) / P(c | all text).
    High for 忽 兀 孛 斡; low for 之 以 而 曰."""

    def __init__(self, scores):
        self.s = scores
        self.floor = min(scores.values()) if scores else -3.0

    def __call__(self, c):
        return self.s.get(c, self.floor)

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def save(self, path):
        Path(path).write_text(json.dumps({k: round(v, 3) for k, v in self.s.items()},
                                         ensure_ascii=False), encoding='utf-8')

    def spans(self, s, lo=-0.7, strong=1.2, mean=1.0):
        """Maximal runs of transcription-like characters, weak ends trimmed.
        Yields (start, end) offsets into s (which should be t2s-normalised)."""
        for m in HZ.finditer(s):
            seg, base, i = m.group(), m.start(), 0
            while i < len(seg):
                if self(seg[i]) <= lo:
                    i += 1
                    continue
                j = i
                while j < len(seg) and self(seg[j]) > lo:
                    j += 1
                a, b = i, j
                while a < b and self(seg[a]) < .3:
                    a += 1
                while b > a and self(seg[b - 1]) < .3:
                    b -= 1
                if 2 <= b - a <= 8:
                    vals = [self(c) for c in seg[a:b]]
                    if sum(v > strong for v in vals) >= 2 and sum(vals) / len(vals) > mean:
                        yield base + a, base + b
                i = j


def train_model(ph, corpus, lex_entries, table_entries, alpha=300, top_common=120):
    heads = Y.bio_heads(corpus)
    fn, han = Counter(), Counter()
    for h in heads:
        om = BOOK_SCHEME.get(h['book']) == 'om'
        if om:   # native names: 本名/又作 in Liao–Ming histories (Tang 小字 are Han nicknames)
            for al in h['aliases']:
                fn.update(ph.t2s(al))
        n = ph.t2s(h['name'])
        clan = next((c for c in Y.CLANS if n.startswith(c)), None)
        if clan and not h['aliases']:
            # 完颜宗翰 has 本名粘没喝: then 宗翰 is a Han-style name and must not count
            fn.update(n[len(clan):])
        elif not clan and len(n) in (2, 3) and n[0] in Y.HAN_SURNAMES:
            han.update(n[1:])     # Han given names: the main source of false positives
    for e in lex_entries:
        for f in e['forms_list']:
            for c in ph.t2s(f):
                fn[c] += 3
    for e in table_entries:
        for f in e['variants_list']:
            for c in ph.t2s(f):
                fn[c] += 3
    for c in SEED_CHARS:
        fn[c] += 5

    txt, texts = Counter(), []
    for _, _, f in Y.corpus_files(corpus):
        for p in Y.paragraphs(f):
            s = ph.t2s(p)
            texts.append(s)
            txt.update(c for c in s if HZ.match(c))
    tt, th = sum(txt.values()), sum(han.values()) or 1
    vocab = set(txt) | set(fn)

    def bgp(c):   # background: half running text, half Han given names
        return .5 * (txt[c] + 1) / (tt + len(vocab)) + .5 * (han[c] + .01) / (th + .01 * len(vocab))

    # The most frequent characters of running text (不 之 亦 也 …) also occur in
    # names (不花, 也先), but as evidence they are worthless: cap them at neutral
    # so a candidate needs other, distinctive characters to qualify.
    common = {c for c, _ in txt.most_common(top_common)}

    def build(fn):
        tf = sum(fn.values())
        return ForeignModel({c: min(0.0, v) if c in common else v for c, v in
                             ((c, math.log(((fn[c] + alpha * bgp(c)) / (tf + alpha)) / bgp(c))) for c in vocab)})

    m = build(fn)
    # one bootstrap round: confident, recurring runs become extra positives
    boot = Counter()
    for s in texts:
        for i, j in m.spans(s, mean=2.0):
            boot[s[i:j]] += 1
    added = 0
    for r, n in boot.items():
        if n >= 3 and len(r) >= 3:
            fn.update(r)
            added += 1
    print(f'{len(heads)} biography subjects, {added} bootstrap names, {tt:,} characters', file=sys.stderr)
    return build(fn)


# ── resolution ───────────────────────────────────────────────────────────────
def resolve_unknown(ph, form, scheme, lex_entries, min_sound=.92):
    """No curated/proposed entry: try a sound-only match to the lexicon."""
    sk = {Y.consonants(Y.skeleton(v)) for v in ph.variants(form, scheme)}
    if max((len(x) for x in sk), default=0) < 3:
        return None
    best = None
    for e in lex_entries:
        if e['status'] != 'attested':
            continue
        s, _ = Y.score(ph, form, e['original'], scheme)
        if s >= min_sound and (not best or s > best[0]):
            best = (s, e)
    return best


# ── LLM proposals ────────────────────────────────────────────────────────────
PROMPT = """You are helping read Chinese dynastic histories. Each item is a string that may be a
Chinese transcription of a non-Chinese name, title or word. For each item decide:
- is_transcription: true/false (false if it is ordinary Chinese, e.g. a Han given name or a phrase)
- candidates: up to 3 possible ORIGINAL forms, most likely first, each with
  original (scholarly romanization of the source language), language, family (one of:
  {families}), gloss (short meaning, if known), source (a scholarly work or well-known attestation).
Only give candidates you can tie to a real attestation or standard reference. If you do not know,
return an empty list; an empty list is a good answer. Never invent a source.

The period reading of each item is given as consonant/vowel classes to help you.

Return ONLY a JSON array, one object per item, with keys: name, is_transcription, candidates.

Items:
{items}"""


def call_llm(prompt, model):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=model, max_tokens=4000,
                                 messages=[{'role': 'user', 'content': prompt}])
    return ''.join(b.text for b in msg.content if getattr(b, 'type', '') == 'text')


def parse_json_array(text):
    text = re.sub(r'```(?:json)?', '', text).strip()
    i, j = text.find('['), text.rfind(']')
    return json.loads(text[i:j + 1]) if i >= 0 and j > i else []


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_train(a, ph):
    lex, _ = load_lexicon(ph, lexicon_paths(a))
    tab, _ = Y.load_table(a.table, ph)
    m = train_model(ph, a.corpus, lex, tab)
    m.save(a.model)
    top = sorted(m.s, key=lambda c: -m(c))[:60]
    print(f'model -> {a.model}; most transcription-like: {"".join(top)}', file=sys.stderr)


ERA = {'mc': 0, 'om': 1, 'qm': 2}


def tables_for(a, ph, root, book, base, by_form_all):
    """For one book: variant table (plus 四庫 respellings for a 四庫本) and the
    lexicon forms allowed there. An entry from a later era is not matched in an
    earlier book (no Calicut, 古里, in the 旧唐书)."""
    era = ERA.get(scheme_for(book, a.scheme, root, ph), 0)
    by_form = {k: e for k, e in by_form_all.items() if ERA.get(e.get('scheme', 'mc'), 0) <= era}
    table = dict(base)
    if is_siku(root, book, a):
        for k, v in edition_table(a, ph, book).items():
            table.setdefault(k, v)
    known = set(by_form) | set(table)
    return table, known, max((len(k) for k in known), default=2), by_form


def collect(ph, a, books):
    """Detected transcribed names per book: form -> {count, context, scheme}."""
    model = ForeignModel.load(a.model)
    _, by_form_all = load_lexicon(ph, lexicon_paths(a))
    by_form = by_form_all
    _, base = Y.load_table(a.table, ph)
    rejected = load_rejected(a, ph)
    found = defaultdict(lambda: {'count': 0, 'context': '', 'book': '', 'scheme': ''})
    current, table = None, base
    for book, rel, f in Y.corpus_files(a.corpus, books):
        if book != current:
            current = book
            table, known, maxlen, by_form = tables_for(a, ph, a.corpus, book, base, by_form_all)
        sch = scheme_for(book, a.scheme, a.corpus, ph)
        for p in Y.paragraphs(f):
            s = ph.t2s(p)
            taken = [False] * len(s)
            i = 0
            ctx = {'table': table, 'by_form': by_form}
            while i < len(s):                      # known forms first (longest match)
                for L in range(min(maxlen, len(s) - i), 1, -1):
                    if s[i:i + L] in known and not excluded(ctx, s, i, L):
                        _note(found, s, i, L, book, sch)
                        taken[i:i + L] = [True] * L
                        i += L
                        break
                else:
                    i += 1
            for x, y in model.spans(s):
                if not any(taken[x:y]) and s[x:y] not in rejected:
                    _note(found, s, x, y - x, book, sch)
    return found, by_form, table


def _note(found, s, i, L, book, sch):
    d = found[s[i:i + L]]
    d['count'] += 1
    if not d['context']:
        d['context'], d['book'], d['scheme'] = s[max(0, i - 20):i + L + 20], book, sch


def describe(ph, form, by_form, table, lex_entries, scheme, sound=False):
    """-> (status, lexicon entry or None, canonical_zh, detail)"""
    eq = table.get(form)
    if eq and eq.get('ambiguous'):
        return 'ambiguous', None, form, ''
    canon = eq['canonical_zh'] if eq else form
    if eq and eq.get('edition'):
        # 俄羅斯 in a 四庫本 元史 may stand for 兀魯思 (ulus): judge by the old spelling
        keys = [ph.t2s(canon)] + [ph.t2s(v) for v in eq['variants_list'] if ph.t2s(v) != form]
    else:
        keys = [form] + ([ph.t2s(v) for v in eq['variants_list']] if eq else [])
    for key in keys:
        e = by_form.get(key)
        if e:
            return ('attested' if e['status'] == 'attested' else 'proposed'), e, canon, ''
    hit = resolve_unknown(ph, form, scheme, lex_entries) if sound else None
    if hit:
        return 'sound', hit[1], canon, f'sound match {hit[0]:.2f}'
    return 'unknown', None, canon, ''


def cmd_scan(a, ph):
    books = set(a.books.split(',')) if a.books else None
    found, by_form, table = collect(ph, a, books)
    lex, _ = load_lexicon(ph, lexicon_paths(a))
    rows, fam = [], Counter()
    for form, d in found.items():
        if d['count'] < a.min_count:
            continue
        st, e, canon, det = describe(ph, form, by_form, table, lex, d['scheme'], a.sound)
        rows.append((d['count'], form, st, e, canon, det, d))
        fam[(e['family'] if e else 'unknown', st)] += d['count']
    rows.sort(key=lambda r: -r[0])
    out = open(a.out, 'w', encoding='utf-8') if a.out else sys.stdout
    print('count\tform\tstatus\toriginal\tlanguage\tfamily\tcanonical_zh\tdetail\tbook\tcontext', file=out)
    for n, form, st, e, canon, det, d in rows:
        print(f'{n}\t{form}\t{st}\t{e["original"] if e else ""}\t{e["language"] if e else ""}\t'
              f'{e["family"] if e else ""}\t{canon}\t{det}\t{d["book"]}\t{d["context"]}', file=out)
    print(f'{len(rows)} names (count >= {a.min_count})', file=sys.stderr)
    for (f, st), n in sorted(fam.items(), key=lambda t: -t[1])[:20]:
        print(f'  {f:14}{st:9}{n:>7}', file=sys.stderr)


def cmd_propose(a, ph):
    books = set(a.books.split(',')) if a.books else None
    found, by_form, table = collect(ph, a, books)
    lex, _ = load_lexicon(ph, lexicon_paths(a))
    cache_p = Path(a.cache)
    cache = json.loads(cache_p.read_text(encoding='utf-8')) if cache_p.exists() else {}
    todo = []
    for form, d in sorted(found.items(), key=lambda t: -t[1]['count']):
        if d['count'] < a.min_count or form in cache:
            continue
        if describe(ph, form, by_form, table, lex, d['scheme'], a.sound)[0] != 'unknown':
            continue
        todo.append((form, d))
        if len(todo) >= a.top:
            break
    print(f'{len(todo)} unknown names to ask about ({len(cache)} cached)', file=sys.stderr)

    mock = json.loads(Path(a.mock).read_text(encoding='utf-8')) if a.mock else None
    for k in range(0, len(todo), a.batch):
        chunk = todo[k:k + a.batch]
        items = '\n'.join(
            f'- {form}  [{d["scheme"]} reading: '
            f'{" / ".join(sorted({Y.skeleton(v) for v in ph.variants(form, d["scheme"])})[:3])}]  '
            f'context ({d["book"]}): …{d["context"]}…' for form, d in chunk)
        prompt = PROMPT.format(families=', '.join(FAMILIES), items=items)
        if a.dry_run:
            print(prompt)
            return
        if mock is not None:
            answers = [m for m in mock if m.get('name') in {f for f, _ in chunk}]
        else:
            answers = parse_json_array(call_llm(prompt, a.model_name))
        for ans in answers:
            name = ans.get('name')
            d = dict(chunk).get(name)
            if d is None:
                continue
            verified = []
            for c in ans.get('candidates', [])[:3]:
                if not c.get('original'):
                    continue
                s, _ = Y.score(ph, name, c['original'], d['scheme'])
                c['sound_score'] = round(s, 3)
                c['kept'] = s >= a.min_verify
                verified.append(c)
            cache[name] = {'is_transcription': ans.get('is_transcription'), 'candidates': verified,
                           'model': 'mock' if mock is not None else a.model_name, 'book': d['book']}
        cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding='utf-8')

    # rewrite the proposed lexicon from the cache: best kept candidate per name
    rows = []
    for name, r in sorted(cache.items()):
        kept = [c for c in r['candidates'] if c.get('kept')]
        if not r.get('is_transcription') or not kept:
            continue
        c = max(kept, key=lambda c: c['sound_score'])
        fam = c.get('family') if c.get('family') in FAMILIES else 'Other'
        rows.append([f'llm-{name}', c['original'], c.get('language', ''), fam, c.get('gloss', ''), name,
                     'name-element', scheme_for(r.get('book', '')), f'{c.get("source", "")} '
                     f'(model: {r["model"]}; sound {c["sound_score"]}; source not checked)', 'llm-proposed'])
    with open(a.proposed, 'w', encoding='utf-8') as f:
        f.write('# Generated by `yiming.py propose`. Rows are LLM proposals that passed the sound check.\n'
                '# Move a row to lexicon.tsv (status attested) once you have checked its source.\n')
        f.write('id\toriginal\tlanguage\tfamily\tgloss\tforms\tkind\tscheme\tsource\tstatus\n')
        for r in rows:
            f.write('\t'.join(x.replace('\t', ' ') for x in r) + '\n')
    rejected = sum(1 for r in cache.values() for c in r['candidates'] if not c.get('kept'))
    print(f'{len(rows)} proposals kept -> {a.proposed}; {rejected} candidates rejected by the sound check',
          file=sys.stderr)


# ── reading view ─────────────────────────────────────────────────────────────
CSS = """
:root{--paper:#f5f6f3;--ink:#1f2328;--muted:#5d646c;--rule:#d5d9dd;
 --Iranian:#1d6b74;--Turkic:#9a3b1f;--Mongolic:#3b4f9a;--Para-Mongolic:#6a4c93;--Tungusic:#2f7a3b;
 --Tibetic:#b8322a;--Indic:#9a5f10;--Dravidian:#8a6a1f;--Semitic:#8a2f5a;--Austronesian:#0b7c99;
 --European:#4d6480;--Other:#555b61;--unknown:#8a9096}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--paper:#16191c;--ink:#e6e8ea;--muted:#9aa3ab;--rule:#2c3238;
 --Iranian:#6cc3cc;--Turkic:#e98f6f;--Mongolic:#9fb0f0;--Para-Mongolic:#c3a6ec;--Tungusic:#83cf90;
 --Tibetic:#f08a80;--Indic:#e5b25e;--Dravidian:#d8bd72;--Semitic:#e58bb6;--Austronesian:#6fd0e6;
 --European:#a9bdd6;--Other:#b3b9bf;--unknown:#7d848a}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:"Noto Serif TC","Noto Serif SC","Source Han Serif","Songti TC","Songti SC",serif;font-size:19px;line-height:2.4}
main{max-width:36em;margin:0 auto;padding:3rem 1.25rem 5rem}
h1{font-size:1.5rem;font-weight:600;letter-spacing:.08em;margin:0 0 .3rem;line-height:1.5}
.sub{color:var(--muted);font-size:.78rem;line-height:1.7;margin:0 0 1rem}
.key{display:flex;flex-wrap:wrap;gap:.3rem 1rem;font-size:.72rem;line-height:1.6;margin:0 0 2.5rem;color:var(--muted)}
.key span::before{content:"";display:inline-block;width:.7em;height:.7em;margin-right:.35em;background:var(--c);vertical-align:-.05em}
p{margin:0 0 1.2em;text-align:justify;text-justify:inter-ideograph}
.n{position:relative;cursor:help;text-decoration-line:underline;text-underline-offset:.3em;
 text-decoration-color:var(--c);text-decoration-thickness:2px}
.n.proposed{text-decoration-style:dashed}
.n.sound{text-decoration-style:dashed;text-decoration-thickness:1px}
.n.unknown{text-decoration-style:dotted;text-decoration-thickness:1.5px}
.n.ambiguous{text-decoration-style:wavy;text-decoration-thickness:1px}
.n:focus{outline:2px solid var(--c);outline-offset:2px}
rt{font-family:"Noto Serif","Source Serif 4",Georgia,serif;font-size:.5em;color:var(--c);letter-spacing:0;font-style:italic}
.was{font-size:.55em;color:var(--muted);vertical-align:-.1em;margin-left:.05em}
.tip{display:none;position:absolute;left:0;top:100%;z-index:2;width:max-content;max-width:22em;
 background:var(--paper);border:1px solid var(--rule);border-left:3px solid var(--c);
 padding:.5em .75em;font-size:.72rem;line-height:1.65;color:var(--ink);text-align:left;font-style:normal}
.n:hover .tip,.n:focus .tip{display:block}
.tip b{font-weight:600}
aside{margin-top:3rem;border-top:1px solid var(--rule);padding-top:1rem;font-size:.78rem;line-height:1.8}
aside h2{font-size:.9rem;font-weight:600;margin:1.2rem 0 .3rem;color:var(--c)}
aside table{border-collapse:collapse;width:100%}
aside td{padding:.15em .8em .15em 0;vertical-align:top}
aside td:first-child{white-space:nowrap}
"""
STATUS_NOTE = {'ambiguous': '四庫本 respelling that stands for more than one older name; left as written',
               'attested': 'identification from the curated lexicon',
               'proposed': 'LLM proposal; passed the sound check; source not verified',
               'sound': 'sound match only; not an attested identification',
               'unknown': 'looks like a transcription; original not known'}


def excluded(ctx, s, i, k):
    """True if this occurrence sits inside an exclusion string of its entry."""
    form = s[i:i + k]
    exs = []
    for e in (ctx['table'].get(form), ctx['by_form'].get(form)):
        if e:
            exs += e.get('exclude_list', [])
    return any(ex in s[max(0, i - 6):i + k + 6] and _covers(s, i, k, ex) for ex in exs)


def _covers(s, i, k, ex):
    lo = max(0, i - len(ex) + 1)
    return any(s[j:j + len(ex)] == ex and j <= i and j + len(ex) >= i + k for j in range(lo, i + 1))


def render_paragraph(p, ctx, sch, seen):
    ph, forms_known, maxlen, model = ctx['ph'], ctx['known'], ctx['maxlen'], ctx['model']
    if 'trad' not in ctx:
        ctx['trad'] = ph.is_traditional(p)
    s = ph.t2s(p)
    # where do known forms start? an unknown span must stop before them
    # (亦突厥 -> 突厥 is known; don't let the detector swallow it)
    known_at = set()
    for k in range(len(s)):
        for L in range(min(maxlen, len(s) - k), 1, -1):
            if s[k:k + L] in forms_known and not excluded(ctx, s, k, L):
                known_at.add(k)
                break
    spans = {}
    if model:
        for x, y in model.spans(s, mean=ctx['unknown_mean']):
            cut = next((k for k in range(x, y) if k in known_at), y)
            if cut - x >= 2 and s[x:cut] not in ctx['rejected'] and s[x:cut] not in forms_known:
                spans[x] = cut
    out, i = [], 0
    while i < len(s):
        L = 0
        for k in range(min(maxlen, len(s) - i), 1, -1):
            if s[i:i + k] in forms_known and not excluded(ctx, s, i, k):
                L = k
                break
        if not L and i in spans:
            L = spans[i] - i
        if not L:
            out.append(html.escape(p[i]))
            i += 1
            continue
        out.append(render_name(p, s, i, L, ctx, sch, seen))
        i += L
    return ''.join(out)


def render_name(p, s, i, L, ctx, sch, seen):
    ph = ctx['ph']
    form, orig = s[i:i + L], p[i:i + L]
    key = (form, sch)
    if key not in ctx['memo']:
        ctx['memo'][key] = describe(ph, form, ctx['by_form'], ctx['table'], ctx['lex'], sch, ctx['sound'])
    st, e, canon, det = ctx['memo'][key]
    mention = s[max(0, i - 2):i] in Y.MENTION
    changed = ph.t2s(canon) != form and not mention
    fam = e['family'] if e and st not in ('unknown', 'ambiguous') else 'unknown'
    if changed:
        canon = ph.to_script(canon, ctx['trad'])      # 蒙哥 in a traditional passage: 蒙哥; 拖雷, not 拖雷 in 简体
    shown = canon if changed else orig
    top = (e['original'] or f"‹{e['language']}›") if e else ''
    if ctx['display'] == 'latin' and e and e['original'] and not mention:
        shown, top = e['original'], canon
    body = f'<ruby>{html.escape(shown)}<rt>{html.escape(top)}</rt></ruby>' if top else html.escape(shown)
    if changed:
        body += f'<span class="was">{html.escape(orig)}</span>'
    tip = [f'<b>{html.escape(e["original"] or "original form unknown")}</b> · {html.escape(e["language"])}'
           if e else ('<b>which older name?</b>' if st == 'ambiguous' else '<b>origin unknown</b>')]
    amb = ctx['table'].get(form, {}).get('ambiguous')
    if amb:
        opts = []
        for c, w in amb:
            le = ctx['by_form'].get(ph.t2s(c))
            opts.append(f'{ph.to_script(c, ctx["trad"])}' + (f' ({le["original"]})' if le and le['original'] else '')
                        + f' ×{w}')
        tip.append('Qianlong used this spelling for several older names: ' + html.escape(' / '.join(opts)))
    if e and e.get('gloss'):
        tip.append(html.escape(e['gloss']))
    if changed:
        tip.append(f'text has {html.escape(orig)}; shown as {html.escape(canon)}')
    eqrow = ctx['table'].get(form)
    if eqrow and eqrow.get('edition') and not eqrow.get('ambiguous'):
        tip.append(f'四庫本 respelling (Qianlong era); older spelling {html.escape(canon)}')
    eq = ctx['table'].get(form)
    if eq and len(eq['variants_list']) > 1:
        tip.append('also written ' + html.escape('、'.join(eq['variants_list'])))
    elif e and len(e['forms_list']) > 1:
        tip.append('also written ' + html.escape('、'.join(e['forms_list'])))
    if e and e.get('entity'):
        others = [o for o in ctx['lex'] if o.get('entity') == e['entity'] and o is not e]
        if others:
            tip.append('same entity also appears as ' + html.escape(
                '、'.join(f'{o["forms_list"][0]} ({o["original"]})' for o in others)))
    prev = s[i - 1] if i else ''
    if prev in SOGDIAN_SURNAMES and sch == 'mc' and fam in ('Iranian', 'unknown'):
        tip.append(f'preceded by {prev}: surname of Sogdians from {SOGDIAN_SURNAMES[prev]} (昭武九姓); '
                   f'also an ordinary Han surname')
    tip.append(f'<i>{STATUS_NOTE[st]}{"; " + det if det else ""}</i>')
    if e and e.get('source'):
        tip.append('source: ' + html.escape(e['source']))
    rec = seen.setdefault((canon, e['id'] if e else form), {'forms': Counter(), 'e': e, 'st': st, 'fam': fam})
    rec['forms'][orig] += 1
    return (f'<span class="n {st}" style="--c:var(--{fam})" tabindex="0">{body}'
            f'<span class="tip" role="tooltip">{"<br>".join(tip)}</span></span>')


def make_ctx(ph, a):
    lex, by_form = load_lexicon(ph, lexicon_paths(a))
    _, base = Y.load_table(a.table, ph)
    model = ForeignModel.load(a.model) if (not a.known_only and Path(a.model).exists()) else None
    return {'ph': ph, 'lex': lex, 'by_form': by_form, 'by_form_all': by_form, 'base': base, 'model': model,
            'display': a.display, 'memo': {}, 'sound': a.sound, 'unknown_mean': a.unknown_mean,
            'rejected': load_rejected(a, ph), 'book': None}


def locate(f, root):
    """(book name, corpus root) for a file: the folder right under the corpus root."""
    f = Path(f).resolve()
    if root:
        root = Path(root).resolve()
        if (root / 'meta.json').exists() or not any(p.is_dir() for p in root.iterdir()):
            return root.name, root.parent          # root IS a book folder
        rel = f.relative_to(root)
        if len(rel.parts) > 1:
            return rel.parts[0], root
    # single file: walk up to a folder that looks like a book
    for d in f.parents:
        if (d / 'meta.json').exists() or book_title(d.name) in BOOK_SCHEME:
            return d.name, d.parent
    return f.parent.name, f.parent.parent


def set_book(ctx, a, root, book):
    if ctx['book'] == (root, book):
        return
    ctx['book'] = (root, book)
    ctx['table'], ctx['known'], ctx['maxlen'], ctx['by_form'] = tables_for(
        a, ctx['ph'], root, book, ctx['base'], ctx['by_form_all'])
    ctx['memo'] = {}


def render_html(ph, a, files, root):
    ctx = make_ctx(ph, a)
    seen, body = {}, []
    for f in files:
        book, broot = locate(f, root)
        set_book(ctx, a, broot, book)
        sch = scheme_for(book, a.scheme, broot, ph)
        if len(files) > 1:
            body.append(f'<p class="sub">{html.escape(str(f.relative_to(root)))}</p>')
        paras = Y.paragraphs(f)
        ctx['trad'] = ph.is_traditional(''.join(paras))     # script of the whole file
        body += [f'<p>{render_paragraph(p, ctx, sch, seen)}</p>' for p in paras]

    fam_count = Counter()
    for rec in seen.values():
        fam_count[rec['fam']] += sum(rec['forms'].values())
    key = ''.join(f'<span style="--c:var(--{f})">{f} {fam_count[f]}</span>'
                  for f in FAMILIES + ['unknown'] if fam_count[f])
    index = []
    for f in FAMILIES + ['unknown']:
        recs = [(k, r) for k, r in seen.items() if r['fam'] == f]
        if not recs:
            continue
        recs.sort(key=lambda t: -sum(t[1]['forms'].values()))
        rows = ''.join(
            f'<tr><td>{html.escape(k[0])}</td><td>{html.escape(r["e"]["original"]) if r["e"] else ""}</td>'
            f'<td>{html.escape("、".join(r["forms"]))}</td><td>{sum(r["forms"].values())}×</td>'
            f'<td>{r["st"]}</td></tr>' for k, r in recs[:200])
        index.append(f'<section style="--c:var(--{f})"><h2>{f if f != "unknown" else "Origin unknown"}</h2>'
                     f'<table>{rows}</table></section>')
    title = html.escape(a.title or (root.stem if root else 'reading'))
    return (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title><style>{CSS}</style></head><body><main>'
            f'<h1>{title}</h1>'
            f'<p class="sub">Above each foreign name: its form in the original language, coloured by language '
            f'family. Solid line: attested identification. Dashed: proposal or sound match. Dotted grey: looks '
            f'transcribed, origin unknown. Small grey text after a name: the spelling this passage uses, when '
            f'the name is shown in its unified form. Hover or tab to a name for details.</p>'
            f'<p class="key">{key}</p>'
            + ''.join(body)
            + f'<aside>{"".join(index) or "No transcribed names found."}</aside></main></body></html>'), seen


# ── book site: one page per chapter, plus a book index and a name index ─────
NAV_CSS = """
nav.top{display:flex;justify-content:space-between;gap:1rem;font-size:.78rem;line-height:1.6;margin:0 0 1.5rem;color:var(--muted)}
nav.top a,.toc a,.names a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule)}
nav.top a:hover,.toc a:hover,.names a:hover{border-bottom-color:var(--ink)}
.toc{list-style:none;padding:0;margin:0;font-size:.9rem;line-height:1.9}
.toc li{display:flex;align-items:center;gap:.8rem;border-bottom:1px solid var(--rule);padding:.15rem 0}
.toc .t{flex:0 0 14em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{flex:1;display:flex;height:.55rem;min-width:0}
.bar i{display:block;height:100%;background:var(--c)}
.toc .cnt{flex:0 0 3.5em;text-align:right;color:var(--muted);font-size:.75rem}
.toc a.t{border-bottom:none}
.bar i.u{opacity:.35}
.meta{font-size:.78rem;color:var(--muted);line-height:1.7;margin:0 0 1.5rem}
.names section{margin-bottom:1.5rem}
.names h2{font-size:.95rem;color:var(--c);margin:.2rem 0 .4rem}
.names table{border-collapse:collapse;width:100%;font-size:.82rem;line-height:1.7}
.names td{padding:.1rem .8rem .1rem 0;border-bottom:1px solid var(--rule);vertical-align:top}
.names td:first-child{white-space:nowrap}
.names i{color:var(--c)}
@media (max-width:640px){.toc .t{flex-basis:8em}}
"""


def chapter_label(f, root):
    rel = Path(f).relative_to(root)
    stem = rel.stem.replace('-原文', '')
    m = re.search(r'卷[一二三四五六七八九十百零〇]+', stem)
    label = m.group(0) if m else (f'卷{int(stem)}' if stem.isdigit() else stem)
    section = rel.parts[-2] if len(rel.parts) > 1 else ''
    return f'{section} {label}'.strip()


def page(title, body, extra_css=''):
    return (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}{NAV_CSS}{extra_css}</style></head>'
            f'<body><main>{body}</main></body></html>')


def fam_bar(counter, total_max):
    parts = ''.join(f'<i{" class=u" if f == "unknown" else ""} style="--c:var(--{f});width:{100 * counter[f] / total_max:.1f}%"></i>'
                    for f in FAMILIES + ['unknown'] if counter[f])
    return f'<span class="bar">{parts}</span>'


def render_site(ph, a, files, root, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ctx = make_ctx(ph, a)
    book = Path(root).name
    title = a.title or book
    files = sorted(files, key=lambda f: _natural(Path(f).relative_to(root)))
    chapters, allnames = [], {}
    for k, f in enumerate(files):
        bk, broot = locate(f, root)
        set_book(ctx, a, broot, bk)
        sch = scheme_for(bk, a.scheme, broot, ph)
        seen = {}
        plist = Y.paragraphs(f)
        ctx['trad'] = ph.is_traditional(''.join(plist))
        paras = ''.join(f'<p>{render_paragraph(p, ctx, sch, seen)}</p>' for p in plist)
        fam = Counter()
        for key, rec in seen.items():
            n = sum(rec['forms'].values())
            fam[rec['fam']] += n
            nk = (ph.t2s(key[0]), key[1] if rec['e'] else ph.t2s(key[1]))
            g = allnames.setdefault(nk, {'forms': Counter(), 'e': rec['e'], 'st': rec['st'], 'label': key[0],
                                         'fam': rec['fam'], 'chapters': Counter()})
            g['forms'].update(rec['forms'])
            g['chapters'][k] += n
        label = chapter_label(f, root)
        chapters.append((label, fam))
        prev = f'<a href="{k - 1:04d}.html">← {html.escape(chapter_label(files[k - 1], root))}</a>' if k else '<span></span>'
        nxt = (f'<a href="{k + 1:04d}.html">{html.escape(chapter_label(files[k + 1], root))} →</a>'
               if k + 1 < len(files) else '<span></span>')
        key_html = ''.join(f'<span style="--c:var(--{x})">{x} {fam[x]}</span>' for x in FAMILIES + ['unknown'] if fam[x])
        body = (f'<nav class="top">{prev}<a href="index.html">{html.escape(title)} · 目录</a>'
                f'<a href="names.html">名字索引</a>{nxt}</nav>'
                f'<h1>{html.escape(title)} · {html.escape(label)}</h1><p class="key">{key_html}</p>{paras}')
        (outdir / f'{k:04d}.html').write_text(page(f'{title} {label}', body), encoding='utf-8')
        print(f'\r{k + 1}/{len(files)} {label}', end='', file=sys.stderr)
    print(file=sys.stderr)

    # book index
    tot = Counter()
    for _, fam in chapters:
        tot.update(fam)
    mx = max((sum(f.values()) for _, f in chapters), default=1) or 1
    rows = ''.join(f'<li><a class="t" href="{k:04d}.html">{html.escape(lbl)}</a>{fam_bar(fam, mx)}'
                   f'<span class="cnt">{sum(fam.values())}</span></li>' for k, (lbl, fam) in enumerate(chapters))
    meta = book_meta(Path(root).parent, book)
    sch = scheme_for(book, a.scheme, Path(root).parent, ph)
    info = ' · '.join(x for x in [meta.get('dynasty', ''), meta.get('author', ''), meta.get('edition', ''),
                                  f'phonology {sch}', '四庫本: Qianlong respellings undone' if is_siku(Path(root).parent, book, a) else '']
                      if x)
    key_html = ''.join(f'<span style="--c:var(--{x})">{x} {tot[x]}</span>' for x in FAMILIES + ['unknown'] if tot[x])
    body = (f'<nav class="top"><span></span><a href="names.html">名字索引 · name index</a></nav>'
            f'<h1>{html.escape(title)}</h1><p class="meta">{html.escape(info)}<br>{len(chapters)} chapters · '
            f'{len(allnames)} distinct names · bars show foreign names per chapter by language family</p>'
            f'<p class="key">{key_html}</p><ul class="toc">{rows}</ul>')
    (outdir / 'index.html').write_text(page(title, body), encoding='utf-8')

    # name index
    secs = []
    for fam in FAMILIES + ['unknown']:
        recs = [(k, r) for k, r in allnames.items() if r['fam'] == fam]
        if not recs:
            continue
        recs.sort(key=lambda t: -sum(t[1]['forms'].values()))
        trs = ''.join(
            f'<tr><td>{html.escape(r["label"])}</td><td><i>{html.escape(r["e"]["original"] or r["e"]["language"]) if r["e"] else ""}</i></td>'
            f'<td>{html.escape("、".join(r["forms"]))}</td><td>{sum(r["forms"].values())}×</td><td>'
            + ' '.join(f'<a href="{c:04d}.html">{html.escape(chapters[c][0])}</a>' for c, _ in r['chapters'].most_common(6))
            + '</td></tr>' for k, r in recs[:a.index_limit])
        secs.append(f'<section style="--c:var(--{fam})"><h2>{fam if fam != "unknown" else "Origin unknown"} '
                    f'({len(recs)})</h2><table>{trs}</table></section>')
    body = (f'<nav class="top"><a href="index.html">← {html.escape(title)} · 目录</a><span></span></nav>'
            f'<h1>{html.escape(title)} · 名字索引</h1><div class="names">{"".join(secs)}</div>')
    (outdir / 'names.html').write_text(page(f'{title} 名字索引', body), encoding='utf-8')
    return len(chapters), len(allnames), tot


def _natural(rel):
    """Sort 卷二 before 卷十一: Chinese numerals and digits by value."""
    def num(s):
        d = dict(zip('〇零一二三四五六七八九', [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
        total, cur = 0, 0
        for c in s:
            if c in d:
                cur = d[c]
            elif c == '十':
                total += (cur or 1) * 10; cur = 0
            elif c == '百':
                total += (cur or 1) * 100; cur = 0
        return total + cur
    order = {'本纪': 0, '帝纪': 0, '纪': 0, '世家': 2, '志': 3, '书': 3, '八书': 3, '表': 4, '十表': 4,
             '列传': 5, '传': 5, '七十列传': 5}
    parts = rel.parts
    sec = order.get(parts[-2], 1) if len(parts) > 1 else 1
    m = re.search(r'卷([一二三四五六七八九十百零〇]+)', rel.stem)
    if m:
        return (sec, num(m.group(1)), str(rel))
    m = re.search(r'\d+', rel.stem)
    return (sec, int(m.group(0)) if m else 0, str(rel))
