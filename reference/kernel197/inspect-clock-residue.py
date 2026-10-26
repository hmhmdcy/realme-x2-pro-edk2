from pathlib import Path
import tarfile,json,host,re
out=host.PRIVATE;host.ssh('python3 -',input=b"from pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k197-baseline/boot-id-private.txt').read_bytes()\nPath('/var/lib/samurai/k197-clock-final').mkdir(mode=0o700)\nPath('/var/lib/samurai/k197-clock-final/clocks-private.txt').write_bytes(Path('/sys/kernel/debug/clk/clk_summary').read_bytes())\n",timeout=20);host.download('/var/lib/samurai/k197-clock-final/clocks-private.txt',out/'final-clocks-private.txt')
def read(s):
 rows={}
 for l in s.splitlines():
  w=l.split()
  if w and w[0] in ['cam_cc_core_ahb_clk','cam_cc_slow_ahb_clk_src','cam_cc_cpas_ahb_clk','cam_cc_cci_1_clk','gcc_camera_ahb_clk','cam_cc_mclk2_clk']:rows[w[0]]=w[1:9]
 return rows
with tarfile.open(out.parent/'kernel196/native-evidence-private.tar.gz') as tar:old=read(tar.extractfile('k196-final-health/clocks-private.txt').read().decode())
current=read((out/'final-clocks-private.txt').read_text());r=dict(stage=197,prior196=old,current197=current,entire_clock_reference_counts_restored=old==current);(out/'clock-residue-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
