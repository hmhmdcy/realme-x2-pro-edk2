"""Recover the terminal pre-build failure; preserve the original SDK tree."""
from pathlib import Path
import difflib,hashlib,json,os,stat,shutil
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
marker=P/'r14-build-state-private.json';state=json.loads(marker.read_text());assert state['original214_files_links_modes_restored']
original=json.loads((P/'original214-work-manifest-private.json').read_text());work=SDK/'work/libcamera'
for n,item in original.items():
 p=work/n
 if 'target' in item:assert p.is_symlink() and os.readlink(p)==item['target']
 else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
assert not (SDK/'private/libcamera214-before238-r14').exists() and not (P/'full-r14-build-private.log').exists()
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus']:assert not p.joinpath('cwd').resolve().is_relative_to(work)
 except (FileNotFoundError,ProcessLookupError):pass
failed=SDK/'work/libcamera238-r14-built';preserved=SDK/'work/libcamera238-preparation-failed-built'
assert failed.is_dir() and not preserved.exists()
assert failed.resolve().is_relative_to(SDK.resolve()) and preserved.parent.resolve().is_relative_to(SDK.resolve())
os.rename(failed,preserved)
state.update(terminal=True,exit=1,first_preparation_failure=True,no_compiler_started=True,failed_r13_cache_preserved=str(preserved))
(P/'r14-first-preparation-failure-private.json').write_text(json.dumps(state,indent=2)+'\n')
source=(R/'prepare.py').read_text();part=source[source.index('cache=SDK/'):];exec(compile(part,'complete238-source-preparation','exec'))
(R/'first-preparation-failure-validation.json').write_text(json.dumps(dict(stage=238,wrong_insertion_anchor_corrected=True,dependent_build_started_without_preparation_and_failed_before_compiler=True,original214_2254_files_links_modes_verified=True,failed_cache_and_receipt_preserved=True,no_phone_operation=True),indent=2)+'\n')
