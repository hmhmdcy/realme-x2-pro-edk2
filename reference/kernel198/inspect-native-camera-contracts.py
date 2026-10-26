from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');o=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
for p,marker,count in [(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi','camcc: clock-controller@ad00000',950),(k/'drivers/media/platform/qcom/camss/camss-vfe.c','static int vfe_set_clock_rates',6000),(o/'arch/arm64/boot/dts/qcom/sm8150-camera.dtsi','cam_csid0:',3000),(o/'arch/arm64/boot/dts/qcom/sm8150-camera.dtsi','cam_ife0:',3000),(o/'drivers/clk/qcom/camcc-sm8150.c','static struct clk_rcg2 cam_cc_ife_0_clk_src',1300)]:
 s=p.read_text();i=s.find(marker);print(p.name,marker);print(s[i:i+count] if i>=0 else 'NOT FOUND')
repo=Path('/home/cy122/x2pro-linux/hotdog-ref195');import subprocess
names=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only','47087509c4289c2580c54f5433e55366b2e00445'],text=True).splitlines()
for n in names:
 if '/linux-oneplus-hotdog-mainline616/' in n and n.endswith('.patch') and any(x in n.lower() for x in ['opp','power','voltage','0068','0060']):
  print(n)
  if '0068' in n or '0060' in n:print(subprocess.check_output(['git','-C',str(repo),'show','47087509c4289c2580c54f5433e55366b2e00445:'+n],text=True)[:6000])
