"""Reuse the independently checked LSC/CCM oracle and add static Gamma checks."""
from pathlib import Path
import copy,json,sys
sys.path.insert(0,'/usr/lib/python3/dist-packages')
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runs=sys.argv[1].split(',');selected_runs={}
if len(runs)>1:
 combined=None;source_reports=[]
 for run in runs:
  item=json.loads((P/('probe-'+run+'-observation.json')).read_text())
  assert item['state']['terminal'] and not item['worker_live'] and item['state']['summary']['passed']
  source_reports.append(item['state']['summary'])
  if combined is None:combined=dict(state=dict(terminal=True,phase='derived-complete',summary=copy.deepcopy(item['state']['summary'])),worker_live=False,logs={},failures={},derived_not_worker_observation=True)
  combined['logs'].update(item['logs']);combined['state']['summary']['captures'].update(item['state']['summary']['captures'])
  for name in item['state']['summary']['captures']:selected_runs[name]=run
 combined['state']['summary']['health']=source_reports[-1]['health'];combined['source_reports']=source_reports
 tag='-'.join(runs)+'-combined';(P/('probe-'+tag+'-observation.json')).write_text(json.dumps(combined)+'\n');sys.argv[1]=tag
else:
 item=json.loads((P/('probe-'+runs[0]+'-observation.json')).read_text())
 selected_runs={name:runs[0] for name in item['state']['summary']['captures']}
(P/'selected-runs-private.json').write_text(json.dumps(selected_runs)+'\n')
s=(HERE.parent/'kernel342/analyze-installed-iq.py').read_text()
s=s.replace("P/'profiles'/(name+'.yaml')","P/'profiles'/item['profile']").replace("line.startswith('CCM_FRAME ')","line.startswith('GAMMA_FRAME ')")
s=s.replace('rows=[];ccm_bytes=0','rows=[];ccm_bytes=0;phase_signatures={}')
s=s.replace("  elif 'ISP applied epoch=' in line:","  elif 'GAMMA_APPLIED ' in line:\n   gamma_acks=[{k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('GAMMA_APPLIED ',1)[1])}]\n  elif 'ISP applied epoch=' in line:")
s=s.replace("hist.append((fields['first-sof'],fields['revision']))","hist.append((fields['first-sof'],fields['revision']));assert fields['gamma']==1")
s=s.replace('hist.sort();first=',"assert log.count('GAMMA_APPLIED ')==1 and len(gamma_acks)==1 and gamma_acks[0]['revision']==0\n hist.sort();first=")
s=s.replace("if frame['settled']=='1':settled[int(frame['phase'])]=frame",'''if frame['settled']=='1':
   settled[int(frame['phase'])]=frame
   phase_signatures.setdefault(name,{})[int(frame['phase'])]=dict(sof=sof,revision=revision,trace=state['mesh-trace'],
    matrix=frame.get('matrix'),red=frame.get('red'),blue=frame.get('blue'),exposure=frame.get('exposure'),gain=frame.get('gain'))
  assert sof>=gamma_acks[0]['first-sof']''')
s=s.replace('stage=342','stage=349').replace('installed_core_and_ipa=True','candidate_core_and_ipa=True').replace('len(rows)==4','len(rows)==7')
s=s.replace('installed_package_compatibility=summary','combined_temporary_compatibility=summary')
s=s.replace('mode_specific_exposure_table_binding_verified=False','factory_gamma_uses_confirmed_mode_binding=True')
s=s.replace("'installed-iq-validation.json'","'runtime-iq-validation.json'")
s=s.replace("(HERE/'runtime-iq-validation.json').write_text", "(P/'phase-signatures-private.json').write_text(json.dumps(phase_signatures)+'\\n')\n(HERE/'runtime-iq-validation.json').write_text")
exec(compile(s,str(HERE/'analyze-runtime.py'),'exec'),dict(__file__=str(HERE/'analyze-runtime.py'),__name__='__main__'))
path=HERE/'runtime-iq-validation.json';report=json.loads(path.read_text());report.update(source_runs=runs,selected_case_run=selected_runs,
 total_observed_frames=sum(sum(c['frames'] for c in json.loads((P/('probe-'+r+'-observation.json')).read_text())['state']['summary']['captures'].values()) for r in runs))
path.write_text(json.dumps(report,indent=2)+'\n')
