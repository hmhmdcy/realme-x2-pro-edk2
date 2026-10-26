"""Preserve pre-closeout documentation and make moved links resolve correctly."""
from pathlib import Path
import hashlib, json, os, re

root = Path('/mnt/e/RealmeX2Pro edk2')
records = []
for name, target in [
    ('linux-port/docs/HARDWARE-STATUS.md', 'archive/HARDWARE-STATUS-through150-2026-10-13.md'),
    ('NEXT-SESSION.md', 'archive/NEXT-SESSION-through150-2026-10-13.md'),
    ('NEXT-SESSION-PROMPT.md', 'archive/NEXT-SESSION-PROMPT-through150-2026-10-13.md'),
]:
    source, archive = root/name, root/target
    assert not archive.exists(), 'Archive already exists; do not replay this one-time operation'
    original = source.read_bytes()
    def relocate(match):
        destination = match[1]
        if destination.startswith(('https:', 'http:', '/', '#')):
            return match[0]
        file, separator, fragment = destination.partition('#')
        resolved = source.parent/file
        relative = os.path.relpath(resolved, archive.parent).replace(os.sep, '/')
        return ']('+relative+(separator+fragment if separator else '')+')'
    text = re.sub(r'\]\(([^)]+)\)', relocate, original.decode('utf-8-sig'))
    preface = ('历史快照：阶段151收尾更新前的文档，仅保留历史证据；'
               '当前状态以NEXT-SESSION.md及linux-port/docs/HARDWARE-STATUS.md为准。\n\n')
    archive.write_text(preface+text)
    records.append(dict(source=name, archive=target,
        original_sha256=hashlib.sha256(original).hexdigest(),
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        relative_links_relocated=True))
(root/'reference/kernel151/document-history.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records))
