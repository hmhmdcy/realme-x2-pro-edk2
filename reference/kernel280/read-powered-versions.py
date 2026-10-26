"""Read only HW_VERSION at DT-described, clocked blocks during normal capture.

No MMIO writes, forced PM references, module replacement, or firmware changes.
The two selected ordinary clients own the power/stream lifecycle.
"""
from pathlib import Path
import ast
import json
import host

ROOT = Path(__file__).resolve().parent
response = host.PRIVATE / 'version-r1-response-private.log'
assert not response.exists(), 'Inspect the prior handset worker, do not replay it'
template = ast.parse((ROOT.parent / 'kernel276/test-manager-lifetime.py').read_text())
node = next(n for n in template.body if isinstance(n, ast.Assign) and
            any(isinstance(x, ast.Name) and x.id == 'code' for x in n.targets) and isinstance(n.value, ast.Call))
code = ast.literal_eval(node.value.func.value)
code = code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1', 'k280-version-r1')
code += r'''
import mmap,re,struct,signal
save();report={};versions={};legs=[];forced=False
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
 assert health()['passed']
 camss=Path('/sys/bus/platform/devices/acb3000.camss')
 node=camss/'of_node'
 names=(node/'reg-names').read_bytes().rstrip(b'\0').split(b'\0')
 data=(node/'reg').read_bytes();assert len(data)==len(names)*16
 mapping={name.decode():struct.unpack_from('>QQ',data,i*16) for i,name in enumerate(names)}
 expected={'vfe0':0xacaf000,'vfe1':0xacb6000,'csid0':0xacb3000,'csid1':0xacba000}
 for name,address in expected.items():assert mapping[name][0]==address and mapping[name][1]>=4
 # These first words are the read-only version registers in the OEM sources.
 clocks_by_block={'vfe0':'cam_cc_ife_0_clk','vfe1':'cam_cc_ife_1_clk',
                  'csid0':'cam_cc_ife_0_csid_clk','csid1':'cam_cc_ife_1_csid_clk'}
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 ids={'wide':'/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10',
      'front':'/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10'}
 for which,camera in ids.items():
  with (root/(which+'-stdout-private.log')).open('xb') as out,(root/(which+'-stderr-private.log')).open('xb') as err:
   proc=subprocess.Popen(['/usr/bin/cam','-c',camera,'--capture=120'],stdout=out,stderr=err,preexec_fn=demote,
                         env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name))
   state.update(state='capture-'+which,child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
   deadline=time.monotonic()+25
   while proc.poll() is None and time.monotonic()<deadline:
    if (camss/'power/runtime_status').read_text().strip()=='active':
     lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
     block_clocks={line.split()[0]:int(line.split()[1]) for line in lines if line.split() and line.split()[0] in clocks_by_block.values()}
     for name,clock in clocks_by_block.items():
      if name in versions or block_clocks.get(clock,0)<=0:continue
      # Recheck the owning block's clock just before the sole read.
      latest=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
      if not any(l.split() and l.split()[0]==clock and int(l.split()[1])>0 for l in latest):continue
      fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
      try:
       with mmap.mmap(fd,4096,access=mmap.ACCESS_READ,offset=expected[name]) as registers:
        value=struct.unpack_from('<I',registers,0)[0]
      finally:os.close(fd)
      versions[name]=dict(address=hex(expected[name]),raw=hex(value),generation=value>>28&0xf,
                          revision=value>>16&0xfff,stepping=value&0xffff,clock=clock,read_only=True)
      state['versions']=versions;save()
    time.sleep(.03)
   if proc.poll() is None:
    forced=True;proc.send_signal(signal.SIGINT);proc.wait(timeout=8)
   assert proc.returncode==0 and not forced
  text=(root/(which+'-stdout-private.log')).read_text()
  sequence=[int(n) for n in re.findall(r'seq:\s*(\d+)',text)]
  assert len(sequence)==120 and all(b>a for a,b in zip(sequence,sequence[1:]))
  legs.append(dict(camera=which,frames=len(sequence),exit=proc.returncode))
  end=time.monotonic()+4
  while not health()['passed'] and time.monotonic()<end:time.sleep(.1)
  assert health()['passed']
 assert any(name.startswith('vfe') for name in versions) and any(name.startswith('csid') for name in versions)
 report=dict(stage=280,versions=versions,legs=legs,read_only_mmio_only_hw_version=True,
             blocks_derived_from_deployed_dt=True,clock_checked_before_reads=True,no_power_forcing=True)
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  state.update(state='needs-attention-live-capture',terminal=False);save();raise RuntimeError('Inspect this existing capture before any new experiment')
 time.sleep(2);after=health();report.update(error=error,health=after)
 state.update(state='terminal',terminal=True,exit_code=0 if not error and after['passed'] else 1);save()
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
compile(code, 'read-powered-versions280-worker', 'exec')
response.write_bytes(b'SUBMISSION INTENT: inspect /var/lib/samurai/k280-version-r1 before replay.\n')
run = host.ssh('python3 -', input=code.encode(), timeout=75, check=False)
response.write_bytes(run.stdout + run.stderr)
assert run.returncode == 0 and run.stdout, 'Inspect retained worker/process state'
data = json.loads(run.stdout)
(ROOT / 'powered-version-validation.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({key: value for key,value in data.items() if key != 'health'}, indent=2))
print('Final health:',data['health']['passed'])
