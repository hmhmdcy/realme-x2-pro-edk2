from pathlib import Path
import json,struct,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel320')
expected=json.loads((P/'stock-unit-lsc-private.json').read_text())['channels']
for arch,compiler,runner in [('host','gcc',[]),('aarch64','aarch64-linux-gnu-gcc',['qemu-aarch64'])]:
 binary=P/('decode-stock-'+arch)
 q=subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-static',str(HERE/'decode-stock-lsc.c'),'-o',str(binary)],capture_output=True)
 (P/('build-'+arch+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 subprocess.run([*runner,str(binary),'--self-test'],check=True)
 for sample in [1,2]:
  q=subprocess.run([*runner,str(binary),str(P.parent/f'kernel299/imx319-eeprom-read{sample}-private.bin')],capture_output=True,check=True)
  assert list(struct.unpack('<884H',q.stdout))==[v for channel in expected for v in channel]
  (P/f'decoded-{arch}-read{sample}-private.bin').write_bytes(q.stdout)
p=HERE/'stock-lsc-layout-validation.json';d=json.loads(p.read_text());d.update(independent_sequential_c_decoder=True,host_and_aarch64_werror_build=True,both_retained_reads_match=True,asymmetric_group_boundary_test_passed=True)
p.write_text(json.dumps(d,indent=2)+'\n');print('Both architectures and both retained reads match the corrected target-specific decoder.')
