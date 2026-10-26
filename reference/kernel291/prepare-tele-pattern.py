"""Reuse the standard path for the other ordinary Bayer sensor, with native controls."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
ROOT=Path(__file__).resolve().parent
proofs={}
for kind in ['raw','pix']:
 s=(ROOT/f'samurai-pattern-{kind}.c').read_text().replace('imx319','s5k3m5').replace('SRGGB10','SGRBG10')
 for a,b in [('1632','2104'),('1224','1560'),('512','64'),('500','150'),('3000','1200')]:s=re.sub(r'\b'+a+r'\b',b,s)
 if kind=='raw':
  for a,b in [('2040','2630'),('2496960','4102800'),('2247264','3692520'),('408','526'),('1216','1552'),('204','263')]:s=re.sub(r'\b'+a+r'\b',b,s)
  a='(double)sums[0]/counts[0],(double)sums[1]/counts[1],(double)sums[2]/counts[2],(double)sums[3]/counts[3]'
  b='(double)sums[1]/counts[1],(double)sums[0]/counts[0],(double)sums[3]/counts[3],(double)sums[2]/counts[2]'
  assert a in s;s=s.replace(a,b)
 source=ROOT/f'samurai-tele-pattern-{kind}.c';assert not source.exists();source.write_text(s)
 binary=host.PRIVATE/f'tele-pattern-{kind}-aarch64-private';assert not binary.exists()
 q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
 (host.PRIVATE/f'tele-pattern-{kind}-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
 assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-tele-pattern'],capture_output=True,timeout=10).returncode==3
 proofs[kind]=dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),qemu_self_test_pass=True,wrong_kernel_guard_passed=True)
 worker=(ROOT/f'native-pattern-{kind}.py').read_text().replace(f'k291-pattern-{kind}-r1',f'k291-tele-pattern-{kind}-r1').replace(f'k291-tools/pattern-{kind}',f'k291-tools/tele-pattern-{kind}').replace("physical_sensor='imx319'","physical_sensor='s5k3m5'")
 if kind=='raw':worker=worker.replace('len(b)==2048*1224','len(b)==2640*1560')
 (ROOT/f'native-tele-pattern-{kind}.py').write_text(worker)
 launcher=(ROOT/f'launch-pattern-{kind}.py').read_text().replace('pattern-tool-validation','tele-pattern-tool-validation')
 launcher=launcher.replace(f'pattern-{kind}',f'tele-pattern-{kind}')
 (ROOT/f'launch-tele-pattern-{kind}.py').write_text(launcher)
 poll=(ROOT/f'poll-pattern-{kind}.py').read_text().replace(f'pattern-{kind}',f'tele-pattern-{kind}')
 (ROOT/f'poll-tele-pattern-{kind}.py').write_text(poll)
(ROOT/'tele-pattern-tool-validation.json').write_text(json.dumps(dict(stage=291,tools=proofs,sensor_pattern=2,csid_pattern=0,sensor='s5k3m5',bayer='GRBG',native_gain_code=64,exposure_codes=[150,1200,150]),indent=2)+'\n')
print(json.dumps(proofs,indent=2))
