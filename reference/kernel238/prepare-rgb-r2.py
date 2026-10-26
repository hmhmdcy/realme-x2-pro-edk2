from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
failed=json.loads((R/'controlled-rear-rgb-validation.json').read_text());assert failed['program_exit']==1 and failed['frames']==[] and all(failed[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed'])
source=(R/'native-controlled-rgb-capture.py').read_text().replace('k238-controlled-rear-rgb-r14','k238-controlled-rear-rgb-r14-r2').replace('instances/k238_rgb_controls','instances/k238_rgb_controls_r2')
old="dims=(1632,1224) if which=='rear' else ((2304,1728) if kind=='raw' else (2296,1728))";assert source.count(old)==1;source=source.replace(old,'dims=(1624,1224)')
start=(R/'start-controlled-rgb-capture.py').read_text().replace('native-controlled-rgb-capture.py','native-controlled-rgb-capture-r2.py').replace('k238-controlled-rear-rgb-r14','k238-controlled-rear-rgb-r14-r2').replace('controlled-rgb-capture-launch','controlled-rgb-capture-r2-launch')
poll=(R/'poll-controlled-rgb-capture.py').read_text().replace('k238-controlled-rear-rgb-r14','k238-controlled-rear-rgb-r14-r2').replace('controlled-rear-rgb-validation.json','controlled-rear-rgb-r2-validation.json').replace('controlled-rgb-capture-poll','controlled-rgb-capture-r2-poll')
for name,text in [('native-controlled-rgb-capture-r2.py',source),('start-controlled-rgb-capture-r2.py',start),('poll-controlled-rgb-capture-r2.py',poll)]:
 ast.parse(text);p=R/name;assert not p.exists();p.write_text(text)
print(json.dumps(dict(stage=238,first_rgb_native_size_rejection_retained=True,raw_input_1632_rgb_output_1624_cpu_border_accounted=True,new_context_distinct=True)))
