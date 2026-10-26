"""Rebase applicable posted fixes onto the existing multi-output candidate."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '21facb9a7941ecd0a624a9e4fccd9ae544dde7b5'
git = lambda *args: subprocess.check_output(['git', '-C', str(TREE), *args], text=True)
assert git('rev-parse', 'HEAD').strip() == BASE and not git('status', '--porcelain')
assert (ROOT / 'existing-solutions-validation.json').exists()
git('switch', '-c', 'samurai-vfe175-output282')
directory = TREE / 'drivers/media/platform/qcom/camss'
path = directory / 'camss-vfe-17x.c'
source = path.read_text()
old = '''\tfor (wm = 0; wm < MSM_VFE_IMAGE_MASTERS_NUM; wm++)
\t\tif (status0 & BIT(9))
\t\t\tif (vfe_bus_status[1] & STATUS1_WM_CLIENT_BUF_DONE(wm))
\t\t\t\tvfe->isr_ops.wm_done(vfe, wm);'''
new = '''\tfor (wm = 0; wm < MSM_VFE_IMAGE_MASTERS_NUM; wm++)
\t\tif (vfe_bus_status[1] & STATUS1_WM_CLIENT_BUF_DONE(wm))
\t\t\tvfe->isr_ops.wm_done(vfe, wm);'''
assert source.count(old) == 1
path.write_text(source.replace(old, new))
assert 'ret = vfe_get_output_v2(line);' in source and 'static int vfe_get_output(' not in source
path = directory / 'camss-vfe.c'
source = path.read_text()
assert source.count('static int vfe_disable_output(struct vfe_line *line)') == 1
source = source.replace('static int vfe_disable_output(struct vfe_line *line)',
                        'static void vfe_disable_output(struct vfe_line *line)')
start = source.index('static void vfe_disable_output(')
end = source.index('\n}\n', start) + 3
stop = source[start:end]
assert stop.count('\n\treturn vfe_reset(vfe);') == 1
source = source[:start] + stop.replace('\n\treturn vfe_reset(vfe);', '') + source[end:]
start = source.index('int vfe_disable(struct vfe_line *line)')
end = source.index('\n}\n', start) + 3
source = source[:start] + '''int vfe_disable(struct vfe_line *line)
{
\tstruct vfe_device *vfe = to_vfe(line);
\tint ret = 0;

\tvfe_disable_output(line);
\tvfe_put_output(line);

\tmutex_lock(&vfe->stream_lock);

\tif (--vfe->stream_count == 0)
\t\tret = vfe_reset(vfe);

\tmutex_unlock(&vfe->stream_lock);

\treturn ret;
}
''' + source[end:]
path.write_text(source)
git('diff', '--check')
report = dict(stage=282, parent=BASE, branch='samurai-vfe175-output282',
    posted_fixes_rebased=[1,3], posted_fixed_rdi_mapping_already_present=True,
    maintainer_void_stop_advice_applied=True,
    source_hashes={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
                   for name in ['camss-vfe-17x.c','camss-vfe.c']},
    no_board_dt_or_userspace_change=True, not_deployed=True)
(ROOT / 'public-fixes-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
