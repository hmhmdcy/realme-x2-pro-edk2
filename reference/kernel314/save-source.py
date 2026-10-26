"""Save only the changed CAMSS sources and their tested module identity."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera314-streams-kernel')
BASE='f7ee1b4735a217e2aebdcae1cd385ed8823fc710'
diff=subprocess.check_output(['git','-C',str(TREE),'diff',BASE,'--','drivers/media/platform/qcom/camss'])
(HERE/'shared-streams.patch').write_bytes(diff)
names=subprocess.check_output(['git','-C',str(TREE),'diff','--name-only',BASE,'--','drivers/media/platform/qcom/camss'],text=True).splitlines()
module=Path(json.loads((HERE/'kernel-build-validation.json').read_text())['module'])
source={'stage':314,'tree':str(TREE),'branch':'samurai-raw314','base_commit':BASE,
 'head':subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip(),
 'changed_sources':{n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in names},
 'module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),
 'source_patch':'shared-streams.patch','upstream_inputs':'upstream/manifest.json',
 'applied_upstream_mechanism':[1,2,4,6],
 'adapted_upstream_mechanism':[3,7],'not_enabled_or_applied':[5,8],
 'existing_vfe_three_fixes_already_present_in_base':True,
 'soc_flag_enabled_only':'SM8150','dt_sensor_sources_changed':False,
 'v4l2_core_changed':False,'userspace_candidate_source_stage':313,'system_module_installed':False,
 'scope':'Standard stream ownership for shared CSI input; independent RDI and175 IPP/PIX lifecycle. No libcamera RAW request integration or physical frame pairing claim.'}
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
print(json.dumps({'changed_sources':len(names),'patch_bytes':len(diff),'head':source['head'],'module':str(module)}))
