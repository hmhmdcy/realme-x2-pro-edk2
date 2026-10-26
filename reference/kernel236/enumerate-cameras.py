"""List both physical camera graphs and verify idle state, without capturing."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k236-lab-fix/state-private.json').read_text())['exit_code']==0
out=root/'k236-media-enumeration';assert not out.exists();out.mkdir(mode=0o700)
result=subprocess.run(['cam','-l'],capture_output=True,timeout=20)
(out/'cam-list-private.log').write_bytes(result.stdout+result.stderr)
entries=[line.strip() for line in result.stdout.decode(errors='replace').splitlines() if re.match(r'^\d+:',line)]
graphs=[]
for node in sorted(Path('/dev').glob('media*')):
 graph=subprocess.run(['media-ctl','-d',str(node),'-p'],capture_output=True,timeout=15)
 (out/(node.name+'-private.txt')).write_bytes(graph.stdout+graph.stderr)
 assert graph.returncode==0
 graphs.append(graph.stdout.decode(errors='replace'))
sensors={node.name:(node/'name').read_text().strip() for node in Path('/sys/class/video4linux').glob('v4l-subdev*') if (node/'name').read_text().strip().startswith(('imx319','imx471'))}
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={name:log.count(needle) for name,needle in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
report=dict(stage=236,cam_exit=result.returncode,camera_entries=entries,sensor_subdevices=sensors,
            media_devices=len(graphs),rear_in_graph=any('imx319 7-0010' in graph for graph in graphs),
            front_in_graph=any('imx471 9-0010' in graph for graph in graphs),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,no_scene_capture=True)
assert result.returncode==0 and len(entries)==2 and report['rear_in_graph'] and report['front_in_graph']
assert report['taint']==0 and not any(faults.values())
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=70)
(host.PRIVATE / 'camera-enumeration-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(Path(__file__).resolve().parent / 'camera-enumeration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
