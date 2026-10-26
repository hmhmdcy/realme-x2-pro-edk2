"""Pin manufacturer GW1 pattern source; no API credentials or device writes."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE/'sources';P.mkdir(exist_ok=True)
repo=P/'realme6-kernel';url='https://github.com/realme-kernel-opensource/realme6-kernel-source'
if not repo.exists():subprocess.run(['git','clone','--filter=blob:none','--no-checkout','--depth=1',url+'.git',str(repo)],check=True)
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()
path='drivers/misc/mediatek/imgsensor/src/common/v1_1/s5kgw1_mipi_raw/s5kgw1mipiraw_Sensor.c'
raw=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+path],timeout=40);(P/'s5kgw1mipiraw_Sensor.c').write_bytes(raw)
text=raw.decode();at=text.index('set_test_pattern_mode');end=text.index('static kal_uint32 get_sensor_temperature',at);function=text[at:end]
assert 'write_cmos_sensor(0x0600, 0x0002)' in function and 'write_cmos_sensor(0x0600, 0x0000)' in function
report=dict(stage=324,repository=url,commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest(),
 function='set_test_pattern_mode',function_line=text[:at].count('\n')+1,
 url=url+'/blob/'+commit+'/'+path,register='0x0600',register_bits=16,enabled_color_bars=2,disabled=0,
 manufacturer_source_for_same_sensor_other_board=True,current_handset_enable_not_yet_tested=True,
 factory_handset_description_declares_off_only=True,phone_changed=False)
(HERE/'gw1-pattern-primary-source.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
