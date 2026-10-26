from pathlib import Path
import difflib,importlib.util,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(P/'camss-icp-a5-boot-test.c.before').read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('Temporary A5/IPE session diagnostic. No image frames or sensor changes.','Temporary A5/IPE synthetic frame diagnostic; no sensor changes.')
replace('#include <linux/dma-mapping.h>','#include <linux/dma-mapping.h>\n#include <linux/crc32.h>\n#include <linux/vmalloc.h>')
replace('#include "camss-icp-a5-boot.h"','#include "camss-icp-a5-boot.h"\n#include "camss-icp-a5-ipe.h"')
replace('static bool snapshot_ranges_valid(u32 bytes)',(HERE/'frame-owner.c').read_text()+'\nstatic bool snapshot_ranges_valid(u32 bytes)')
replace('\\"image_frames\\":0}', '\\"image_frames\\":%u,\\"frames_completed\\":%u,\\"transfer_maps\\":%u,\\"transfer_unmaps\\":%u,\\"ipe_dma_pending\\":%s,\\"request_fw_mapped\\":%s,\\"engine_dma_capable\\":%s,\\"ipe_reset_acks\\":[%u,%u],\\"image_bytes\\":%u,\\"input_crc\\":%u,\\"output_crc\\":%u}')
replace('a5->firmware.mapped + a5->shared.mapped + a5->heap.mapped + a5->config.mapped,','a5->firmware.mapped + a5->shared.mapped + a5->heap.mapped + a5->config.mapped +\n\t\t  a5->request.mapped + a5->image_input.mapped + a5->image_output.mapped,')
replace('a5->config_fw_mapped ? "true" : "false", scratch_observed[0], scratch_observed[1]);','a5->config_fw_mapped ? "true" : "false", scratch_observed[0], scratch_observed[1],\n\t\t  a5->frames_submitted, a5->frames_completed, a5->transfer_maps, a5->transfer_unmaps,\n\t\t  a5->ipe_dma_pending ? "true" : "false", a5->request_fw_mapped ? "true" : "false",\n\t\t  a5->engine_dma_capable ? "true" : "false", a5->resources.ipe_reset_acks[0],\n\t\t  a5->resources.ipe_reset_acks[1], test_output_bytes, test_input_crc, test_output_crc);')
replace('test_bin_attributes[] = { &firmware_attribute, NULL };','test_bin_attributes[] = { &firmware_attribute, &image_attribute, NULL };')
replace('\tscratch_observed[1] = session_non_rt.scratch_bytes;','\tscratch_observed[1] = session_non_rt.scratch_bytes;\n\tif (enable_frame) {\n\t\tphase = "process-ipe-rt";\n\t\tret = test_frame(dev, a5);\n\t\tif (ret)\n\t\t\tgoto done;\n\t}')
replace('\tdevice_a5 = NULL;\n\tmutex_unlock(&test_lock);','\tkvfree(test_output);\n\ttest_output = NULL;\n\ttest_output_bytes = 0;\n\tdevice_a5 = NULL;\n\tmutex_unlock(&test_lock);')
replace('\t\t.probe_type = PROBE_FORCE_SYNCHRONOUS,','\t\t.probe_type = PROBE_FORCE_SYNCHRONOUS,\n\t\t.suppress_bind_attrs = true,')
(P/'camss-icp-a5-boot-test.c.proposed').write_text(s);(HERE/'camss-icp-a5-boot-test.c').write_text(s)
state=json.loads((HERE/'proposal-state.json').read_text());name='camss-icp-a5-boot-test.c'
if name not in state['changed']:state['changed'].append(name)
(HERE/'proposal-state.json').write_text(json.dumps(state,indent=2)+'\n')
patch='';relative=Path('drivers/media/platform/qcom/camss')
for name in state['changed']:
 old=(P/(name+'.before')).read_text();new=(P/(name+'.proposed')).read_text();patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
(HERE/'ipe-transfer.patch').write_text(patch)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['parent']
dts=(P.parent/'kernel366/boot-test-private.dts').read_text();facts=json.loads((P.parent/'kernel380/live-overlay-state-private.json').read_text())
specs=[(0x2222,0),(0x2080,0x20),(0x20a0,0x20),(0x2100,0x20),(0x2120,0x20),(0x20c0,0),(0x2140,0)]
anchor='iommus = <44 0x2222 0>;';assert dts.count(anchor)==1;dts=dts.replace(anchor,'iommus = '+', '.join(f'<44 {sid:#x} {mask:#x}>' for sid,mask in specs)+';')
anchor='  trace356:';assert dts.count(anchor)==1;dts=dts.replace(anchor,'  image381: samurai-icp356-images-iova { iommu-addresses = <&icp356 0 0x20000000 0 0x08000000>; };\n'+anchor)
dts=dts.replace('<&trace356>;','<&trace356>, <&image381>;').replace('"heap", "trace";','"heap", "trace", "images";')
src=P/'boot-test-private.dts';src.write_text(dts);out=P/'boot-test-private.dtbo'
q=subprocess.run([str(build/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(out),str(src)],capture_output=True);(P/'dtc-private.log').write_bytes(q.stderr);q.check_returncode()
merged=P/'boot-test-merged-private.dtb';base=P.parent/'kernel365/samurai365-private.dtb'
subprocess.run([str(build/'scripts/dtc/fdtoverlay'),'-i',str(base),'-o',str(merged),str(out)],capture_output=True,check=True)
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns);before=ns['fdt_nodes'](base.read_bytes());after=ns['fdt_nodes'](merged.read_bytes())
assert all(after[path]==props for path,props in before.items())
node=after['/soc@0/samurai-icp356-boot@ac10000'];assert node['iommus']==b''.join(struct.pack('>III',44,*pair) for pair in specs)
image=after['/reserved-memory/samurai-icp356-images-iova'];assert 'reg' not in image and 'no-map' not in image
# iommu-addresses is phandle + two-cell address + two-cell size, no RAM reg.
words=struct.unpack('>5I',image['iommu-addresses']);assert words[1:]==(0,0x20000000,0,0x08000000)
facts.update(bytes=out.stat().st_size,combined_icp_sid_specs=specs,image_iova_start=0x20000000,image_iova_bytes=0x08000000,existing_dt_properties_untouched_by_overlay=True)
(P/'live-overlay-state-private.json').write_text(json.dumps(facts,indent=2)+'\n')
report=dict(stage=381,original_combined_icp_sid_specs_used=True,sid_specs=specs,temporary_image_iova_reservation=[0x20000000,0x08000000],no_new_physical_ram_reservation=True,existing_dt_properties_untouched=True,static_icp_stays_disabled=True,phone_mutated=False,passed=True)
(HERE/'overlay-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
