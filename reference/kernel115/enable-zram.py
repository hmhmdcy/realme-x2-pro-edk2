from pathlib import Path
import subprocess,json
out=Path('/var/lib/samurai/k115-zram')
assert not out.exists()
out.mkdir(mode=0o700)
assert subprocess.check_output(['uname','-v']).startswith(b'#115 ')
assert 'lzo-rle' in Path('/sys/block/zram0/comp_algorithm').read_text()
info=Path('/etc/deviceinfo')
original=info.read_text()
out.joinpath('deviceinfo-before-private').write_text(original)
assert 'deviceinfo_zram_swap_algo=' not in original
info.write_text(original+'\n# Kernel115 supports lzo-rle; zstd is not enabled in this build.\ndeviceinfo_zram_swap_algo="lzo-rle"\n')
subprocess.run(['rc-service','postmarketos-zram-swap','start'],check=True,stdout=out.joinpath('start.txt').open('w'),stderr=subprocess.STDOUT)
subprocess.run(['rc-service','postmarketos-zram-swap','status'],check=True,stdout=out.joinpath('status.txt').open('w'),stderr=subprocess.STDOUT)
swaps=Path('/proc/swaps').read_text();out.joinpath('swaps.txt').write_text(swaps)
assert '/dev/zram0' in swaps
algorithm=Path('/sys/block/zram0/comp_algorithm').read_text().strip()
assert '[lzo-rle]' in algorithm
report=dict(kernel_build=115,zram_swap_active=True,algorithm='lzo-rle',disksize_bytes=int(Path('/sys/block/zram0/disksize').read_text()),priority=300,forced_memory_pressure_not_run=True,goal_complete=False)
out.joinpath('validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
