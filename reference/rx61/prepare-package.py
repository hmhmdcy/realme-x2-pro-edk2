from pathlib import Path
import xml.etree.ElementTree as ET,hashlib,json
root=Path('/mnt/e/edk2-samurai-out/rx61')
source=Path(json.loads((root/'source-preparation.json').read_text())['source_directory'])
wd=source/'src/windows/wdfserial'
inf='''; Experimental EUD COM package, offline candidate only.
; Based on Qualcomm qcwdfser.inf, commit 14b6fe1, BSD-3-Clause.
; Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
; SPDX-License-Identifier: BSD-3-Clause
; This new option is implemented by the candidate source; it is NOT an
; existing setting for the currently installed proprietary qcusbser.

[Version]
Signature="$WINDOWS NT$"
Class=Ports
ClassGuid={4D36E978-E325-11CE-BFC1-08002BE10318}
Provider=%Provider%
DriverVer=10/10/2026,1.0.0.1
CatalogFile=qceudexp.cat
PnpLockdown=1

[ControlFlags]
ExcludeFromSelect=*

[Manufacturer]
%Provider%=EudCom,NTamd64

[EudCom.NTamd64]
%Device%=EudInstall,USB\\VID_05C6&PID_9505

[SourceDisksNames]
1=%Disk%,,,

[SourceDisksFiles]
qcwdfserial.sys=1

[DestinationDirs]
EudCopy=13

[EudInstall.NT]
CopyFiles=EudCopy
AddReg=EudPortSettings

[EudCopy]
qcwdfserial.sys

[EudInstall.NT.Services]
AddService=qceudexp,0x00000002,EudService

[EudInstall.NT.Wdf]
KmdfService=qceudexp,EudKmdf

[EudKmdf]
KmdfLibraryVersion=$KMDFVERSION$

[EudService]
DisplayName=%Service%
ServiceType=1
StartType=3
ErrorControl=1
ServiceBinary=%13%\\qcwdfserial.sys

[EudPortSettings]
HKR,,PortSubClass,0x00000001,01
HKR,,EnumPropPages32,,"MsPorts.dll,SerialPortPropPageProvider"
HKR,,QCEudPreserveToggleOnOpen,0x00010001,1

[Strings]
Provider="Realme X2 Pro EUD experiment"
Device="EUD COM 9505 toggle preservation candidate"
Service="Experimental EUD COM serial"
Disk="EUD COM offline candidate package"
'''
path=wd/'qceudexp.inf'
assert not path.exists()
path.write_text(inf)
# Keep the production project unchanged. The offline candidate project
# builds the same nine C modules but packages only this exact EUD match.
old=wd/'qcwdfserial.vcxproj'
raw=old.read_text()
assert raw.count('<Inf Include="qcwdfmdm.inf" />')==1 and raw.count('<Inf Include="qcwdfser.inf" />')==1
new=raw.replace('    <Inf Include="qcwdfmdm.inf" />\n','').replace('<Inf Include="qcwdfser.inf" />','<Inf Include="qceudexp.inf" />')
new=new.replace('<ProjectName>qcwdfserial</ProjectName>','<ProjectName>qceudexp</ProjectName>\n    <TargetName>qcwdfserial</TargetName>')
out=wd/'qceudexp.vcxproj';out.write_text(new)
ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
oldxml=ET.fromstring(raw);newxml=ET.fromstring(new)
assert [i.attrib for i in oldxml.findall('.//m:ClCompile',ns) if 'Include' in i.attrib]==[i.attrib for i in newxml.findall('.//m:ClCompile',ns) if 'Include' in i.attrib]
assert [i.attrib['Include'] for i in newxml.findall('.//m:Inf',ns)]==['qceudexp.inf']
assert inf.count('USB\\VID_05C6&PID_9505')==1 and '9501' not in inf and 'HKLM' not in inf
assert 'QCDeviceZLPEnabled' not in inf
report=dict(status='OFFLINE PACKAGE INPUTS ONLY',exact_hardware_match='USB\\VID_05C6&PID_9505',service='qceudexp',source_tree=str(source),project=str(out),project_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),inf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),same_nine_c_modules=True,broad_upstream_infs_not_packaged=True,no_global_usb_flags=True,zlp_setting_unchanged=True,new_candidate_flag_defaults_to_one_in_candidate_package=True,installed=False,full_wdk_build=False,infverif=False,inf2cat=False,hardware_validated=False,notes=['WDK MSBuild must verify KMDF binding/INF requirements before any installation.','No signer or Windows boot setting changed. Secure Boot observed enabled; test-signed loading requires separate resolution.'])
(root/'package-inputs.json').write_text(json.dumps(report,indent=2)+'\n')
# Copy only reviewable authored inputs to root; complete vendor source remains external.
(root/'qceudexp.inf').write_bytes(path.read_bytes())
(root/'qceudexp.vcxproj').write_bytes(out.read_bytes())
print(json.dumps(report,indent=2))
