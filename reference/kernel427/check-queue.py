"""Exercise actual new auxiliary queue functions with distinct IRQ groups/SOFs."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,resource,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354';D=kernel/'drivers/media/platform/qcom/camss'
negative='--negative' in sys.argv
core=(D/'camss-vfe.c').read_text();backend=(D/'camss-vfe-17x.c').read_text()
tree=ast.parse((HERE.parent/'kernel297/test-sof.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix=prefix.replace('#include <assert.h>','#include <assert.h>\n#include <errno.h>')
prefix=prefix.replace('if(!o->pending_count)return NULL;struct','if(!o->pending_count)return NULL;\n struct')
prefix=prefix.replace('struct camss_video { int unused; };','struct camss_video { bool auxiliary; };')
prefix=prefix.replace('struct vfe_hw_ops {','''struct vfe_hw_ops {
 int (*vfe_output_prepare)(struct vfe_device *,struct vfe_output *);
 void (*vfe_output_start)(struct vfe_device *,struct vfe_output *);
 void (*vfe_output_stop)(struct vfe_device *,struct vfe_output *);
 void (*vfe_wm_start)(struct vfe_device *,u8,struct vfe_line *);''')
prefix=prefix.replace('unsigned pad,wm_num,state,comp_group,sequence,sof_sequence;','unsigned pad,wm_num,state,comp_group,sequence,sof_sequence,wait_reg_update,reg_update;')
prefix+='\n#define VFE_OUTPUT_OFF 0\n#define VFE_OUTPUT_RESERVED 1\n#define reinit_completion(p) do{*(p)=0;}while(0)\n#define WARN_ON(v) assert(!(v))\n#define dev_err dev_err_ratelimited\n'
def function(text,name):
 match=re.search(r'(?:static )?(?:int|void|u32|struct (?:camss_buffer|vfe_output) \*)\s*'+name+r'\(.*?\n\}',text,re.S);assert match,name;return match[0]
names=['vfe_params_output','vfe_params_apply_next','vfe_output_done','vfe_buf_done','vfe_queue_buffer_v2','vfe_enable_one_output']
functions='\n\n'.join(function(core,n) for n in names)+'\n'+function(backend,'vfe_isr_sof')
code=prefix+functions+(HERE/'queue-contract.c').read_text();tag='before-fix' if negative else 'current'
(P/('queue-'+tag+'.c')).write_text(code);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 if negative and arch!='host':continue
 binary=P/('queue-'+tag+'-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-Wno-unused-function',*flags,str(P/('queue-'+tag+'.c')),'-o',str(binary)],capture_output=True)
 (P/('queue-'+tag+'-'+arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],capture_output=True);(P/('queue-'+tag+'-'+arch+'-run.log')).write_bytes(q.stdout+q.stderr)
 if negative:assert q.returncode!=0 and b'Auxiliary image' in q.stderr;outputs.append(dict(arch=arch,expected_legacy_rdi_start_failure=True));continue
 assert not q.returncode and b'DS4_QUEUE_CONTRACTS_PASSED' in q.stdout,q.stderr.decode();outputs.append(dict(arch=arch,passed=True))
r=dict(stage=427,negative_control=negative,actual_queue_start_done_sof_functions=True,architectures=outputs,
 owned_buffers_then_wm_arm_then_addresses_verified=not negative,independent_done_groups_verified=not negative,starvation_stop_restart_verified=not negative,
 shared_sof_with_gap_verified=not negative,missing_sof_error_verified=not negative,missing_calibration_reject_before_start_verified=not negative,
 source_sha256=hashlib.sha256(core.encode()).hexdigest(),hardware_proof_not_claimed=True,passed=True)
(HERE/('queue-negative-validation.json' if negative else 'queue-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
