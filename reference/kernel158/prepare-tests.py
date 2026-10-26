from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158');out=Path('/mnt/e/edk2-samurai-out/kernel158')
n='drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c';s=(k/n).read_text()
needle='static int dpu_kms_quiesce_boot_dsi(struct msm_kms *kms)\n{\n\tint i, ret;'
assert s.count(needle)==1
(k/n).write_text(s.replace(needle,'static int dpu_kms_quiesce_boot_dsi(struct msm_kms *kms)\n{\n\tunsigned int i;\n\tint ret;',1))
report=json.loads((ref/'source-validation.json').read_text());before=json.loads((out/'source-before-private.json').read_text())
head=(ref/'before-ctl-stop.patch').read_text().split('diff --git',1)[0];patch=head
for n in report['modified_files']:
    s=(k/n).read_text();report['after_sha256'][n]=hashlib.sha256(s.encode()).hexdigest()
    patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before[n].splitlines(True),s.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ref/'before-ctl-stop.patch').write_text(patch)
fixture=(ref.parent/'kernel157/test-early-host-stop.c').read_text()
fixture=fixture.replace('#include "actual-functions.h"','''struct msm_kms { struct msm_dsi *dsi[2]; };
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#include "actual-functions.h"
#ifdef BASELINE
/* 157 has no DPU pre-CTL host quiesce call. */
static int dpu_kms_quiesce_boot_dsi(struct msm_kms *kms) { (void)kms;return 0; }
#endif''',1)
fixture=fixture.replace('struct drm_bridge bridge={0};int ret;','struct drm_bridge bridge={0};struct msm_kms kms;int ret;',1)
needle='#ifndef BASELINE\n    reset();ret=msm_dsi_host_quiesce_firmware'
assert fixture.count(needle)==1
fixture=fixture.replace(needle,'''    reset();kms=(struct msm_kms){{&dsis[0],NULL}};ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("single_host_stopped_before_ctl",ret==0 && hosts[0].firmware_quiesced && hosts[0].ctrl==0 && writes==1 && !phy_on && locks==0);
    reset();kms=(struct msm_kms){{&dsis[0],&dsis[1]}};ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("both_hosts_stopped_before_ctl",ret==0 && hosts[0].firmware_quiesced && hosts[1].firmware_quiesced && writes==2 && !phy_on && locks==0);
#ifndef BASELINE
    reset();kms=(struct msm_kms){{NULL,NULL}};ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("absent_dsi_does_not_touch_hardware",ret==0 && !get_count && !writes && locks==0);
    reset();kms=(struct msm_kms){{NULL,&dsis[1]}};ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("sparse_secondary_slot_is_quiesced",ret==0 && hosts[1].firmware_quiesced && !hosts[0].firmware_quiesced && writes==1 && get_count==put_count && locks==0);
    reset();kms=(struct msm_kms){{&dsis[0],&dsis[1]}};hosts[0].pm_error=-ENOMEM;ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("pre_ctl_runtime_error_blocks_cleanup",ret==-ENOMEM && !hosts[1].firmware_quiesced && !writes && get_count==1 && !put_count && locks==0);
    reset();kms=(struct msm_kms){{&dsis[0],&dsis[1]}};hosts[1].readback_error=1;ret=dpu_kms_quiesce_boot_dsi(&kms);
    CASE("partial_handoff_error_blocks_cleanup",ret==-EIO && hosts[0].firmware_quiesced && !hosts[1].firmware_quiesced && writes==2 && get_count==put_count && locks==0);
    hosts[1].readback_error=0;ret=dpu_kms_quiesce_boot_dsi(&kms);bonded=true;
    if (!ret) ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("retry_and_phy_fallback_reuse_handoff",ret==0 && hosts[1].firmware_quiesced && writes==3 && get_count==3 && put_count==3 && phy_on==1 && irqs[0]==1 && irqs[1]==1 && locks==0);
    reset();ret=msm_dsi_host_quiesce_firmware''',1)
(ref/'test-before-ctl.c').write_text(fixture)
