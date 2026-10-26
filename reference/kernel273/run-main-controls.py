"""Measure physical GW1 RAW/RGB control response on the new guarded boot."""
from pathlib import Path
import ast,hashlib,json,shlex,sys
import host
R=Path(__file__).resolve().parent;proof=json.loads((R/'main-control-probe-build-validation.json').read_text())
mode=sys.argv[1];assert mode in ['manual','auto'];label='main-'+mode+'-r1'
response=host.PRIVATE/(label+'-response-private.log');assert not response.exists()
remote='/run/samurai-camera273-probes/main-control-probe273'
if mode=='manual':
 binary=(host.PRIVATE/'main-control-probe273').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['binary_sha256']
 code="from pathlib import Path;import hashlib,os,sys;p=Path(%r);assert not Path('/var/lib/samurai/k273-main-manual-r1').exists();p.parent.mkdir(mode=0o755,exist_ok=True);b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;assert not p.exists() or p.read_bytes()==b;\nif not p.exists():p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
 host.ssh('python3 -c '+shlex.quote(code),input=binary,timeout=20)
else:assert json.loads((R/'main-manual-r1-validation.json').read_text())['exit']==0
t=ast.parse((R.parent/'kernel271/run-control-baseline.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
value=n.value
while isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute):value=value.func.value
code=ast.literal_eval(value)
changes=[("label='baseline-'+mode+'-r1'","label='main-'+mode+'-r1'"),('k271-','k273-'),('k270-work','k273-work'),('stage=271','stage=273'),
 ("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010']"),
 ("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')"),
 ("['cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']","['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']"),
 ('len(rails)==6','len(rails)==9'),('kernel/drivers/media/i2c/s5k3m5.ko','kernel/drivers/media/i2c/s5kgw1.ko'),
 ('22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72','0c907b122065b8657dc9f9e68ff17784c5419ed1994fe9f1ced5ccfa60c90ade'),
 ('/run/samurai-camera271-probes/telephoto-control-probe271',remote),('s5k3m5 8-002d','s5kgw1 6-0010'),
 ('/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10'),
 ("'s5k3m5'","'s5kgw1'"),('time.sleep(1)','time.sleep(3)')]
for a,b in changes:assert a in code,a;code=code.replace(a,b)
line=" assert 'test_pattern: 0' in subprocess.check_output(['v4l2-ctl','-d',node,'--get-ctrl=test_pattern'],text=True)\n"
assert code.count(line)==1;code=code.replace(line,'')
code=code.replace('__MODE__',repr(mode)).replace('__SHA__',repr(proof['binary_sha256']))
response.write_bytes(b'SUBMISSION INTENT: inspect the same k273-main context if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=140,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the submitted main-camera control process before another capture'
d=json.loads(q.stdout);(R/(label+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
