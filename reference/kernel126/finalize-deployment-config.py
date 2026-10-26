from pathlib import Path
import subprocess,runpy,json,difflib,hashlib,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');k=v/'kernel';base=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
assert not (ref/'release-coexistence-validation.json').exists()
shutil.copyfile(out/'kernel-full-build.log',out/'first-shared-release-build-private.log')
subprocess.run([str(k/'scripts/config'),'--file',str(k/'.config'),'--set-str','LOCALVERSION','-rmx1931-samurai-k126'],check=True)
p=k/'drivers/media/platform/qcom/camss/camss-video.c';s=p.read_text()
if '#include <linux/module.h>' not in s:
 at=s.index('#include ');s=s[:at]+'#include <linux/module.h>\n'+s[at:]
needle='static int video_check_dma_mapping(';a=s.index('/* Verify every byte')
s=s[:a]+'''/* Bounded bring-up diagnostics; normal camera operation stays quiet. */
static bool trace_dma;
module_param_named(dma_trace, trace_dma, bool, 0600);
MODULE_PARM_DESC(dma_trace, "Log prepared SM8150 DMA plane ranges");

'''+s[a:]
needle='\t\tdev_dbg(video->camss->dev, "DMA plane %u address %pad size %lu\\n",\n\t\t\ti, &buffer->addr[i], vb2_plane_size(vb, i));';assert needle in s
s=s.replace(needle,'\t\tif (trace_dma && video->camss->res->version == CAMSS_8150)\n\t\t\tdev_info(video->camss->dev, "DMA plane %u address %pad size %lu\\n",\n\t\t\t\ti, &buffer->addr[i], vb2_plane_size(vb, i));');p.write_text(s)
state=json.loads((ref/'tpg-port-validation.json').read_text());patch=''
for rel in state['changed_files']:
 old=(base/rel).read_text();new=(k/rel).read_text();patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ref/'sm8150-tpg-dma-guards-7.3.patch').write_text(patch);state['patch_sha256']=hashlib.sha256(patch.encode()).hexdigest();state.update(dma_trace_default_false_root_only=True,distinct_module_release_selected=True);(ref/'tpg-port-validation.json').write_text(json.dumps(state,indent=2)+'\n')
(ref/'release-coexistence-validation.json').write_text(json.dumps(dict(localversion='-rmx1931-samurai-k126',old118_module_directory_not_replaced=True,no_hardcoded_release_in_init_or_rootfs_services=True,first_shared_release_build_pass=True,distinct_release_full_rebuild_required=True,not_deployed=True),indent=2)+'\n');print('K126_DISTINCT_RELEASE_AND_OPT_IN_DMA_TRACE_CONFIGURED')
