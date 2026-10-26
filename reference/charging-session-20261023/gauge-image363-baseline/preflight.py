"""Read-only input discovery using the original storage guard; no build."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
spec = importlib.util.spec_from_file_location('original_storage284', REF/'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
build = storage.mounted_build()
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()
source = build.parent/'source354'
manifest = json.loads((REF/'charging-oem-audit-20261023/gauge-image363-integration-plan/link-inputs.json').read_bytes())
final = json.loads((REF/'charging-oem-audit-20261023/gauge-image363-integration-plan/final-link-inputs.json').read_bytes())
report = {
 'uid': os.getuid(), 'namespace': os.readlink('/proc/self/ns/mnt'),
 'mount': [s for s in Path('/proc/self/mountinfo').read_text().splitlines() if s.split()[4] == str(build.parent)],
 'build_du': subprocess.check_output(['du','-sb',str(build)], text=True).strip(),
 'source_du': subprocess.check_output(['du','-sb',str(source)], text=True).strip(),
 'free_home': os.statvfs('/home/cy122').f_bavail*os.statvfs('/home/cy122').f_frsize,
 'source_HEAD': subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'], text=True, env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}).strip(),
 'build_symlinks': {str(p.relative_to(build)): os.readlink(p) for p in build.rglob('*') if p.is_symlink()},
 'tmp_entries': sorted(p.name for p in (build.parent/'tmp').iterdir()),
 'current_inputs': {name:sha(build/name) for name in ['.config','arch/arm64/boot/Image','vmlinux','vmlinux.a','Module.symvers','drivers/power/supply/bq27xxx_battery.o']},
 'tools': {n:{'path':r['path'],'expected':r['sha256'],'actual':sha(Path(r['path']).resolve())} for n,r in manifest['toolchains'].items() if r['path']},
 'rust': [{**r,'actual_sha256':sha(r['path'])} for r in manifest['rust_toolchains']],
 'link_members':manifest['member_count'], 'libstub_members':final['libstub_members_count'],
 'initramfs_entries':len(list((build.parent/'input-initramfs363').rglob('*'))),
 'existing_private_output':Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01').exists(),
 'compile_link_executed':False, 'device_access':False,
}
(HERE/'preflight-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
