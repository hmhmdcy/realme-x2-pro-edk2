"""Snapshot the already authorized original build volume; no SDK/device."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent
OUT=HERE/'current-r7'
FILES=[
 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c','drivers/phy/phy-core.c',
 'drivers/usb/dwc3/dwc3-qcom.c','drivers/usb/dwc3/dwc3-qcom-legacy.c','drivers/usb/dwc3/drd.c',
 'drivers/usb/dwc3/gadget.c','drivers/usb/dwc3/core.c','drivers/usb/dwc3/core.h',
 'drivers/usb/misc/qcom_eud.c','drivers/tty/serial/eud.c','drivers/tty/serial/eud_earlycon.c',
 'drivers/usb/roles/class.c','drivers/usb/typec/class.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_pdphy.c',
 'include/linux/phy/phy.h','include/linux/usb/role.h','include/linux/usb/typec.h',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150-mtp.dts',
 'arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/pm8150b.dtsi']
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('storage461_current',HERE.parents[1]/'kernel461/storage.py')
 storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
 build=storage.mount.mounted_build()
 source=(build/'source').resolve();assert source.is_dir() and (source/'Makefile').is_file()
 assert str(source) in (build/'Makefile').read_text()
 OUT.mkdir();snap=OUT/'snapshots';snap.mkdir()
 records=[];missing=[]
 for name in FILES:
  path=source/name
  if not path.is_file():missing.append(name);continue
  raw=path.read_bytes();assert len(raw)<2*1024*1024
  target=snap/name.replace('/','--');target.write_bytes(raw)
  records.append(dict(relative_path=name,source_path=str(path),snapshot=target.name,bytes=len(raw),sha256=sha(raw)))
 for name in ['.config','Makefile','include/config/kernel.release','include/generated/utsrelease.h','include/generated/compile.h']:
  path=build/name
  if path.is_file():
   raw=path.read_bytes();target=snap/('build--'+name.replace('/','--'));target.write_bytes(raw)
   records.append(dict(relative_path='build/'+name,source_path=str(path),snapshot=target.name,bytes=len(raw),sha256=sha(raw)))
 config=(build/'.config').read_text()
 selected=[line for line in config.splitlines() if any(x in line for x in
   ['CONFIG_PHY_QCOM_SNPS','CONFIG_USB_DWC3','CONFIG_USB_QCOM_EUD','CONFIG_SERIAL_QCOM_EUD','CONFIG_TYPEC','CONFIG_USB_ROLE_SWITCH'])]
 q=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True)
 result=dict(schema='samurai-apsd-current-source-snapshot-v1',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  build=str(build),selected_source=str(source),source_git_head=q.stdout.decode().strip() if q.returncode==0 else None,
  config_selection=selected,files=records,missing=missing,phone_accessed=False,ssh_executed=False,sdk_invoked=False,
  shared_source_modified=False,build_invoked=False,root_authorized_original_storage_helper=True,
  source_linkage='selected build/source and generated output Makefile agree; runtime bytes require original Image provenance')
 (OUT/'source-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['build','selected_source','source_git_head','config_selection','missing']},indent=2))


if __name__=='__main__':main()
