from pathlib import Path
import hashlib,json,re,subprocess
import host

here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=host.PRIVATE
for n in ['summary.json','live-private.dtb','uart-pm-private.json','interrupts-private.txt','wakeup-sources-private.txt','bluetooth-init-private.txt','dmesg-private.txt','pinctrl-private.txt']:
 host.download('/var/lib/samurai/k204-baseline-r2/'+n,private/('baseline-'+n))
subprocess.run([str(k/'scripts/dtc/dtc'),'-I','dtb','-O','dts','-o',str(private/'live-private.dts'),str(private/'baseline-live-private.dtb')],capture_output=True,check=True)
def block(text,marker):
 start=text.index(marker);first=text.index('{',start);level=1;end=first+1
 while level:
  if text[end]=='{':level+=1
  if text[end]=='}':level-=1
  end+=1
 return text[start:end+1]
sources={}
for name,path,marker in [
 ('samurai-uart',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','&uart13 {'),
 ('samurai-default-pins',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','samurai_bt_uart_default:'),
 ('x3-uart',Path('/mnt/e/edk2-samurai-out/kernel203/related-device-sources/realme-x3-dts-pinned.txt'),'&uart13 {'),
 ('x3-sleep-pins',Path('/mnt/e/edk2-samurai-out/kernel203/related-device-sources/realme-x3-dts-pinned.txt'),'qup_uart13_sleep:'),
 ('live-uart',private/'live-private.dts','serial@c8c000 {')]:
 data=path.read_text();sources[name]=block(data,marker)
(private/'uart-source-blocks-private.json').write_text(json.dumps(sources,indent=2)+'\n')
oem=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts')
matches=[]
for p in sorted(oem.rglob('*.dtsi')):
 if not any(t in p.name for t in ['19781','sm8150','bluetooth']):continue
 data=p.read_text(errors='replace');lines=data.splitlines()
 for i,l in enumerate(lines):
  if re.search(r'blsp_uart|qupv3_se13|qup_uart13|rx-gpio|tx-gpio|cts-gpio|rts-gpio',l):
   matches.append(dict(path=str(p.relative_to(oem)),line=i+1,context='\n'.join(lines[max(0,i-3):i+9])))
(private/'oem-uart-matches-private.json').write_text(json.dumps(matches,indent=2)+'\n')
details=json.loads((private/'baseline-uart-pm-private.json').read_text())
r=dict(stage=204,same_boot203=True,live_uart_has_only_primary_interrupt='interrupts = ' in sources['live-uart'] and 'interrupts-extended' not in sources['live-uart'],
 live_uart_sleep_state_absent='pinctrl-1' not in sources['live-uart'],source_x3_explicit_rx_gpio46_wake='tlmm 46 IRQ_TYPE_EDGE_FALLING' in sources['x3-uart'],source_x3_sleep_state_present='pinctrl-1' in sources['x3-uart'],
 native_uart_power_wakeup_attribute_present=any('power/wakeup' in v for v in details.values()),oem_uart_matching_contexts=len(matches),modification_performed=False)
(here/'uart-current-validation.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r));print(json.dumps(sources,indent=2));print(json.dumps(details,indent=2));print(json.dumps(matches[:12],indent=2))
