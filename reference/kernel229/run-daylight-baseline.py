from pathlib import Path
import json
import sys
import host

ref = Path(__file__).resolve().parent
assert sys.argv[1:] in (['rgb'], ['raw'])
kind = sys.argv[1]
dimensions = '2296 1728' if kind == 'rgb' else '2304 1728'
code = (ref / 'native-daylight-baseline.py').read_bytes()
result = host.ssh('python3 - ' + kind + ' 0 ' + dimensions + ' 1 system', input=code, timeout=75)
(host.PRIVATE / (kind + '-daylight-baseline-host-private.log')).write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / (kind + '-daylight-baseline-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
assert report['program_exit'] == 0 and len(report['frames']) == 6
assert report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored'] and report['camera_devices_suspended']
assert report['taint'] == 4096 and not any(report['fault_delta'].values())
print(json.dumps(report))
