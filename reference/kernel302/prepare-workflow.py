"""Prepare bounded native runs; keep scene statistics and control traces private."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300'
s=(OLD/'pack-candidate.py').read_text().replace('stage=300','stage=302').replace("HERE.parent/'kernel299/manual-sunny-imx319-bls.yaml'","HERE/'imx319-manual.yaml'")
ast.parse(s);(HERE/'pack-candidate.py').write_text(s)
s=(OLD/'native-ipa.py').read_text().replace('k300-ipa','k302-controls').replace('stage=300','stage=302')
s=s.replace(r" ipa_pids=set(map(int,re.findall(r'IPA init pid=(\d+)',text)))",r" all_ipa_pids=set(map(int,re.findall(r'IPA init pid=(\d+)',text)))"+'\n'+r" ipa_pids=set(map(int,re.findall(r'IPA init pid=(\d+) model=imx319',text)))")
s=s.replace('CamssVfe:DEBUG,IPACamss:DEBUG','CamssVfe:DEBUG,DelayedControls:DEBUG,IPACamss:DEBUG')
s=s.replace(' for pid in ipa_pids:', ' for pid in all_ipa_pids:')
s=s.replace("application_pids=sorted(app_pids),ipa_pids=sorted(ipa_pids)","application_pids=sorted(app_pids),ipa_pids=sorted(ipa_pids),all_initialized_ipa_pids=sorted(all_ipa_pids)")
s=s.replace("len(epochs)==3", "len(epochs)==2").replace("r['frames']>=24", "r['frames']>=240").replace("len(applied)==3", "len(applied)==2").replace("=={1,2,3}", "=={1,2}").replace("len(pairs)>=60", "len(pairs)>=480").replace("report['ipa_metadata_frames']==72", "report['ipa_metadata_frames']==report['application_frames']")
anchor=" (root/'summary-private.json').write_text";pos=s.index(anchor)
s=s[:pos]+r''' sensor_metadata=re.findall(r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)
 sensor_commands=re.findall(r'APPLICATION_SENSOR_COMMAND epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)
 contexts=re.findall(r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)
 report.update(sensor_metadata_frames=len(sensor_metadata),standard_sensor_control_commands=len(sensor_commands),sensor_sof_contexts=len(contexts),
  known_sensor_sof_contexts=sum(int(c[2]) for c in contexts),sensor_helper_and_delayed_controls_integrated=True,
  sensor_values_are_quantized_effective_sof_context_not_requested_values=True)
 report['passed']=(report['passed'] and len(sensor_metadata)==report['application_frames'] and len(sensor_commands)==18
  and len(contexts)>=480 and all(c[2]=='1' for c in contexts))
'''+s[pos:]
ast.parse(s);(HERE/'native-controls.py').write_text(s)
s=(OLD/'launch-ipa.py').read_text().replace('k300-ipa','k302-controls').replace('native-ipa.py','native-controls.py').replace("f'ipa-{run}-launch","f'controls-{run}-launch")
ast.parse(s);(HERE/'launch-controls.py').write_text(s)
s=(OLD/'poll-ipa.py').read_text().replace('k300-ipa','k302-controls').replace("f'ipa-{run}-poll","f'controls-{run}-poll")
a=s.index(" (HERE/'ipa-capture-validation.json')");b=s.index("summary=report.get",a)
s=s[:a]+''' summary=report['summary'];public={k:v for k,v in summary.items() if k!='exact_sof_pairs'}
 public['exact_sof_pairs_count']=len(summary['exact_sof_pairs'])
 (HERE/f'controls-capture-{run}-validation.json').write_text(json.dumps(public,indent=2)+'\\n')
'''+s[b:]
ast.parse(s);(HERE/'poll-controls.py').write_text(s)
print('Prepared private302 package and guarded state-restoring native workflow.')
