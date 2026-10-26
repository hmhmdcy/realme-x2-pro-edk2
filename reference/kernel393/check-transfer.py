from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel388'
strip=lambda p:'\n'.join(l for l in p.read_text().splitlines() if not l.startswith('#include'))+'\n'
source=(P/'camss-icp-a5-boot.c.proposed').read_text()
def function(name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert m,name;return m.group()
dma=(OLD/'dma-model-provider.h').read_text()+strip(OLD/'camss-icp-a5-dma.h')+strip(OLD/'camss-icp-a5-dma.c')
provider=(OLD/'transfer-model-provider.h').read_text().replace('bool initialized,cpu_enabled,','bool irq_enabled,config_fw_mapped;u32 watchdogs,protocol_errors;\n bool initialized,cpu_enabled,')
provider=provider.replace('a->command_queued=mode!=9;','a->command_queued=mode!=9;\n if(mode==13)return -EINVAL;\n if(mode==14){a->session_reply=true;return -EREMOTEIO;}')
provider=provider.replace('m->mapped=0;return 0;}','if(mode==17)return -EIO;m->mapped=0;return 0;}',1)
ipe=strip(P/'camss-icp-a5-ipe.h.proposed')
tests=(OLD/'transfer-model-cases.c').read_text();split=tests.index('int main(void)');encoder=tests[:split].replace('static int camss_a5_ipe_','int camss_a5_ipe_').replace('mode==5?-EINVAL:0','mode==5 || mode==17?-EINVAL:0');cases=tests[split:]
cases=cases.replace('scenario<=12','scenario<=17').replace('.initialized=true,.cpu_enabled=true,','.initialized=true,.cpu_enabled=true,.irq_enabled=true,')
cases=cases.replace('  int ret=camss_a5_ipe_run(&a,&session,&job);','''  if(scenario==15)a.irq_enabled=false;
  if(scenario==16)a.protocol_errors=1;
  enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
  int ret=camss_a5_ipe_run_status(&a,&session,&job,&result);''')
cases=cases.replace('scenario==10?-EOVERFLOW:-EINVAL','scenario==10?-EOVERFLOW:scenario==14?-EREMOTEIO:scenario==15?-ENODEV:scenario==16?-EBUSY:-EINVAL')
cases=cases.replace('  assert(ret==expected);','''  assert(ret==expected);
  enum camss_a5_ipe_result wanted=scenario==0 || scenario==11?CAMSS_A5_IPE_COMPLETE:
   (scenario>=1 && scenario<=5) || scenario==12?CAMSS_A5_IPE_REJECTED:CAMSS_A5_IPE_RESET_REQUIRED;
  assert(result==wanted);''')
cases=cases.replace('scenario==6 || scenario==7 || scenario==8;','scenario==6 || scenario==7 || scenario==8 || scenario==13 || scenario==14;')
cases=cases.replace('  if(retained){','''  if(scenario==17){
   assert(result==CAMSS_A5_IPE_RESET_REQUIRED && !hw_frames && a.request.cpu && bo_live==1);
   /* Cleanup failed before any firmware MAP; classify conservatively. */
   mode=0;a.cpu_enabled=false;assert(!free_memory(&a));
  }else if(retained){''')
body='\n'.join(function(n) for n in ['nv12_layout_valid','camss_a5_backing_owned','free_imported_images','free_memory','free_transfer_memory','transfer_region_locked','transfer_alloc','transfer_released','camss_a5_ipe_run_status','camss_a5_ipe_run'])
code=dma+provider+ipe+encoder+body+cases
model=P/'transfer-model.c';model.write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'transfer-model')],capture_output=True)
(P/'transfer-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
q=subprocess.run([str(P/'transfer-model')],capture_output=True);(P/'transfer-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
match=re.fullmatch(r'TRANSFER_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
r=dict(stage=393,actual_core_and_dma_functions=True,asan_ubsan=True,cases=int(match[1]),same_errno_preflight_and_submitted_failures_distinguished=True,preflight_fence_timeout_local=True,failed_cleanup_not_local=True,missing_irq_or_protocol_error_not_local=True,unknown_map_frame_unmap_refs_retained=True,old_pointer_fixture_and_mixed_rejection_kept=True,hardware_error_concurrency_not_claimed=True,passed=True)
(HERE/'transfer-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
