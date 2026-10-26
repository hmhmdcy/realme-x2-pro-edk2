"""Build the saved 287 candidate and preserve the preceding full 286 artifacts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
previous = ROOT.parent/'kernel285/build-cst-full.py'
s = previous.read_text()
changes = [
    ('/mnt/e/edk2-samurai-out/kernel285', '/mnt/e/edk2-samurai-out/kernel287'),
    ("COMMIT='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'", "COMMIT='6ddf1ba4cfafe221a38cc12667a1aac06f3f9ec5'"),
    ("ROOT.parent/'kernel284/demosaic-full-build-validation.json'", "ROOT.parent/'kernel286/depth-gamma-full-build-validation.json'"),
    ('completed-demosaic284', 'completed-depth-gamma286'),
    ("'cst-", "'demux-mnds-"),
    ("KBUILD_BUILD_VERSION='285'", "KBUILD_BUILD_VERSION='287'"),
    ('stage=285', 'stage=287'),
]
for before, after in changes:
    assert before in s, before
    s = s.replace(before, after)
needle = "assert any(n.endswith('/camss-vfe-175-cst.o') for n in components)"
assert s.count(needle) == 1
s = s.replace(needle, needle + "\n    assert len(components)==39 and all(any(n.endswith('/'+name) for n in components) for name in ['camss-vfe-175-demux.o','camss-vfe-175-mnds.o'])")
exec(compile(s, str(previous), 'exec'), globals())
