from pathlib import Path
import hashlib,json,os,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');bin=Path('/home/cy122/x2pro-linux/schema-k194/venv/bin');schema=k/'Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml';processed=out/'processed-camss-private.json';commands=[]
def command(name,args,quiet=True):
 p=subprocess.run(args,capture_output=True,timeout=90);(out/(name+'-private.log')).write_bytes(p.stdout+p.stderr);commands.append(dict(name=name,returncode=p.returncode,diagnostic_bytes=len(p.stdout+p.stderr)));assert p.returncode==0,(name,(p.stdout+p.stderr).decode()[:3000]);
 if quiet:assert not p.stdout+p.stderr,(name,(p.stdout+p.stderr).decode()[:3000])
command('mmcx-doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)])
command('mmcx-compile-schema',[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/media/video-interfaces.yaml')])
pp=out/'mmcx-board-private.pp';dtb=out/'mmcx-board-private.dtb';command('mmcx-board-cpp',['aarch64-linux-gnu-gcc','-E','-P','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I'+str(k/'include'),str(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)])
command('mmcx-board-dtc',[str(k/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(dtb),str(pp)],False)
script=r'''
from pathlib import Path
import hashlib,json,struct,sys
import libfdt,dtschema
out=Path(sys.argv[1]);raw=(out/'mmcx-board-private.dtb').read_bytes();f=libfdt.Fdt(raw);node=f.path_offset('/soc@0/camss@acb3000');names=bytes(f.getprop(node,'power-domain-names')).rstrip(b'\0').decode().split('\0');cells=struct.unpack('>8I',bytes(f.getprop(node,'power-domains')));assert names==['ife0','ife1','top','mmcx'];provider=f.node_offset_by_phandle(cells[-2]);assert 'rpmhpd' in bytes(f.getprop(provider,'compatible')).decode() and cells[-1]==int(sys.argv[2])
v=dtschema.DTValidator([str(out/'processed-camss-private.json')])
def errors(data):
 decoded=v.decode_dtb(data)[0];n=decoded['soc@0']['camss@acb3000'];n['$nodename']=['camss@acb3000'];return list(v.iter_errors(n,filter=['qcom,sm8150-camss']))
assert not errors(raw);results=[]
for name,changes in [('old-three-domains',{'power-domains':bytes(f.getprop(node,'power-domains'))[:-8],'power-domain-names':b'ife0\0ife1\0top\0'}),('missing-mmcx-domain',{'power-domains':bytes(f.getprop(node,'power-domains'))[:-8]}),('wrong-domain-name',{'power-domain-names':b'ife0\0ife1\0top\0bad\0'})]:
 broken=libfdt.Fdt(raw);broken.resize(len(raw)+1024);n=broken.path_offset('/soc@0/camss@acb3000')
 for prop,value in changes.items():broken.setprop(n,prop,value)
 e=errors(bytes(broken.as_bytearray()));assert e,name;results.append(dict(name=name,strict_errors=len(e)))
r=dict(stage=199,actual_candidate_board_node_passed=True,four_named_domains=True,mmcx_provider_and_index_checked=True,negative_controls=results,whole_board_not_claimed=True,dtb_sha256=hashlib.sha256(raw).hexdigest());(out/'mmcx-schema-result-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
expected=subprocess.check_output(['aarch64-linux-gnu-gcc','-E','-P','-x','c','-I'+str(k/'include'),'-'],input=b'#include <dt-bindings/power/qcom,rpmhpd.h>\nSM8150_MMCX\n').decode().strip();assert expected.isdigit();p=out/'validate-mmcx-node-private.py';p.write_text(script);command('mmcx-strict-node',[str(bin/'python'),str(p),str(out),expected],False);result=json.loads((out/'mmcx-schema-result-private.json').read_text());result['commands']=commands;(ref/'mmcx-schema-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

