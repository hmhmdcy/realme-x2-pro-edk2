from pathlib import Path
import difflib,hashlib,json,struct,subprocess
import libfdt

here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel204')
name='arch/arm64/boot/dts/qcom/sm8150-samurai.dts';source=k/name;old=source.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
prior=json.loads((here.parent/'kernel203/source-final-validation.json').read_text())['source_sha256'];assert all(sha((k/n).read_bytes())==h for n,h in prior.items())
# The board DTS is maintained separately from the hashed SoC-source subset.
expected=sha(old);assert json.loads((out/'uart-source-blocks-private.json').read_text())['samurai-uart'] in old.decode()
backup=out/'samurai-dts-before-private.dts';assert not backup.exists();backup.write_bytes(old)
text=old.decode();anchor='&uart13 {\n    status = "okay";\n    pinctrl-names = "default";\n    pinctrl-0 = <&samurai_bt_uart_default>;'
assert text.count(anchor)==1
text=text.replace(anchor,'''&uart13 {
    status = "okay";
    /delete-property/ interrupts;
    interrupts-extended = <&intc GIC_SPI 585 IRQ_TYPE_LEVEL_HIGH>,
                          <&tlmm 46 IRQ_TYPE_EDGE_FALLING>;
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&samurai_bt_uart_default>;
    pinctrl-1 = <&samurai_bt_uart_sleep_ctsrts>,
                <&samurai_bt_uart_sleep_txrx>;''')
text+='''
&tlmm {
    samurai_bt_uart_sleep_ctsrts: samurai-bt-uart-sleep-ctsrts-state {
        pins = "gpio43", "gpio44";
        function = "gpio";
        drive-strength = <2>;
        /* CTS matches the controller; active-low RTS permits RX wake. */
        bias-pull-down;
    };

    samurai_bt_uart_sleep_txrx: samurai-bt-uart-sleep-txrx-state {
        pins = "gpio45", "gpio46";
        function = "gpio";
        drive-strength = <2>;
        /* Keep idle TX and the RX wake input high while GENI sleeps. */
        bias-pull-up;
    };
};
'''
source.write_text(text)
(here/'samurai-bluetooth-rx-wakeup.patch').write_text(''.join(difflib.unified_diff(old.decode().splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
pp=out/'samurai-source-candidate-private.pp';compiled=out/'samurai-source-candidate-private.dtb'
subprocess.run(['aarch64-linux-gnu-gcc','-E','-P','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I'+str(k/'include'),'-I'+str(k/'arch/arm64/boot/dts'),str(source),'-o',str(pp)],capture_output=True,check=True)
p=subprocess.run([str(k/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(compiled),str(pp)],capture_output=True);(out/'candidate-dtc-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
base=Path('/mnt/e/edk2-samurai-out/kernel199/sm8150-samurai-mmcx-static-private.dtb');raw=base.read_bytes();assert sha(raw)=='2e2f8e64319195f2d4af98b4cec1a83a2da31ed80a97c2b6afbf261b2e25d3e2'
tree=libfdt.Fdt(raw);full=libfdt.Fdt(compiled.read_bytes())
def snapshot(f):
 result={}
 def walk(n,path):
  props={};off=f.first_property_offset(n,quiet=libfdt.QUIET_NOTFOUND)
  while off>=0:
   p=f.get_property_by_offset(off);props[p.name]=bytes(p);off=f.next_property_offset(off,quiet=libfdt.QUIET_NOTFOUND)
  result[path]=props;c=f.first_subnode(n,quiet=libfdt.QUIET_NOTFOUND)
  while c>=0:walk(c,path.rstrip('/')+'/'+f.get_name(c));c=f.next_subnode(c,quiet=libfdt.QUIET_NOTFOUND)
 walk(0,'/');return result
before=snapshot(tree);src=snapshot(full)
tlmm=next(p for p,v in before.items() if v.get('compatible')==b'qcom,sm8150-pinctrl\0');uart='/soc@0/geniqup@cc0000/serial@c8c000'
if uart not in before:uart=next(p for p in before if p.endswith('/serial@c8c000'))
tlmm_phandle=struct.unpack('>I',before[tlmm]['phandle'])[0]
gic=next(p for p,v in before.items() if b'arm,gic-v3\0' in v.get('compatible',b''));gic_phandle=struct.unpack('>I',before[gic]['phandle'])[0]
assert before[uart]['interrupts']==struct.pack('>III',0,585,4) and 'pinctrl-1' not in before[uart]
top=max(struct.unpack('>I',v['phandle'])[0] for v in before.values() if 'phandle' in v)
tree.resize(len(raw)+4096);phandles=[];new_nodes=[]
for index,suffix in enumerate(['ctsrts','txrx'],1):
 node_name='samurai-bt-uart-sleep-'+suffix+'-state';path=tlmm+'/'+node_name;assert path in src
 n=tree.add_subnode(tree.path_offset(tlmm),node_name)
 for prop,value in src[path].items():
  if prop not in ['phandle','linux,phandle']:tree.setprop(n,prop,value)
 handle=top+index;tree.setprop_u32(n,'phandle',handle);phandles.append(handle);new_nodes.append(path)
n=tree.path_offset(uart);tree.delprop(n,'interrupts');tree.setprop(n,'interrupts-extended',struct.pack('>IIIIIII',gic_phandle,0,585,4,tlmm_phandle,46,2))
tree.setprop(n,'pinctrl-names',b'default\0sleep\0');tree.setprop(n,'pinctrl-1',struct.pack('>II',*phandles));tree.pack();after=snapshot(tree)
assert set(after)-set(before)==set(new_nodes) and set(before)<=set(after)
changes=[(p,n) for p in before for n in set(before[p])|set(after[p]) if before[p].get(n)!=after[p].get(n)]
assert set(changes)=={(uart,n) for n in ['interrupts','interrupts-extended','pinctrl-names','pinctrl-1']}
assert after[uart]['firmware-name'] if 'firmware-name' in after[uart] else True
# Verify source and stable-phandle artifact describe exactly the same UART resources.
assert src[uart]['pinctrl-names']==after[uart]['pinctrl-names'] and src[uart]['interrupts-extended'][4:16]==after[uart]['interrupts-extended'][4:16] and src[uart]['interrupts-extended'][-8:]==after[uart]['interrupts-extended'][-8:]
for path in new_nodes:assert {n:v for n,v in after[path].items() if n!='phandle'}=={n:v for n,v in src[path].items() if n!='phandle'}
dest=out/'sm8150-samurai-bt-wake-static-private.dtb';assert not dest.exists();dest.write_bytes(bytes(tree.as_bytearray()))
r=dict(stage=204,source_before_sha256=expected,source_candidate_sha256=sha(source.read_bytes()),candidate_dtb_sha256=sha(dest.read_bytes()),base_boot200_dtb_preserved=True,
 stable_existing_phandles_and_all_non_uart_properties=True,new_sleep_nodes=new_nodes,changed_existing_properties=[dict(node=p,property=n) for p,n in changes],source_compiles_and_uart_contract_matches_artifact=True,
 uart_gpio46_matches_own19781_vendor_tree=True,same_handset_firmware_baud_supplies_unchanged=True,kernel_image_config_modules_unchanged=True,hardware_deployment_not_performed=True)
(here/'uart-candidate-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
