from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
assert json.loads((R/'controlled-rear-r2-validation.json').read_text())['passed']
source=(R/'native-controlled-capture-r2.py').read_text().replace("assert (which,kind)==('rear','raw')","assert (which,kind)==('rear','rgb')").replace('k238-controlled-rear-r14-r2','k238-controlled-rear-rgb-r14').replace('instances/k238_controls_r2','instances/k238_rgb_controls').replace('/physical-control-probe','/physical-rgb-control-probe').replace('raw_cpu_statistics_path_verified','cpu_rgb_control_metadata_verified')
start=(R/'start-controlled-capture-r2.py').read_text().replace('native-controlled-capture-r2.py','native-controlled-rgb-capture.py').replace('control-probe-build-validation.json','rgb-control-probe-build-validation.json').replace('physical-control-probe238','physical-rgb-control-probe238').replace('physical-control-probe','physical-rgb-control-probe').replace('k238-controlled-rear-r14-r2','k238-controlled-rear-rgb-r14').replace('controlled-capture-r2-launch','controlled-rgb-capture-launch').replace("str(source),'rear','raw'","str(source),'rear','rgb'")
# The binary replacement is intentionally one pass: fix doubled RGB prefix if any.
start=start.replace('physical-rgb-rgb-control-probe','physical-rgb-control-probe')
poll=(R/'poll-controlled-capture-r2.py').read_text().replace('k238-controlled-rear-r14-r2','k238-controlled-rear-rgb-r14').replace('controlled-rear-r2-validation.json','controlled-rear-rgb-validation.json').replace('controlled-capture-r2-poll','controlled-rgb-capture-poll').replace('raw_cpu_statistics_path_verified','cpu_rgb_control_metadata_verified')
for name,text in [('native-controlled-rgb-capture.py',source),('start-controlled-rgb-capture.py',start),('poll-controlled-rgb-capture.py',poll)]:
 ast.parse(text);p=R/name;assert not p.exists();p.write_text(text)
print('Prepared one rear RGB48-frame candidate experiment, original RAW results preserved')
