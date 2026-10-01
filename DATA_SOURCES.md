# Data sources

The MIT licence in `LICENSE` covers the code. This page lists where each data file comes from.

| File | Derived from | Terms | In this repo? |
|---|---|---|---|
| `mc_table.json` | [nk2028/qieyun](https://github.com/nk2028) rhyme-book data (切韵 / 广韵 positions) | CC0 1.0 (public domain dedication) | yes |
| `variants.json` | [cjkvi/cjkvi-variants](https://github.com/cjkvi/cjkvi-variants) variant tables (漢語大字典 and Japanese tables) | No licence file found in the repository at the time of writing | **no**: built locally by `python yiming.py setup` |
| `equivalence_siku.tsv` | 《欽定遼金元三史國語解》 text from [Kanripo](https://www.kanripo.org) (KR2a0037) | 18th-century work; check Kanripo's terms for the digital text | yes: name pairs only |
| `equivalence_aligned_*.tsv` | Comparison of hunterhug (中華本-based) and Kanripo (四庫本) texts | Short name pairs only; no running text | yes |
| `samples/` | Kanripo texts (四庫全書 editions: 元史, 明史, 金史, 資治通鑑, 大唐西域記, 異域錄) rendered by yiming | Check Kanripo's terms before reuse | yes |
| `foreign_model.json` | Character statistics computed over the hunterhug corpus | Statistics only; no text | yes |
| `lexicon.tsv`, `equivalence.tsv`, `gold_pairs.tsv` | Compiled for this project; each row cites its source | MIT, like the code | yes |
| `docs/img/*.png` | Screenshots of the samples above | as `samples/` | yes |

**Not redistributed:**

- **The hunterhug/china-history corpus.** Its repository has no licence, and it appears to follow modern punctuated editions. Users clone it themselves (see README).
- **Any full text from modern punctuated editions** (中華書局 点校本).

If you are a rights holder and see a problem, please open an issue.
