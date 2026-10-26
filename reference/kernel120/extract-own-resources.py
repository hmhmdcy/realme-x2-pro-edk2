from pathlib import Path
import re,json,hashlib
down=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source')
out=Path('/mnt/e/edk2-samurai-out/kernel120');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def clean(text):return re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
def nodes(text,pattern):
    for m in re.finditer(pattern+r'\s*\{',text):
        start=m.end();level=1;i=start
        while level and i<len(text):
            level+=(text[i]=='{')-(text[i]=='}');i+=1
        assert level==0
        yield m.group(0),text[start:i-1]
def props(body):
    return {m[1]:re.sub(r'\s+',' ',m[2]).strip() for m in re.finditer(r'([\w,\-]+)\s*=\s*([^;]*);',body)}
camera=down/'arch/arm64/boot/dts/19781/sm8150-camera.dtsi'
sensor=down/'arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi'
records=[]
for name,body in nodes(clean(camera.read_text()),r'cam_cci[01]:\s*qcom,cci@[a-f0-9]+'):
    p=props(body);records.append(dict(node=name,properties={k:v for k,v in p.items() if k in ['reg','reg-names','interrupts','interrupt-names','clock-names','pinctrl-0','pinctrl-1','qcom,cci-clk-src','qcom,hw-thigh','qcom,hw-tlow','qcom,hw-trdhld']}))
assert len(records)==2
slots=[]
for name,body in nodes(clean(sensor.read_text()),r'qcom,cam-sensor@[0-9]+'):
    p=props(body);slots.append(dict(node=name,properties={k:v for k,v in p.items() if k.startswith('cam_v') or k in ['cell-index','csiphy-sd-index','cci-device','cci-master','gpios','gpio-reset','gpio-custom1','clock-rates','clocks','rgltr-min-voltage','rgltr-max-voltage','regulator-names']}))
pinpaths=[down/'arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi']
pins=[]
for p in pinpaths:
    text=clean(p.read_text())
    for name,body in nodes(text,r'cci[0-3]_(?:active|suspend):\s*cci[0-3]_(?:active|suspend)'):
        if 'cci_i2c' in body:
            pr=props(body);pins.append(dict(file=p.name,node=name,properties={k:v for k,v in pr.items() if k in ['pins','function','drive-strength']}))
report=dict(downstream_cci=records,active_source_slots=slots,cci_pinctrl=pins,source_hashes=[dict(file=p.name,sha256=sha(p)) for p in [camera,sensor]+pinpaths],sources_only_not_physical_sensor_identification=True,stock_bins_still_not_decoded=True)
for folder in [out,ref]:(folder/'own-camera-resource-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
