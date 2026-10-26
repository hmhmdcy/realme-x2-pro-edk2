"""Execute affected real helper paths only; R1's 12-case suite is not run."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
R1=HERE.parent/'eud-boot-policy'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
for name in ['direct-fifo.inc','launch.inc','core-functions.inc']:
    (HERE/name).write_bytes((R1/name).read_bytes())
prefix=(R1/'test-boot.c').read_text().split('int main(void)')[0]
# These are fake MMIO boundary changes, not changes to candidate helper code.
assert prefix.count('static UINT32 csr;')==1
prefix=prefix.replace('static UINT32 csr;','static UINT32 csr, forced_after_write;')
assert prefix.count('if(!ignore_write)csr=0;')==1
prefix=prefix.replace('if(!ignore_write)csr=0;','if(!ignore_write)csr=0;if(forced_after_write)csr=forced_after_write;')
tail=r'''
int main(void){
 assert(SamuraiEudCsrKnown(0)&&SamuraiEudCsrKnown(1)&&SamuraiEudCsrKnown(0x01010101U));
 assert(!SamuraiEudCsrKnown(0x00010101U)&&!SamuraiEudCsrKnown(0x01010100U));
 puts("ok: exact full-word set adds only the actually observed literal");

 reset(0x01010101U);forced_after_write=0;
 assert(!SamuraiArmEudOffHandoff()&&reads==1&&!writes&&created==1);
 assert(mSamuraiEudOffHandoff.ArmCsr==0x01010101U);
 notify(NULL,notify_context);
 assert(csr==0&&writes==1&&reads==3&&mSamuraiEudOffHandoff.WriteAttempted);
 assert(mSamuraiEudOffHandoff.BeforeCsr==0x01010101U&&mSamuraiEudOffHandoff.AfterCsr==0&&mSamuraiEudOffHandoff.Status==EFI_SUCCESS);
 notify(NULL,notify_context);assert(writes==1&&reads==3);
 SamuraiEudComPuts("late");assert(!fifo_writes);SamuraiDisarmEudOffHandoff();assert(closed==1);
 puts("ok: observed full word arms without writes, callback writes literal0 once, exact zero readback succeeds, retry inert");

 UINT32 unknowns[]={0x00010101U,0x01000101U,0x01010100U,0x01010102U,0x00000101U,2U,0xffffffffU,0x10000001U};
 for(unsigned i=0;i<sizeof(unknowns)/sizeof(unknowns[0]);i++){
  reset(unknowns[i]);forced_after_write=0;launch();
  assert(!writes&&!created&&!kernel_calls&&!panel_arms&&csr==unknowns[i]);
  assert(mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);
 }
 puts("ok: approximate and other unknown whole words refuse arm and launch with zero writes");

 reset(0x01010101U);forced_after_write=0;assert(!SamuraiArmEudOffHandoff());csr=0x00010101U;
 notify(NULL,notify_context);assert(!writes&&csr==0x00010101U&&mSamuraiEudOffHandoff.Attempted&&mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);
 int n=reads;notify(NULL,notify_context);assert(!writes&&reads==n);
 puts("ok: unknown near-word at callback is preserved and terminal without write or retry");

 UINT32 nonzero[]={1U,0x01010101U,0x01000000U};
 for(unsigned i=0;i<sizeof(nonzero)/sizeof(nonzero[0]);i++){
  reset(0x01010101U);forced_after_write=nonzero[i];assert(!SamuraiArmEudOffHandoff()&&!writes);
  notify(NULL,notify_context);assert(writes==1&&csr==nonzero[i]&&mSamuraiEudOffHandoff.AfterCsr==nonzero[i]&&mSamuraiEudOffHandoff.Status==EFI_DEVICE_ERROR);
  int count=reads;notify(NULL,notify_context);assert(writes==1&&reads==count);
 }
 puts("ok: every nonzero full readback fails even if known or low byte zero, and no callback retry writes");
 return 0;
}
'''
(HERE/'test-r2.c').write_text(prefix+tail)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer']
built=subprocess.run(['gcc',*flags,str(HERE/'test-r2.c'),'-o',str(HERE/'test-r2')],capture_output=True,text=True)
assert built.returncode==0,built.stderr
run=subprocess.run([str(HERE/'test-r2')],capture_output=True,text=True)
assert run.returncode==0 and not run.stderr,(run.returncode,run.stdout,run.stderr)
cases=[s.removeprefix('ok: ') for s in run.stdout.splitlines() if s.startswith('ok: ')]
assert len(cases)==5
proof=json.loads((HERE/'candidate-result.json').read_bytes())
r1=json.loads((R1/'result.json').read_bytes())
for name,digest in r1['files'].items():assert sha((R1/name).read_bytes())==digest,name
files={n:sha((HERE/n).read_bytes()) for n in ['PlatformBm.c.candidate','eud-handoff-fragment.inc','direct-fifo.inc','launch.inc','core-functions.inc','test-r2.c','test-delta.py','candidate-result.json','source-evidence.json','boot-policy.patch','r1-to-r2.patch']}
result={'passed':True,'case_count':5,'cases':cases,'flags':flags,'files':files,'stdout':run.stdout,'stderr':run.stderr,
    'scope':'actual affected helper/launch paths with fake MMIO and BootServices boundary only',
    'R1_12_case_receipt_reused_not_rerun':proof['r1_12_case_receipt_sha256'],
    'R1_FDT_independent_receipt_reused_not_rerun':proof['r1_independent_FDT_review_sha256'],
    'unchanged_code_proof':'R2 full PlatformBm source with only predicate text reverted is byte-identical to frozen R1',
    'r1_files_unchanged':True,'firmware_built':False,'SDK_invoked':False,'device_accessed':False,'shared_tree_modified':False,
    'hardware_CSR_zero_proven':False,'hardware_write_executed':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'case_count':5,'candidate_source_sha256':files['PlatformBm.c.candidate']}))
