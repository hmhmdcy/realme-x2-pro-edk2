from pathlib import Path
import subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'drivers/media/platform/qcom/camss'
for f in p.glob('camss-csiphy*.c'):
 s=f.read_text();rows=s.splitlines()
 for i,line in enumerate(rows):
  if any(x in line for x in ['clk.pos','lane_mask','clk_lane','clock_lane']):print(f.name,i+1,'\n'.join(rows[max(0,i-4):i+6]))
repo=Path('/home/cy122/x2pro-linux/hotdog-ref195');names=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only','47087509c4289c2580c54f5433e55366b2e00445'],text=True).splitlines()
for n in names:
 if n.endswith('.patch') and any(x in n for x in ['0102','0074','0075','0076','0114']):
  s=subprocess.check_output(['git','-C',str(repo),'show','47087509c4289c2580c54f5433e55366b2e00445:'+n],text=True)
  for i,line in enumerate(s.splitlines()):
   if 'clock-lanes' in line or 'data-lanes' in line:print(n,i+1,line)
