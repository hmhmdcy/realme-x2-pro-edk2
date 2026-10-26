"""Check final handoff originals and sanitized repository copies after sync."""
from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[2]
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
spec=importlib.util.spec_from_file_location('public_docs',ROOT/'linux-port/scripts/public-docs.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
checkpoint=json.loads((ROOT/'reference/maintenance-2026-10-19/checkpoint-validation.json').read_text())
for name,item in checkpoint['files'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==item['sha256'],name
    assert mod.public_bytes(ROOT,Path(name))==(mirror/name).read_bytes(),name
extra=[p.relative_to(ROOT) for p in (ROOT/'reference/maintenance-2026-10-19').iterdir() if p.is_file()]
extra+=[Path('sessions/maintenance-2026-10-19.md'),Path('archive/camera-before-handoff-2026-10-19/manifest.json')]
for name in extra:assert mod.public_bytes(ROOT,name)==(mirror/name).read_bytes(),str(name)
result=dict(nine_handoff_originals_match_checkpoint=True,nine_public_entrypoints_match_mirror=True,
            maintenance_files_and_session_and_archive_manifest_match_mirror=len(extra),verified=True)
Path('/mnt/e/edk2-samurai-out/cleanup20261019/mirror-verification-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
