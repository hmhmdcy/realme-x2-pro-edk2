"""Read current upgrade dependencies without changing device or source trees."""
from pathlib import Path
import json, re, subprocess
import host

ROOT = Path(__file__).resolve().parents[2]
code = '''from pathlib import Path
import json,os
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k297-work/boot-id-private.txt').read_bytes()
cmd=Path('/proc/cmdline').read_text().split()
flags=[v for v in ['clk_ignore_unused','pd_ignore_unused','regulator_ignore_unused'] if v in cmd]
print(json.dumps(dict(release=os.uname().release,bringup_retention_flags=flags,
                     boot_directory_entries=sorted(p.name for p in Path('/boot').iterdir()),
                     dt_present=Path('/sys/firmware/devicetree/base').is_dir(),
                     efi_present=Path('/sys/firmware/efi').is_dir())))
'''
response = host.ssh('python3 -', input=code.encode(), timeout=15)
runtime = json.loads(response.stdout)
base = 'a90ee4305c4a5df72c11b31dacfdc76e00fcf78a'
trees = {}
for name in ['camera270-kernel', 'camera279-isp-kernel']:
    tree = '/home/cy122/x2pro-linux/'+name
    git = lambda *a: subprocess.check_output(['git', '-C', tree, *a], text=True).strip()
    trees[name] = dict(commit=git('rev-parse', 'HEAD'), clean=not git('status', '--porcelain'),
                       commits_after_base=int(git('rev-list', '--count', base+'..HEAD')),
                       diff_shortstat=git('diff', '--shortstat', base+'..HEAD'))
text = (ROOT/'linux-port/packages/libcamera/APKBUILD').read_text()
source = text[text.index('source='):text.index('builddir=')]
patches = re.findall(r'^\s+(\d{4}[^\n]+\.patch)\s*$', source, re.M)
assert len(patches) == 28
report = dict(stage=297, read_only=True, runtime=runtime, base=base, trees=trees,
              libcamera_recipe_numbered_patches=len(patches), includes_existing_distribution_patches=True,
              pipewire_project_patches=6, no_new_kernel_version_migration_test=True,
              no_upstream_acceptance_proven_by_local_commit=True)
(ROOT/'reference/kernel297/layering-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
