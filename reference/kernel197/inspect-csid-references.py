from pathlib import Path
import subprocess
repo=Path('/home/cy122/x2pro-linux/hotdog-ref195');rev='47087509c4289c2580c54f5433e55366b2e00445';names=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',rev],text=True).splitlines()
for n in names:
 if '/linux-oneplus-hotdog-mainline616/' in n and n.endswith('.patch') and any(x in n.lower() for x in ['csid','clock','reset','cphy','camss','vfe','camera']):print(n)
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');s=(k/'drivers/media/platform/qcom/camss/camss-vfe.c').read_text();i=s.index('int vfe_get(struct');print(s[i:i+4500])
for p in (k/'drivers/media/platform/qcom/camss').glob('*.c'):
 s=p.read_text()
 for m in ['vfe_pm_domain_on(','vfe_pm_domain_off(']:
  for needle in ['static int '+m,'int '+m,'static void '+m,'void '+m]:
   i=s.find(needle)
   if i>=0:print(p.name,s[i:i+1100]);break
for n in ['arch/arm64/boot/dts/qcom/sm8150.dtsi','Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml']:
 p=k/n
 if p.exists():
  rows=p.read_text().splitlines()
  for i,l in enumerate(rows):
   if 'camss:' in l or 'csid0' in l and '"' in l:print(n,i+1,'\n'.join(rows[max(0,i-4):i+15]))
