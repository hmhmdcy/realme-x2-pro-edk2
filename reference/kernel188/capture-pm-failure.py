from pathlib import Path
import hashlib
import json
import host

code = '''from pathlib import Path
import os,json,subprocess,re
os.umask(0o077)
root=Path('/var/lib/samurai/k188-pm-failure')
assert not root.exists()
root.mkdir(mode=0o700)
log=subprocess.check_output(['dmesg'],text=True)
(root/'dmesg-private.txt').write_text(log)
before=Path('/var/lib/samurai/k188-ssc-pm/dmesg-before-private.txt').read_text()
assert log.startswith(before)
extra=log[len(before):]
(root/'new-log-private.txt').write_text(extra)
stats={p.name:p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}
(root/'stats-after-private.json').write_text(json.dumps(stats,indent=2))
summary=dict(stage=188,suspend_trial_passed=False,post_resume_sensor_readiness=False,
 slpi_state=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),stats_after=stats,
 fault_delta={key:extra.count(value) for key,value in dict(warning='WARNING:',oops='Oops:',
  scm='Assign memory protection call failed',slpi_fatal='fatal error received',
  slpi_crash='2400000.remoteproc: crash',fastrpc='probe with driver qcom,fastrpc failed',
  gpu='gpu fault:',asoc='ASoC error').items()},
 trace_stats_scope='only one CPU retained by r1 dict-key bug; not all-CPU verified',
 automatic_recovery_disabled=True)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\\n')
print(json.dumps(summary))
# Only technical crash/PM lines, not the sensor RPC log or private identifiers.
for line in extra.splitlines():
 if any(key in line.lower() for key in ['remoteproc','fatal error','suspend entry','suspend exit','pm:','sns_','ssc_']):
  print(line)
'''
p=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'pm-failure-capture-private.log').write_bytes(p.stdout+p.stderr)
lines=p.stdout.decode().splitlines()
summary=json.loads(lines[0])
(Path(__file__).resolve().parent/'persistent-suspend-failure-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(p.stdout.decode())
