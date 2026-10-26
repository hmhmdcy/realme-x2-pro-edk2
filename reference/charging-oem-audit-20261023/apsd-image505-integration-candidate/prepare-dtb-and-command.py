"""Extend the actual deployed IRQ DTB and preserve the current instant mode."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01/samurai-usb-input-irq-native-private.dtb')
OUT=BASE.parents[1]/'apsd-image505-dtb-private-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE)=='13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f' and not OUT.exists()
parser=REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate/inspect-dtb.py';assert sha(parser)=='5280e01c3c662408d6dc60b65317208e76ed765dc86f64f1ac8698146ff9e5fd'
spec=importlib.util.spec_from_file_location('actual_IRQ_native_DTB_decoder_505',parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
before=m.decode(BASE.read_bytes());nodes=before['nodes'];expected={name:dict(props) for name,props in nodes.items()}
string=lambda value:value.encode()+b'\0';cell=lambda value:struct.pack('>I',value)
DWC='/soc@0/usb@a6f8800/usb@a600000';TC='/soc@0/spmi@c440000/pmic@2/typec@1500';PHY='/soc@0/phy@88e2000';ROUTE='/soc@0/eud-off-route'
assert nodes[DWC]['compatible']==string('snps,dwc3') and nodes[TC]['status']==string('disabled') and ROUTE not in nodes
assert not any(name.startswith(TC+'/') for name in nodes) and nodes[TC]['reg']==struct.pack('>II',0x1500,0x1700)
eud=[name for name,props in nodes.items() if props.get('compatible')==string('qcom,sm8150-eud-com')];assert len(eud)==1;EUD=eud[0]
assert all(props.get('status')==string('disabled') for props in nodes.values() if b'eud' in props.get('compatible',b''))
supply=nodes[PHY]['vdda33-supply'];assert len(supply)==4
assert sum(props.get('phandle')==supply for props in nodes.values())==1
CURRENT='console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused bq27xxx_battery.samurai_instant_current=1'
assert nodes['/chosen']['bootargs'] in [string(CURRENT),string(CURRENT.rsplit(' bq27xxx_',1)[0])]
NEW=CURRENT+' qcom_pmic_tcpm.samurai_5v_only=1'
OUT.mkdir();target=OUT/'samurai-apsd505-native-private.dtb';shutil.copyfile(BASE,target)
commands=[]
def run(argv):
 result=subprocess.run(argv,capture_output=True,text=True);commands.append(dict(argv=argv,returncode=result.returncode,stderr=result.stderr));assert result.returncode==0 and not result.stderr,(argv,result.stderr)
def put(path,key,raw):
 if not raw:args=['fdtput',str(target),path,key]
 elif raw.endswith(b'\0') and all(32<=value<127 for value in raw[:-1]):args=['fdtput','-t','s',str(target),path,key,raw[:-1].decode()]
 else:
  assert len(raw)%4==0;args=['fdtput','-t','x',str(target),path,key,*[format(value,'x') for value in struct.unpack('>'+str(len(raw)//4)+'I',raw)]]
 run(args);expected[path][key]=raw
maximum=max([struct.unpack('>I',props['phandle'])[0] for props in nodes.values() if 'phandle' in props]);assert maximum<0xffffff00
assigned={}
for path in [DWC,EUD,TC]:
 if 'phandle' in nodes[path]:assigned[path]=struct.unpack('>I',nodes[path]['phandle'])[0]
 else:maximum+=1;assigned[path]=maximum;put(path,'phandle',cell(maximum))
run(['fdtput','-c',str(target),ROUTE]);expected[ROUTE]={};maximum+=1;assigned[ROUTE]=maximum
for key,raw in {'compatible':string('realme,rmx1931-eud-off-route'),'status':string('okay'),'phandle':cell(maximum),
  'realme,eud-hardware':cell(assigned[EUD]),'realme,usb-controller':cell(assigned[DWC])}.items():put(ROUTE,key,raw)
for key,raw in {'samurai,apsd-owner':b'','samurai,apsd-pd5v-bridge':b'','samurai,apsd-typec':cell(assigned[TC]),'samurai,apsd-eud-route':cell(assigned[ROUTE])}.items():put(DWC,key,raw)
for key,raw in {'status':string('okay'),'realme,pd5v-only':b'','vdd-pdphy-supply':supply}.items():put(TC,key,raw)
put('/chosen','bootargs',string(NEW))
after=m.decode(target.read_bytes());assert after['nodes']==expected and after['reserves']==before['reserves']
assert struct.unpack_from('>10I',target.read_bytes())[7]==struct.unpack_from('>10I',BASE.read_bytes())[7]
assert sha(BASE)=='13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
changes={name:sorted(key for key in set(nodes.get(name,{}))|set(props) if nodes.get(name,{}).get(key)!=props.get(key)) for name,props in expected.items() if nodes.get(name)!=props}
old=(REF/'charging-oem-audit-20261023/eud-route-handoff-candidate/PlatformBm.c.candidate').read_text()
literal='  L"'+CURRENT.rsplit(' bq27xxx_',1)[0]+'";';replacement='  L"'+NEW+'";';assert old.count(literal)==1
new=old.replace(literal,replacement);assert new.replace(replacement,literal)==old
bds=HERE/'PlatformBm.c.candidate';assert not bds.exists();bds.write_text(new)
result=dict(passed=True,base_DTB=dict(path=str(BASE),sha256=sha(BASE)),candidate_DTB=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size),
 actual_prior_IRQ_native_DTB_reused=True,controller=DWC,disabled_EUD_hardware=EUD,typec=TC,route=ROUTE,changed_properties=changes,
 exact_all_other_raw_properties_and_reserves_preserved=True,TypeC_supply_matches_actual_PHY_vdda33=True,
 current_cmdline_observed_from_actual_phone=CURRENT,candidate_cmdline=NEW,instant_current_opt_in_preserved=True,
 BDS_only_global_cmdline_changed_from_checked_handoff=True,BDS_source_sha256=sha(bds),commands=commands,compiled_kernel_or_firmware=False,phone_written=False,installed=False)
with (HERE/'dtb-and-command-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,DTB=result['candidate_DTB'],changes=changes,preserved_instant_current=True)))
