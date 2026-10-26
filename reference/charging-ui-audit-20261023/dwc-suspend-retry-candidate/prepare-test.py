"""Reuse only the explicit fake boundaries, not the previous 13-case main."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
old=HERE.parent/'dwc-suspend-halt-error-candidate/test-halt.c'
text=old.read_text().split('int main(void){',1)[0]
def replace(before,after):
 global text
 assert text.count(before)==1,before
 text=text.replace(before,after)
replace('int locks,polls,run_off,remove[2]',
        'bool inject_run_after_halt_read,inject_run_in_callback;\n int locks,polls,run_off,remove[2]')
replace('f.halt_seen=true;return DWC3_DSTS_DEVCTRLHLT;',
        'f.halt_seen=true;if(f.inject_run_after_halt_read){f.reg[DWC3_DCTL]|=DWC3_DCTL_RUN_STOP;f.halt_seen=false;f.inject_run_after_halt_read=false;}return DWC3_DSTS_DEVCTRLHLT;')
replace("f.callbacks++;event('C');}",
        "f.callbacks++;event('C');if(f.inject_run_in_callback){f.reg[DWC3_DCTL]|=DWC3_DCTL_RUN_STOP;d->pullups_connected=true;f.halt_seen=false;}}")
text+='''static void no_repeat(void){
 assert(f.core_active&&f.phy_active&&f.event_buffer_live&&f.irq_registered&&f.locks==0);
 assert(f.exits==0&&f.irq_joins==0&&f.phy_puts==0&&f.pinctrls==0&&f.callbacks==0);
 assert(f.stop_all==1&&f.run_off==1&&f.masks==1&&f.remove[0]==1&&f.remove[1]==1);
 assert(f.reg[DWC3_GUSB2PHYCFG(0)]==(BIT(24)|DWC3_GUSB2PHYCFG_ENBLSLPM));
 assert(f.reg[DWC3_GUSB3PIPECTL(0)]==BIT(25));
}
static void never_connected(bool halt){
 reset(false,!halt,DWC3_GCTL_PRTCAP_DEVICE);dwc.pullups_connected=dwc.connected=false;f.reg[DWC3_DCTL]=0;
}
int main(void){
 /* Old errno fix prevents the first exit, but old flag-only retry still exits. */
 reset(false,true,DWC3_GCTL_PRTCAP_DEVICE);
 assert(previous_suspend_common(&dwc,PMSG_SUSPEND)==-ETIMEDOUT);
 assert(f.core_active&&!dwc.pullups_connected&&f.run_off==1);
 assert(previous_suspend_common(&dwc,PMSG_SUSPEND)==0&&f.exits==1&&f.unsafe_exits==1);cases++;
 for(int role=DWC3_GCTL_PRTCAP_DEVICE;role<=DWC3_GCTL_PRTCAP_OTG;role++){
  reset(false,true,role);assert(dwc3_pm_suspend(&dwc)==-ETIMEDOUT);retained_failure(false);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==0&&f.polls==2001);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==0&&f.polls==2002);cases++;
  reset(false,true,role);assert(dwc3_pm_suspend(&dwc)==-ETIMEDOUT);f.halt_fault=false;
  assert(dwc3_pm_suspend(&dwc)==0&&f.exits==1&&f.unsafe_exits==0&&f.irq_joins==1&&f.callbacks==1);
  assert(f.run_off==1&&f.stop_all==1&&f.masks==1&&f.polls==2001);cases++;
  /* First real stop keeps its original true-intent reconnect policy. A later
   * no-pullup miss must not blindly reset/reconnect or repeat DMA teardown.
   */
  reset(true,true,role);f.connect_errno=-EIO;
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.reconnects==1);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==1);
  f.halt_fault=false;assert(dwc3_pm_suspend(&dwc)==0&&f.reconnects==1&&f.run_off==1&&f.unsafe_exits==0);cases++;
 }
 never_connected(true);assert(dwc3_pm_suspend(&dwc)==0&&f.run_off==0&&f.stop_all==0&&f.masks==0&&f.exits==1&&f.unsafe_exits==0);cases++;
 never_connected(false);assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.polls==1&&f.stop_all==0&&f.run_off==0&&f.reconnects==0&&f.exits==0);cases++;
 never_connected(true);f.reg[DWC3_DCTL]=DWC3_DCTL_RUN_STOP;
 assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.stop_all==0&&f.run_off==0&&f.exits==0);cases++;
 never_connected(false);dev.runtime_suspended=true;f.core_active=f.phy_active=false;
 assert(dwc3_gadget_suspend(&dwc)==0&&f.polls==0&&f.stop_all==0&&f.callbacks==1);cases++;
 never_connected(false);dev.runtime_suspended=true;f.core_active=f.phy_active=false;
 assert(dwc3_pm_suspend(&dwc)==0&&f.polls==0&&f.callbacks==0&&f.exits==0);cases++;
 /* Model the real fact that run/stop writers are not all under dwc.lock:
  * a request arriving between the two status reads is caught by DCTL.
  */
 never_connected(true);f.inject_run_after_halt_read=true;
 assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.exits==0&&f.stop_all==0&&f.run_off==0);cases++;
 /* Explicit limitation control: this snapshot is not a later lifetime lock.
  * A separate producer injected AFTER the gate can still invalidate HALT.
  * This is not counted as a concurrency/PM safety success.
  */
 never_connected(true);f.inject_run_in_callback=true;
 assert(dwc3_pm_suspend(&dwc)==0&&f.unsafe_exits==1);cases++;
 reset(false,false,DWC3_GCTL_PRTCAP_DEVICE);
 assert(dwc3_pm_suspend(&dwc)==0&&f.run_off==1&&f.stop_all==1&&f.polls==1&&f.unsafe_exits==0);cases++;
 printf("{\\"passed\\":true,\\"cases\\":%u,\\"old_two_attempt_failure_reproduced\\":true,\\"new_retry_miss_no_repeated_DMA_or_reset\\":true,\\"late_halt_allows_existing_path\\":true,\\"post_snapshot_producer_lifetime_not_serialized\\":true,\\"full_resume_unwind_complete\\":false}\\n",cases);
 return 0;
}
'''
(HERE/'test-retry.c').write_text(text,newline='\n')
(HERE/'fixture-source-reuse.json').write_text(json.dumps(dict(
 previous_boundary_fixture_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
 candidate_fixture_sha256=hashlib.sha256(text.encode()).hexdigest(),
 previous_13_case_main_not_used=True,actual_new_cases=15,
 explicit_post_snapshot_concurrency_limitation_control=True),indent=2)+'\n')
print(json.dumps(dict(prepared=True,fixture_sha256=hashlib.sha256(text.encode()).hexdigest())))
