# yiming 異名

**Reveal the foreign names hidden in Chinese histories.**

[English](README.md) · [简体中文](README.zh-CN.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [Tiếng Việt](README.vi.md)

![禄山 shown with its Sogdian original Roxšan; the tooltip explains the name and the 安 surname](docs/img/anlushan.png)

## Why this exists

Chinese histories record foreign people, peoples and places in Chinese characters, and that hides where the names came from.

- **The original name disappears.** The rebel 安禄山 was named 禄山, which was Sogdian *Roxšan*, "bright", from the same root as Greek *Roxana*. Read in modern Mandarin, *Lùshān* tells you nothing. In the Tang pronunciation, *luk-ʂɛn*, the match is obvious.
- **One name, many spellings.** The Oirats appear as 斡亦剌, 瓦剌, 厄鲁特 and 卫拉特 in different centuries. The Ottomans are 鲁迷 (Rūm, "Rome") in the Ming, 控噶尔 in the Qing and 土耳其 later.
- **Later editors made it worse.** For the 《四库全书》, the Qianlong emperor had nearly every Liao, Jin and Yuan name respelled: 伯颜 became 巴延, 脱脱 became 托克托, 拔都 became 巴图. Most digital texts online are 四库 editions.

yiming reads a Chinese history and **writes the original-language form above each foreign name**, coloured by language family. It shows different spellings of the same name in one consistent form, and it undoes Qianlong's respellings. The text is never altered: the spelling actually used in the passage always stays visible.

## What it can do now

- **Reading view.** Each foreign name gets its original form above it (*Roxšan*, *Bayan*, *Rūm*), a colour for its language family (12 families), and an underline showing how certain the identification is. Hovering shows the language, meaning, source, other spellings and other names of the same thing.
- **Period pronunciation.** Names are compared by how they sounded when written:
  - Middle Chinese (切韵) for Han–Tang texts;
  - an Old Mandarin approximation for Song–Ming;
  - a Qing Mandarin approximation for the Qing.
  
  Known transcription habits are built in. For example, the Tang used a *-t* ending for foreign *-r/-l* (阙 = *kül*).
- **Any book, not only the 二十四史.** It downloads texts from the Kanripo repository (about 9,000 titles) and picks the right pronunciation from the book's period.
- **四库本 restoration.** Qianlong's respellings are undone using the 《钦定辽金元三史国语解》 (about 7,400 pairs) and by comparing two editions of the same book line by line (about 3,600 pairs for the 元史 annals). When one Qianlong spelling replaced several older names, yiming does not guess: it marks the name and lists the candidates.
- **Book sites.** A whole book becomes a small website: one page per chapter, a contents page with bars showing the foreign names per chapter, and a name index linking each name to the chapters where it appears.
- **Discovery tools.**
  - Index every transcribed name in a book.
  - Find names that sound alike but are spelled differently (possible "one person, two biographies" cases).
  - Optionally ask an LLM to propose originals for unknown names. Each proposal is kept only if its sound matches the period pronunciation.
- **Measured accuracy.** An evaluation command reports how often true and false identifications pass the sound check (see [Accuracy](#accuracy)).

## Quick start

### 1. Install

Python 3.8 or newer. No third-party package is required.

```bash
git clone https://github.com/<you>/yiming.git
cd yiming
python yiming.py setup          # builds the variant-character table (needs internet once)
```

Optional extras:

| Package | Needed for |
|---|---|
| `pypinyin` | characters missing from the rhyme books |
| `anthropic` | the `propose` command |
| `opencc` | rebuilding `mc_table.json` |

### 2. Get texts

Choose either source, or both.

```bash
# (a) The 二十四史 from hunterhug/china-history (about 250 MB)
git clone --depth 1 https://github.com/hunterhug/china-history.git corpus

# (b) Any title from Kanripo, by name or KR id
python yiming.py fetch 资治通鉴 --corpus corpus --juan 214
python yiming.py fetch 大唐西域记 --corpus corpus
```

### 3. Read

```bash
# one chapter -> one page
python yiming.py read corpus/旧唐书/列传/第一百五十章-卷一百五十-原文.html -o anlushan.html

# a whole book -> a browsable site (no .html in the output name)
python yiming.py read corpus/元史 -o yuan_site
```

Open the HTML in a browser. Ready-made examples are in [`samples/`](samples/).

## How to read the page

**Above the name:** the original-language form in italics. If only the language is known, it shows as ‹Khitan›.

**Colour = language family**

| Family | Examples |
|---|---|
| Iranian (Sogdian, Bactrian, Parthian, Khotanese, Persian) | 禄山 *Roxšan*, 粟特 *Soγd*, 安息 *Aršak*, 哈烈 *Herāt* |
| Turkic | 突厥 *Türk*, 可汗 *qaγan*, 回纥 *Uyγur*, 鲁迷 *Rūm* |
| Mongolic | 帖木儿 *Temür*, 拔都 *ba'atur*, 斡罗思 *Orus* |
| Para-Mongolic (Khitan, Xianbei) | 契丹 *Kitan*, 拓跋 *Tabγač*, 耶律 |
| Tungusic (Jurchen, Manchu) | 女真 *Jürchen*, 勃极烈 *bogile*, 贝勒 *beile* |
| Tibetic | 喇嘛 *bla ma*, 拉萨 *Lha sa* |
| Indic (Sanskrit, Pali) | 佛陀 *Buddha*, 阿罗汉 *arhat*, 鸠摩罗什 |
| Dravidian | 古里 *Kōḻikkōṭ* (Calicut), 柯枝 *Kochi* |
| Semitic (Syriac, Arabic) | 移鼠 *Išoʿ* (Jesus), 默德那 *al-Madīna* |
| Austronesian | 满剌加 *Melaka*, 爪哇 *Jawa*, 吕宋 *Luzon* |
| European | 和兰 *Holland*, 利玛窦 *Matteo Ricci* |
| Other / unknown | 勃律 *Bolor*; grey means the origin is not known yet |

**Underline = how certain the identification is**

| Line | Meaning |
|---|---|
| solid | Attested identification from the curated lexicon, with a source |
| dashed | An LLM proposal that passed the sound check; the source is not yet verified |
| dotted grey | Looks like a transcription; original not known |
| wavy grey | A 四库 respelling that stood for more than one older name; hover to see the candidates |

**Small grey text after a name:** the spelling the passage actually uses, shown when yiming displays the name in its unified form.

**Tooltip** (hover, or Tab with the keyboard): language, meaning, source, other spellings, and other names of the same thing (鲁迷 ↔ 控噶尔 ↔ 土耳其). In Tang books, a name after 安, 康, 石, 米, 何, 史 or 曹 also gets a hint about the Sogdian city that surname points to.

## Features in detail

### Period pronunciation and sound matching

Each character's position in the 切韵 rhyme system comes from the nk2028 `qieyun` data (CC0). A name becomes a string of sound classes: onset, vowel and coda. For example, 禄山 becomes `LuK SaN` and *Roxšan* becomes `RuH SaN`.

Two names, or a name and a romanized original, are compared by a weighted edit distance. Known transcription habits cost little:

- *l* ↔ *r*;
- *k* ↔ *x/h*;
- Tang *-t* for foreign *-r/-l*;
- north-western denasalisation, so 默 can stand for *b-* (默啜 = *Bäg Čor*);
- dropped final consonants (颉利 = *Illig*).

| Scheme | Used for | Main rules |
|---|---|---|
| `mc` | Han–Tang–Five Dynasties sources | 切韵 initials; codas *-p -t -k -m -n -ŋ* kept |
| `om` | Song, Liao, Jin, Yuan, Ming | entering-tone codas lost; 疑 becomes a zero initial; 日 ≈ *r* |
| `qm` | Qing | as `om`, and *-m* merges into *-n*; the 尖/团 split is kept, as Qing transcribers of Manchu did |

The scheme is chosen by the **period of the sources**, not the compiler. The 明史 was compiled under the Qing from Ming records, so it uses `om`. The choice comes from a title table, then from the dynasty recorded when the book was fetched. You can always override it with `--scheme`.

**Era filter:** a lexicon entry never matches in a book older than its earliest attested form. So 古里 is Calicut in Ming texts, but not in the 旧唐书.

### Names: lexicon, spellings, entities

| Table | What it holds |
|---|---|
| `lexicon.tsv` | 123 curated entries: original, language, family, gloss, Chinese forms, source |
| `equivalence.tsv` | Different spellings of the same name, unified into one displayed form |
| `entity` column | Different **names** for one thing. They are linked, never merged. |

Simplified and traditional characters both match. About 21,000 variant shapes (竒 → 奇) are normalised.

### Other books: Kanripo

```bash
python yiming.py fetch KR2a0036 --corpus corpus --juan 1-47 --name 元史_四库
```

The text is cleaned into `corpus/<title>/NNN.txt`. The compiler's dynasty is saved in `meta.json`. 四库 texts have no punctuation, so paragraphs follow the page breaks.

### 四库本: undoing Qianlong's respellings

1. `guoyujie` harvests the 《三史国语解》, giving Qianlong spelling → older spelling. Qianlong's claimed "Manchu/Mongol meanings" are **not** used, because many are reinterpretations.
2. `align A B` compares two editions of the same book, chapter by chapter, and keeps every short span that differs and looks like a transcription. The Qianlong spelling must not occur in the older edition.
3. When reading a book fetched from Kanripo, respellings are restored automatically and the 四库 spelling stays visible in grey. When one Qianlong spelling replaced several old names (俄罗斯 for both 斡罗思 *Orus* and 兀鲁思 *ulus*), the name is left as written with a wavy line, and the tooltip lists the candidates with counts.
4. Qing texts are never "restored", because they were written in those spellings.

![四库本 元史: 巴图 restored to 拔都 (ba'atur), with the 四库 spelling in grey](docs/img/siku.png)

### Book sites

`read BOOK_DIR -o OUT_DIR` writes:

- `index.html`: contents, with a bar per chapter coloured by language family;
- one page per chapter, with previous/next links;
- `names.html`: every name, grouped by family, with counts and links to chapters.

The 旧唐书's 201 chapters take about 6 seconds.

### Discovery tools

| Command | What it does |
|---|---|
| `scan` | A TSV of every transcribed name in a book: count, status, original, family, first context |
| `twins` | Names that sound alike but are spelled differently, e.g. 萧得里底 / 萧迭里得. This is a review queue, not findings. |
| `propose` (experimental) | Sends unknown names, with their period reading and a context line, to an LLM. Strings the LLM judges to be ordinary Chinese are suppressed. Proposed originals are kept only if the sound matches (score ≥ 0.60), and they show dashed. Answers are cached. **So far tested only with mock answers.** |

### Accuracy

This is from `python yiming.py eval gold_pairs.tsv --corpus corpus` (see `samples/eval.txt`).

**Chinese form vs original:** 166 true pairs from the lexicon, against 19,920 wrong pairs.

| Threshold | True identifications kept | Wrong ones kept |
|---|---|---|
| 0.55 | 78% | 4.0% |
| **0.60** (default for `propose`) | 72% | 2.2% |
| 0.70 | 54% | 0.75% |

**Spelling vs spelling:** 19 attested pairs, against 20,000 random name pairs. At 0.80, recall is 79% and the false-positive rate is 0.17% per pair.

A sound match is a filter, not proof.

## Command reference

| Command | Purpose |
|---|---|
| `read FILE_OR_DIR -o OUT` | Reading view. `OUT.html` makes one page; a folder name makes a book site. Options: `--display latin`, `--known-only`, `--unknown-mean`, `--scheme`, `--siku on/off` |
| `find WORD --corpus DIR` | Which files mention a word |
| `fetch TITLE_OR_ID --corpus DIR` | Download from Kanripo; `--juan 1-10`, `--name` |
| `setup` | Build `variants.json` (variant characters) |
| `guoyujie` | Harvest Qianlong respellings from the 《三史国语解》 |
| `align A_DIR B_DIR -o FILE` | Diff two editions and collect renamed names |
| `scan`, `twins`, `propose` | Discovery (see above) |
| `key NAME`, `match A B` | Show readings; compare two names, or a name against a romanized original |
| `train --corpus DIR` | Relearn which characters typically appear in transcriptions |
| `eval gold_pairs.tsv` | Accuracy report |

## Files

| File | Contents |
|---|---|
| `yiming.py` | CLI, phonology, comparison |
| `origin.py` | Detection, lexicon, reading view, book sites, LLM proposals |
| `corpora.py` | Kanripo fetch, variant characters, 国语解 harvest, edition alignment |
| `build_mc.py` | Rebuilds `mc_table.json` from the qieyun data |
| `mc_table.json` | 切韵 positions per character (CC0 data) |
| `foreign_model.json` | Statistics of transcription characters (no text) |
| `lexicon.tsv`, `equivalence.tsv`, `gold_pairs.tsv` | Curated tables |
| `equivalence_siku.tsv`, `equivalence_aligned_*.tsv` | 四库 respellings (generated) |
| `docs/` | Detailed guide in Chinese (使用指南, 原理, 词表编写规范, 练习, 常见问题), also as one page `docs/指南.html` |
| `samples/` | Example pages and book sites |

## Limitations

- **A name's language is evidence of cultural background, not proof of descent.** The evidence is strong when other clues agree (surname, origin, the text calling the person 胡). It is weak where foreign names were fashionable: Han officials with Mongol names under the Yuan, monks with Sanskrit names.
- **Coverage depends on the lexicon.** About 930 transcribed names are detected in the 元史, but only about 50 are in the curated lexicon. The rest show grey until `propose` or a human adds them.
- **Detection is statistical.** In Tang texts, some Chinese words (补阙) are flagged.
- **四库 restoration is best-effort.** Some respellings are missed, and alignment sometimes includes a neighbouring character.
- **`propose` has not yet been tested against real LLM answers.**
- **Many lexicon sources simply say "standard".** They should gradually be replaced by specific citations.
- **The 清史稿 is listed in Kanripo's catalogue but its text is not published there.**

## Extending yiming beyond its current scope

### What the current scope is

- **Texts:** the 二十四史 (hunterhug) and Kanripo titles. These are Chinese-language sources from the Han to the Qing.
- **Pronunciation:** three schemes, `mc`, `om` and `qm`, all derived from the 切韵.
- **Names:** mainly Inner Asian, South Asian, West Asian and some maritime and European names, grouped into 12 families.

### Checklist for a new scope

1. **Texts.** Put plain text in `corpus/<书名>/*.txt`, one paragraph per line. `.html` is also accepted. For a new source, write a small converter. `corpora.clean_mandoku` is an example.
2. **Period.** Add the title to `BOOK_SCHEME` in `origin.py`, or put `"scheme": "mc"` in the book's `meta.json`.
3. **Pronunciation.** If none of `mc`, `om` or `qm` fits, add a scheme:
   - In `yiming.py`, extend `syllable()` (for 切韵-based rules) or `Phon.char_sylls()` (for other reading data) so that each character returns *(onset class, coda class, vowel class)*.
   - Add the scheme name to the CLI choices and to `ERA` in `origin.py`.
   - If the new language has typical substitutions, add them to `SUB` and `INDEL` in `yiming.py`.
4. **Names.** Add rows to `lexicon.tsv` with a real `source`. For a new language family, add it to `FAMILIES` and give it a colour in the CSS block in `origin.py`.
5. **Spellings.** Add same-name variants to `equivalence.tsv`. If an edition altered names, the way the 四库 did, run `align` against an unaltered edition.
6. **Detection.** Run `train --corpus DIR` on the new texts. If the tradition uses its own set of transcription characters, add them to `SEED_CHARS` in `origin.py`.
7. **Check accuracy.** Add attested pairs from the new domain to `gold_pairs.tsv`, then run `eval`. Only trust a threshold you have measured.
8. **LLM proposals (optional).** Adjust `PROMPT` in `origin.py` so it describes the new domain.

### Scenario notes

| Scope | What to change |
|---|---|
| **Korean histories in Classical Chinese** (三国史记, 高丽史, 朝鲜王朝实录) | Foreign names (Jurchen, Mongol, Japanese) were often transcribed by Korean scribes. Add a Sino-Korean scheme (the Unihan field `kHangul` gives readings; Sino-Korean *-l* corresponds to Middle Chinese *-t*). Add families such as Koreanic and Japonic. |
| **Japanese histories** (日本书纪, 续日本纪, …) | Korean and Ainu names are written in characters, often with man'yōgana-like phonetic use. Add a Sino-Japanese scheme (Unihan `kJapaneseOn`; *-tsu/-chi* ↔ *-t*, *-ku/-ki* ↔ *-k*). |
| **Vietnamese histories** (大越史记全书, 钦定越史通鉴纲目) | Cham, Khmer and Tai names. Add a Sino-Vietnamese scheme (Unihan `kVietnamese`; *-t, -c, -p* are kept), plus families such as Austroasiatic and Tai. |
| **Buddhist canon** (CBETA) | Write a converter for the TEI XML. Early (Eastern Han) transcriptions such as 浮屠 predate the 切韵: add an Old Chinese or Later Han scheme from a published reconstruction. |
| **Earlier periods** (匈奴, 西域 in 史记 and 汉书) | Same as above: a pre-切韵 scheme. Expect lower accuracy, because the source languages are poorly known. |
| **Late Qing and Republican texts** | Western names follow Mandarin or Cantonese and Hokkien. Add a pinyin-based scheme, or a Cantonese one (Unihan `kCantonese`) for texts from the south. |
| **Other altered editions** | Any pair of editions works with `align`. |

## Data sources and licences

See [DATA_SOURCES.md](DATA_SOURCES.md).

- The code is MIT-licensed.
- `mc_table.json` comes from nk2028 qieyun data (CC0).
- Samples and 四库 tables derive from Kanripo texts. Check Kanripo's terms before reuse.
- `variants.json` is built locally from the cjkvi variant tables, so it is not included in the repository.
- No hunterhug texts are redistributed here.

## Contributing

Found a wrong or missing identification? Please report:

1. the book and chapter;
2. the sentence;
3. what you think is correct, **and the source**.

These three items let anyone verify and fix the tables. Pull requests to `lexicon.tsv` with real citations are very welcome.

## Acknowledgements

- nk2028 (qieyun data);
- Kanripo / 漢籍リポジトリ (texts);
- cjkvi (variant tables);
- hunterhug/china-history (二十四史 corpus);
- the scholarly identifications cited in `lexicon.tsv`: Pulleyblank, de la Vaissière, Shimunek, and the authors of studies on 鲁迷 and 控噶尔.
