"""Recheck local OEM module XML provenance without publishing vendor payloads."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
rows=[]
for vendor in ['sunny','qtech']:
 root=Path('/home/cy122/x2pro-linux/parser-k235-imx319-'+vendor+'/xml/Scenario.0/XML/None')
 files=[]
 for name in ['cameraModuleData.xml','sensorDriverData.xml']:
  p=root/name;b=p.read_bytes();tree=ET.fromstring(b)
  fields=[e for e in tree.iter() if any(k in e.tag.lower() for k in ['blacklevel','black_level','pedestal','chromatix'])]
  files.append(dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),named_black_or_chromatix_elements=len(fields)))
 rows.append(dict(vendor_reference=vendor,files=files))
d=dict(stage=298,sensor='imx319',local_oem_module_xml_rechecked=True,mode_evidence='../kernel235/vendor-mode-validation.json',
 references=rows,matched_runtime_mode=[1632,1224],sensor_identity_does_not_prove_module_vendor=True,
 individual_module_vendor_or_eeprom_calibration_not_newly_verified=True,
 no_board_or_sensor_mode_changes=True,no_otp_or_eeprom_writes=True,
 black_level_not_obtained_from_these_module_xmls=True,no_other_handset_calibration_copied=True,
 black_level_evidence='raw-analysis-validation.json (scene fit only; dark calibration pending)')
(HERE/'module-evidence-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
