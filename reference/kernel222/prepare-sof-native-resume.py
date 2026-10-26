from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222')
inspection=json.loads((private/'sof-trial-inspection-private.json').read_text());assert inspection['phase']=='original-restored' and inspection['same_boot'] and inspection['taint']==0
assert all(x['exit']==0 for x in inspection['commands']) and inspection['gap_summary']['frame_start_emitter_observed']
r=dict(stage=222,first_event_reader_failed_after_one_event=True,empty_event_queue_kernel_errno_is_enoent=True,candidate_gap_capture_16_frames_succeeded=True,libcamera_saw_frame_start_emitter=True,original_module_graph_and_wireplumber_restored=True,taint=0,no_reboot_or_flash=True)
(here/'sof-first-native-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n')
code=(here/'native-sof-trial.py').read_text().replace("out=root/'k222-sof-trial'","out=root/'k222-sof-trial-r2'").replace("stage/'gap-runner.py'","stage/'gap-runner-r2.py'")
code=code.replace('if error.errno==11:break','if error.errno in [2,11]:break').replace("state['phase']='original-restore-pending';save()", "state['event_reader_errors']=event_errors;state['phase']='original-restore-pending';save()")
compile(code,'native-sof-trial-r2','exec');(here/'native-sof-trial-r2.py').write_text(code)
wrapper=(here/'run-sof-trial.py').read_text().replace("here/'native-sof-trial.py'","here/'native-sof-trial-r2.py'").replace("'sof-trial-host-private.log'","'sof-trial-r2-host-private.log'")
compile(wrapper,'run-sof-trial-r2','exec');(here/'run-sof-trial-r2.py').write_text(wrapper)
print(json.dumps(r))
