from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
runtime=json.loads((here/'runtime-validation.json').read_text())
assert runtime['front_sensor'][0]['bound'] and runtime['media']['media0']['imx471'] and runtime['taint']==0 and not runtime['temporary_helpers_loaded']
p=host.ssh('python3 -',input=(here/'capture-static-front.py').read_bytes(),timeout=120)
(host.PRIVATE/'static-capture-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['six_physical_raw10_frames_captured']
(here/'static-front-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
