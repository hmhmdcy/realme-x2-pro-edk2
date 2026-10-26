"""Confirm active streaming controls before drawing a sensor-clock conclusion."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
original=(here/'measure-current-raw-timing.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k217-current-raw-timing'","out=root/'k217-current-raw-timing-r2'")
old="p=subprocess.run(['cam','--camera',ids[0],'--stream=role=raw','--capture=12'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=20)"
new="""process=subprocess.Popen(['cam','--camera',ids[0],'--stream=role=raw','--capture=120'],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    active_samples=[]
    for _ in range(5):
        time.sleep(0.15)
        if process.poll() is None:active_samples.append(controls())
    try:stdout,stderr=process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        process.send_signal(signal.SIGINT)
        try:stdout,stderr=process.communicate(timeout=5)
        except subprocess.TimeoutExpired:process.kill();stdout,stderr=process.communicate(timeout=3)
    from types import SimpleNamespace
    p=SimpleNamespace(returncode=process.returncode,stdout=stdout,stderr=stderr)"""
assert old in code;code=code.replace(old,new).replace('len(frames)==12','len(frames)==120').replace('physical_raw_frames=12,','physical_raw_frames=120,active_control_samples=active_samples,streaming_control_values_not_assumed_from_pre_stream_snapshot=True,')
compile(code,'native-active-raw-timing217','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'active-raw-timing-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'active-raw-timing-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key not in ['intervals_seconds','sequence_deltas']}))
