from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
builder=here.parent/'kernel215/run-default-clients.py';prefix=builder.read_text().split("p=host.ssh('python3 -'",1)[0];namespace={'__file__':str(builder)};exec(compile(prefix,'default-clients-code-generation','exec'),namespace)
code=namespace['code'].replace('k215-','k216-').replace('samurai-camera215-client','samurai-camera216-client').replace('stage=215','stage=216')
code=code.replace("out=Path('/var/lib/samurai/k216-default-clients')","out=Path('/var/lib/samurai/k216-default-clients-r2')")
needle="before=subprocess.check_output(['dmesg']);(out/'client-dmesg-before-private.txt').write_bytes(before)"
extra="""limits=subprocess.check_output(['v4l2-ctl','-d',sensor,'--list-ctrls'],text=True,timeout=10)
assert 'max=960' in next(line for line in limits.splitlines() if 'analogue_gain' in line)
p=subprocess.run(['cam','--camera',camera_id,'--list-controls'],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=15)
(out/'standard-camera-control-ranges-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0
gain_lines=[line for line in (p.stdout+p.stderr).splitlines() if 'AnalogueGain' in line]
"""
assert needle in code;code=code.replace(needle,extra+needle)
code=code.replace('stage=216,uid=10000,','stage=216,uid=10000,kernel_gain_code_max=960,factory_nominal_gain_max=16.0,pre_config_standard_gain_control_listed=bool(gain_lines),standard_manual_gain_api_not_accepted=True,')
compile(code,'native-default-clients216','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'default-clients-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'default-clients-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
