"""Collect only the two private images from the confirmed-scene follow-up."""
from pathlib import Path

source = Path(__file__).with_name('collect-two-rear-photos.py').read_text()
for old, new in [
    ('two-rear-jpeg-response-private.log', 'rear-jpeg-scene-r2-response-private.log'),
    ('k270-two-rear-jpeg-r1', 'k270-two-rear-jpeg-scene-r2'),
    ("'native-'", "'scene-r2-'"),
    ('two-rear-photo-collection-validation.json', 'scene-r2-photo-collection-validation.json'),
]:
    assert old in source
    source = source.replace(old, new)
exec(compile(source, str(__file__), 'exec'))
