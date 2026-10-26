"""Offline bounded snapshots of actual Type-C/TCPM sources, no SDK or Git."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('tcpm_owner_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
names=['drivers/usb/typec/tcpm/tcpm.c','include/linux/usb/tcpm.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_pdphy.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_pdphy.c',
 'drivers/usb/typec/tcpm/Kconfig','drivers/usb/typec/tcpm/Makefile',
 'drivers/usb/typec/tcpm/qcom/Makefile',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_pdphy_stub.c']
target=HERE/'sources';target.mkdir(exist_ok=True)
records=[]
for name in names:
 p=source/name;raw=p.read_bytes();dest=target/name.replace('/','--')
 assert len(raw)<600000
 dest.write_bytes(raw);records.append(dict(path=name,bytes=len(raw),sha256=sha(raw),snapshot=dest.name))
r=dict(source=str(source),build=str(build),files=records,source_or_config_modified=False,
       SDK_invoked=False,Git_invoked=False,device_accessed=False)
(HERE/'source-manifest.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(files=len(records),total_bytes=sum(x['bytes'] for x in records))))
