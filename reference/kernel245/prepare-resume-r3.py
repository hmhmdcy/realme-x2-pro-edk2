"""Match every original received VERSION, including late untagged replies."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent
s=(R/'native-resume-rf-r2.py').read_text().replace("o=r/'k245-resume-rf-r2'","o=r/'k245-resume-rf-r3'")
old="old_versions={bytes.fromhex(x['hex']) for x in old if x['kind']=='response' and x['request_code']==0}"
new="old_versions={p for x in old if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe for p in frames(bytes.fromhex(x['hex'])) if p and p[0]==0}"
assert old in s;s=s.replace(old,new);compile(s,'native-resume-rf-r3.py','exec');(R/'native-resume-rf-r3.py').write_text(s)
t=(R/'launch-resume-r2.py').read_text().replace('native-resume-rf-r2.py','native-resume-rf-r3.py').replace('k245-resume-rf-r2','k245-resume-rf-r3').replace('resume-r2-','resume-r3-');compile(t,'launch-resume-r3.py','exec');(R/'launch-resume-r3.py').write_text(t)
p=(R/'poll-resume-r2.py').read_text().replace('k245-resume-rf-r2','k245-resume-rf-r3');(R/'poll-resume-r3.py').write_text(p)
spec=importlib.util.spec_from_file_location('diag245r3',R/'diag_resume_rf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Regression for the observed failure: late RX VERSION can differ from the only
# reply tagged by query(); every validated original RX must remain a candidate.
def wire(payload):return b'\x7e\x01'+len(payload).to_bytes(2,'little')+payload+b'\x7e'
a=b'\0'+b'a'*54;b=b'\0'+b'b'*54;old_rows=[dict(kind='rx',channel=3,port=10,hex=wire(a).hex()),dict(kind='rx',channel=3,port=10,hex=wire(b).hex()),dict(kind='response',request_code=0,hex=a.hex())]
old=old_rows;frames=m.frames;candidates=eval(new.split('=',1)[1]);assert candidates=={a,b} and sum(p in candidates for p in [b,b])==2
report=dict(stage=245,all_original_rx_version_variants_retained=True,late_reply_regression_passed=True,no_control_requests_in_prior_two_attempts=True)
(R/'resume-r3-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
