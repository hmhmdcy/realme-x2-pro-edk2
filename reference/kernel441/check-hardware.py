"""Audit saved real captures and causal PD10 changes without touching hardware."""
from pathlib import Path
import importlib.util,json,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('frame441',HERE/'frame-audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=P/('runtime-collected-'+attempt)
state=json.loads((root/'state.json').read_text())
assert state['terminal'] and not state['failure'] and state['formal_modules_restored'] and state['services_restored']
assert state['taint_before']==state['taint_after']==0
rows=[];completed=0
assert set(state['captures'])=={f'{w}x{h}-{kind}' for w,h in [(1280,720),(1920,1080)] for kind in ['native','isolated']}
for name,summary in state['captures'].items():
 folder=root/name;text=(folder/'client.log').read_text();w=summary['width'];h=summary['height']
 samples=[tuple(map(int,m)) for m in re.findall(r'SAMPLE sequence=(\d+) width=(\d+) height=(\d+) stride=(\d+) bytes=(\d+)',text)]
 assert len(samples)==summary['frames'] and len({s[0] for s in samples})==len(samples)
 assert all(s[1:]==(w,h,w,w*h*3//2) for s in samples)
 row=audit.audit_auto(text,'s5kgw1',folder,width=w,height=h,stride=w,coarse_bytes=summary['coarse_bytes'])
 app=set(re.findall(r'ADAPT_PID value=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text))
 assert len(app)==len(ipa)==1 and bool(app&ipa)==(not summary['isolated'])
 trace=summary['trace'];sof=trace['sof'];packet=(folder/f'tone-{sof}-params.bin').read_bytes()
 assert struct.unpack_from('<4I',packet)==(1,6008,3,0) and struct.unpack_from('<I',packet,32)[0]==5
 assert trace['full_kernel_sequence']==trace['pd10_kernel_sequence']
 assert row['queued_images']==summary['ipe_completed']
 completed+=summary['ipe_completed'];rows.append(dict(capture=name,width=w,height=h,**row))
replays=[]
for name,summary in state['replays'].items():
 folder=root/(name+'-replay');w=summary['width'];h=summary['height'];sof=summary['source_sof'];source=root/(name+'-native')
 for src,dst in [(f'tone-{sof}-full.nv12','full-private.bin'),(f'tone-{sof}-coarse.pd10','pd10-private.bin'),(f'tone-{sof}-params.bin','parameters-private.bin')]:assert (source/src).read_bytes()==(folder/dst).read_bytes()
 outputs=[(folder/f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
 assert all(len(x)==w*h*3//2 for x in outputs)
 assert outputs[0]==outputs[3]==(source/f'frame-{sof}.nv12').read_bytes()
 assert outputs[0]!=outputs[1] and outputs[0]!=outputs[2] and outputs[1]!=outputs[2]
 logs=(folder/'client.log').read_text();modes=[json.loads(line) for line in logs.splitlines() if line.startswith('{')]
 assert [m['mode'] for m in modes]==list(range(4)) and len({m['full_hash'] for m in modes})==1
 assert modes[0]['pd10_hash']==modes[3]['pd10_hash'] and len({m['pd10_hash'] for m in modes})==3
 replays.append(dict(width=w,height=h,jobs=4,repeat_real_and_live_bytes_equal=True,fixed_full_only_pd10_changes_output=True,passed=True));completed+=4
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed']==completed
assert not any(s[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
kernel=(root/'kernel-log-private.txt').read_text();assert kernel.count('A5 IPE frame completed request=')==completed
restart_heads=[tuple(map(int,m)) for m in re.findall(r'Dropped untagged auxiliary restart buffer pad=(\d+) sof=(\d+)',kernel)]
assert all(pad in [2,4] for pad,sof in restart_heads)
r=dict(stage=441,attempt=attempt,accepted_attempt=attempt if state['passed'] else None,rows=rows,replays=replays,total_ipe_completed=completed,same_sof_pd10_actual_gtm_wb_and_success_history=True,causal_ltm_consumption_both_sizes=True,logged_auxiliary_restart_heads_rejected=len(restart_heads),restart_output_pads=sorted({p for p,s in restart_heads}),unexpected_missing_sof_still_rejected=True,formal440_modules_services_resources_restored=True,new_faults=len(state['new_faults']),taint=0,installed=False,absolute_image_quality_accepted=False,full_goal_complete=False,passed=state['passed'])
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
