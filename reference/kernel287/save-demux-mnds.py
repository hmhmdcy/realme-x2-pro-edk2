"""Save the tested Demux/MNDS backend, preserving unrelated processing code."""
from pathlib import Path
import hashlib, json, os, re, subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel287')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '209d1ea0f0a53e9a725ad288c159baddbc83aef7'
prefix = 'drivers/media/platform/qcom/camss/'
git = lambda *a: subprocess.check_output(['git', '-C', str(TREE), *a], text=True).strip()
assert git('rev-parse', 'HEAD') == BASE
assert git('branch', '--show-current') == 'samurai-vfe175-demux-mnds287'
assert subprocess.run(['git', '-C', str(TREE), 'diff', '--cached', '--quiet']).returncode == 0
header = TREE/prefix/'camss-vfe-175-camif.h'
old = header.read_text()
assert '#include' not in old
header.write_text(old.replace('struct vfe_line;', '#include <linux/types.h>\n\nstruct vfe_line;'))
test = json.loads((ROOT/'demux-mnds-host-tests-validation.json').read_text())
assert test['exit'] == 0 and test['asan_ubsan']
for name, sha in test['source_sha256'].items():
    assert hashlib.sha256((TREE/prefix/name).read_bytes()).hexdigest() == sha
files = [prefix+n for n in ['Makefile', 'camss-vfe-175-camif.c', 'camss-vfe-175-camif.h',
         'camss-vfe-175-demux.c', 'camss-vfe-175-demux.h', 'camss-vfe-175-mnds.c',
         'camss-vfe-175-mnds.h', 'camss-vfe-175-pixel.c']]
pixel = (TREE/prefix/'camss-vfe-175-pixel.c').read_text()
previous = subprocess.check_output(['git', '-C', str(TREE), 'show', BASE+':'+prefix+'camss-vfe-175-pixel.c'], text=True)
preserved = {}
for name in ['vfe_175_wb_q7', 'vfe_175_wb_write', 'vfe_175_wb_validate', 'vfe_175_params_unsupported', 'vfe_175_params_apply']:
    def extract(text):
        match = re.search(r'(?:static )?(?:void|int|u32) '+name+r'\(', text)
        assert match
        return text[match.start():text.index('\n}', match.start())+2]
    assert extract(pixel) == extract(previous)
    preserved[name] = hashlib.sha256(extract(pixel).encode()).hexdigest()
unchanged = ['camss-vfe-175-demosaic.c', 'camss-vfe-175-cst.c', 'camss-vfe-175-gamma.c', 'camss-vfe-175-round.c']
for name in unchanged:
    assert subprocess.check_output(['git', '-C', str(TREE), 'show', BASE+':'+prefix+name]) == (TREE/prefix/name).read_bytes()
subprocess.run(['git', '-C', str(TREE), 'add', '--', *files], check=True)
assert sorted(git('diff', '--cached', '--name-only').splitlines()) == sorted(files)
patch = subprocess.check_output(['git', '-C', str(TREE), 'diff', '--cached', '--binary', '--full-index'])
path = ROOT/'vfe175-demux-mnds-candidate.patch'
path.write_bytes(patch)
check = subprocess.run(['perl', str(TREE/'scripts/checkpatch.pl'), '--no-tree', str(path)], text=True, capture_output=True)
(PRIVATE/'demux-mnds-checkpatch-private.txt').write_text(check.stdout+check.stderr)
assert '0 errors' in check.stdout, check.stdout
message = '''media: qcom: camss: add VFE175 Bayer Demux and MNDS16 backends

Reuse CAMIF Bayer classification for Demux routing. Validate Q10 gains
and black levels before MMIO, preserve reserved fields, and start with
unity gains until the actual input domain is verified on hardware.

Configure luma scaling and NV12 chroma decimation independently. Check
all axes, phase precision and scaling limits before programming either
scaler; reject unsupported cropping instead of silently ignoring it.
Integrate preparation and failure/stop cleanup with the pixel backend.

Keep the three RDI resources unchanged. These internal SoC backends do
not expose PIX or claim a working hardware ISP pipeline; TPG/RAW tests,
statistics and the libcamera pipeline/IPA remain to be completed.

Signed-off-by: Samurai Builder <samurai@localhost>
'''
body = PRIVATE/'demux-mnds-commit-message-private.txt'
body.write_text(message)
subprocess.run(['git', '-C', str(TREE), '-c', 'user.name=Samurai Builder', '-c', 'user.email=samurai@localhost', 'commit', '-F', str(body)], check=True, capture_output=True)
commit = git('rev-parse', 'HEAD')
assert git('rev-parse', 'HEAD^') == BASE and not git('status', '--porcelain')
index = PRIVATE/'patch-check-index-private'
assert not index.exists()
env = dict(os.environ, GIT_INDEX_FILE=str(index))
subprocess.run(['git', '-C', str(TREE), 'read-tree', BASE], env=env, check=True)
subprocess.run(['git', '-C', str(TREE), 'apply', '--cached', str(path)], env=env, check=True)
rebuilt = subprocess.check_output(['git', '-C', str(TREE), 'write-tree'], env=env, text=True).strip()
assert rebuilt == git('rev-parse', 'HEAD^{tree}')
report = dict(stage=287, commit=commit, parent=BASE, branch=git('branch', '--show-current'),
              source_sha256={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in files},
              patch_sha256=hashlib.sha256(patch).hexdigest(), independent_index_tree_matches=True,
              wb_functions_identical=preserved, unchanged_processing_sources=unchanged,
              checkpatch_exit=check.returncode,
              checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
              camif_header_self_contained=True, not_pushed=True, not_deployed=True)
(ROOT/'demux-mnds-commit-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
