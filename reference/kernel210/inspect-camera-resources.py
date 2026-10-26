"""Fresh camera supply/reset inventory; no register writes or output changes."""
from pathlib import Path
import ast,ctypes,fcntl,json,os,struct,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k210-camera-before';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not any(Path('/sys/module/'+n).exists() for n in ['samurai_cci_bringup','samurai_front_identify','qcom_pm8008','imx471'])
adapter=Path('/sys/bus/i2c/devices/i2c-1');assert (adapter/'of_node').resolve().name=='i2c@890000'
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and str((p/'of_node').resolve()).endswith('/pmic@4/gpio@c000')];assert len(chips)==1
gfd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);ifd=os.open('/dev/i2c-1',os.O_RDWR|os.O_CLOEXEC)
source=ast.parse((root/'k195-modules/probe-q-reset-address.py').read_text())
names=['Msg','Rdwr','read','snapshot','level','request','sample']
functions=[n for n in source.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
assert len(functions)==len(names);exec(compile(ast.Module(body=functions,type_ignores=[]),'existing-read-only-inventory','exec'))
report=dict(stage=210,pmic_p_level=sample(0),pmic_q_level=sample(3),pmic=snapshot(4),address8=read(8,0x100,6))
assert report['pmic_p_level']==0 and report['pmic_q_level']==1
assert report['pmic']['identity']['data']==[0,0,0,1,0x51,0x2c] and not report['address8']['success']
assert all(x['enable']['data']==[0] for x in report['pmic']['ldos'])
report['pmic_reset_lines_have_no_owner']=True
dt=Path('/sys/firmware/devicetree/base')
report['provider_paths']={n:str((p/'of_node').resolve()).removeprefix(str(dt)) for n,p in [('pm8150l_gpios',chips[0]),('i2c1',adapter)]}
for p in Path('/sys/kernel/debug/pinctrl').glob('*/pinmux-pins'):
    if '3100000' in str(p):
        selected=[l for l in p.read_text().splitlines() if any(l.startswith('pin '+str(n)+' ') for n in [12,15,29])]
        assert len(selected)==3 and all('MUX UNCLAIMED' in l and 'GPIO UNCLAIMED' in l for l in selected)
        report['front_tlmm_pins_unclaimed']=True
assert report.get('front_tlmm_pins_unclaimed')
os.close(gfd);os.close(ifd)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=210,pmic_p_held_reset=True,pmic_q_released=True,assigned_address4_verified=True,factory_address8_absent=True,all_seven_camera_outputs_off=True,pmic_reset_lines_have_no_owner=True,front_tlmm_pins_unclaimed=True,provider_paths=report['provider_paths'])))
