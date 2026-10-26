from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k210-libcamera-inspection');out.mkdir(mode=0o700)
results={}
for args,label in [(['cam','--help'],'help'),(['cam','--list'],'list')]:
    p=subprocess.run(args,capture_output=True,text=True,timeout=30);(out/(label+'-stdout-private.txt')).write_text(p.stdout);(out/(label+'-stderr-private.txt')).write_text(p.stderr)
    results[label]=dict(exit=p.returncode,stdout=p.stdout if label=='list' else None)
report=dict(stage=210,root_cli_inspection_only=True,libcamera_help_exit=results['help']['exit'],libcamera_list_exit=results['list']['exit'],camera_lines=[l.strip() for l in results['list']['stdout'].splitlines() if 'imx471' in l.lower()],sensor_still_suspended=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended')
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
