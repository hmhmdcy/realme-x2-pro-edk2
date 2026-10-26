"""Add a VFE175 CST12 backend without exposing the unfinished PIX pipeline."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
BASE='af9e2a02365a2ec1a19d3cc42da5c65e84c244c4'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and not git('status','--porcelain')
assert subprocess.run(['git','-C',str(TREE),'show-ref','--verify','--quiet','refs/heads/samurai-vfe175-cst285']).returncode==1
assert json.loads((ROOT.parent/'kernel284/demosaic-full-build-validation.json').read_text())['terminal']
PRIVATE.mkdir(exist_ok=True)
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-vfe175-cst285'],check=True,capture_output=True)
before={n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in ['Makefile','camss-vfe-175-pixel.c']}
for name in ['camss-vfe-175-cst.c','camss-vfe-175-cst.h']:
    target=SOURCE/name
    assert not target.exists()
    target.write_bytes((ROOT/'source'/name).read_bytes())
path=SOURCE/'Makefile';s=path.read_text();needle='\t\tcamss-vfe-175-demosaic.o \\\n'
assert s.count(needle)==1
path.write_text(s.replace(needle,needle+'\t\tcamss-vfe-175-cst.o \\\n'))
path=SOURCE/'camss-vfe-175-pixel.c';s=path.read_text()
needle='#include "camss-vfe-175-demosaic.h"\n';assert s.count(needle)==1
s=s.replace(needle,needle+'#include "camss-vfe-175-cst.h"\n')
old='''int vfe_175_pixel_prepare(struct vfe_line *line)
{
	struct vfe_device *vfe = to_vfe(line);

	int ret;

	if (!line->is_pix)
		return 0;
	ret = vfe_175_demosaic_prepare(line);
	if (ret)
		return ret;
'''
new='''int vfe_175_pixel_prepare(struct vfe_line *line)
{
	struct vfe_device *vfe = to_vfe(line);
	struct vfe_175_cst_config cst;
	int ret;

	if (!line->is_pix)
		return 0;
	/* Reject unsupported output colorimetry before any processing MMIO. */
	ret = vfe_175_cst_from_format(&line->output[0].video_out.active_fmt.fmt.pix_mp,
				      &cst);
	if (ret)
		return ret;
	ret = vfe_175_demosaic_prepare(line);
	if (ret)
		return ret;
	ret = vfe_175_cst_configure(vfe, &cst);
	if (ret) {
		vfe_175_demosaic_stop(vfe);
		return ret;
	}
'''
assert s.count(old)==1;s=s.replace(old,new)
old='''void vfe_175_pixel_stop(struct vfe_device *vfe)
{
	vfe_175_demosaic_stop(vfe);
}'''
new='''void vfe_175_pixel_stop(struct vfe_device *vfe)
{
	vfe_175_cst_stop(vfe);
	vfe_175_demosaic_stop(vfe);
}'''
assert s.count(old)==1;s=s.replace(old,new);path.write_text(s)
(PRIVATE/'source-preparation-private.json').write_text(json.dumps(dict(base=BASE,before_sha256=before),indent=2)+'\n')
print(git('diff','--stat'))
