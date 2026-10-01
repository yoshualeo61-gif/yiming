"""Smoke tests: run with `python -m pytest tests` or `python tests/test_smoke.py`.
They use only the files in the repository (no corpus, no network)."""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.argv = ['yiming']
import yiming as Y  # noqa: E402

# A short passage of the 舊唐書 (public-domain classical text), typed for the test.
PASSAGE = '安祿山，營州柳城雜種胡人也，本無姓氏，名軋犖山。母阿史德氏，亦突厥巫。'


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / 'yiming.py'), *args],
                          capture_output=True, text=True, encoding='utf-8')


def test_sound_match():
    ph = Y.Phon()
    s, _ = Y.score(ph, '禄山', 'Roxšan', 'mc')
    assert s > 0.8, s
    s, _ = Y.score(ph, '速不台', '雪不台', 'om')
    assert s > 0.85, s
    s, _ = Y.score(ph, '沙陀', 'Tabγač', 'mc')
    assert s < 0.4, s


def test_key_runs():
    r = run('key', '禄山', '--scheme', 'mc')
    assert r.returncode == 0 and 'LuK' in r.stdout, r.stdout + r.stderr


def test_read_marks_roxshan():
    with tempfile.TemporaryDirectory() as d:
        book = Path(d) / '旧唐书'
        book.mkdir()
        (book / '001.txt').write_text(PASSAGE + '\n', encoding='utf-8')
        out = Path(d) / 'out.html'
        r = run('read', str(book / '001.txt'), '-o', str(out))
        assert r.returncode == 0, r.stderr
        html = out.read_text(encoding='utf-8')
        assert 'Roxšan' in html and 'Türk' in html


def test_site():
    with tempfile.TemporaryDirectory() as d:
        book = Path(d) / '旧唐书'
        book.mkdir()
        for i in (1, 2):
            (book / f'{i:03d}.txt').write_text(PASSAGE + '\n', encoding='utf-8')
        r = run('read', str(book), '-o', str(Path(d) / 'site'))
        assert r.returncode == 0, r.stderr
        assert (Path(d) / 'site' / 'index.html').exists()
        assert (Path(d) / 'site' / 'names.html').exists()


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
