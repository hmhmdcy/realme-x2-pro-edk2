from pathlib import Path
ref=Path(__file__).resolve().parent;old=ref.parent/'kernel198'
for name in ['stage-live-tools.py','prepare-physical-live-native.py','build-live-overlay.py']:
 s=(old/name).read_text().replace('k198','k199').replace('stage=198','stage=199');(ref/name).write_text(s)
s=(old/'front-probe-overlay.dtso').read_text();s=s.replace('#include <dt-bindings/media/video-interfaces.h>','#include <dt-bindings/media/video-interfaces.h>\n#include <dt-bindings/power/qcom,rpmhpd.h>');position=s.rfind('\n};');assert position>0
s=s[:position]+'''
	fragment@5 {
		target-path = "/soc@0/camss@acb3000";
		__overlay__ {
			power-domains = <CAMCC_PHANDLE IFE_0_GDSC>,
					<CAMCC_PHANDLE IFE_1_GDSC>,
					<CAMCC_PHANDLE TITAN_TOP_GDSC>,
					<RPMHPD_PHANDLE SM8150_MMCX>;
			power-domain-names = "ife0", "ife1", "top", "mmcx";
		};
	};
'''+s[position:];(ref/'front-probe-overlay.dtso').write_text(s)
p=ref/'build-live-overlay.py';s=p.read_text()
s=s.replace("values=dict(PMIC_GPIO_PHANDLE", "values=dict(RPMHPD_PHANDLE=data['mmcx']['provider_phandle'],PMIC_GPIO_PHANDLE");(ref/'build-live-overlay.py').write_text(s)
s=(old/'capture-front-stock-low.py').read_text().replace('k198','k199').replace('stage=198','stage=199').replace('stock-low-module-build-validation.json','mmcx-module-build-validation.json').replace('qcom-camss-stock-low.ko','qcom-camss-mmcx.ko').replace(",'clock_trace=1'",'');(ref/'capture-front-mmcx.py').write_text(s)
# Record the live power-domain specifier without assuming platform indices.
p=ref/'inspect-live-resources.py';s=p.read_text()
if "r['mmcx']" not in s:
 s=s.replace('import json,subprocess','import json,struct,subprocess');needle="Path('/var/lib/samurai/k199-baseline/resources.json').write_text";i=s.index(needle);s=s[:i]+"pd=struct.unpack('>II',(root/'soc@0/clock-controller@ad00000/power-domains').read_bytes());r['mmcx']=dict(provider_phandle=pd[0],index=pd[1]);r['original_camss_domains']=list(struct.unpack('>6I',(root/'soc@0/camss@acb3000/power-domains').read_bytes()))\n"+s[i:];p.write_text(s)
print('Prepared live four-domain overlay and integrated runtime-power candidate session')
