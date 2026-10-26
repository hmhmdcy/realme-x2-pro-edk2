"""Read existing storage only; refuse every mount/SDK/device operation."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STORAGE=HERE.parents[1]/'kernel461/storage.py'
MOUNT=Path('/mnt/samurai-full282')
REQUIRED=[
 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c',
 'drivers/usb/dwc3/dwc3-qcom.c','drivers/usb/dwc3/dwc3-qcom-legacy.c','drivers/usb/dwc3/dwc3-qcom-of.c',
 'drivers/usb/dwc3/drd.c','drivers/usb/dwc3/gadget.c','drivers/usb/dwc3/core.c',
 'drivers/usb/misc/qcom_eud.c','drivers/usb/roles/class.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_pdphy.c',
 'include/linux/phy/phy.h','include/linux/usb/role.h','include/linux/usb/typec.h',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150-mtp.dts',
 'arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/pm8150b.dtsi']
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('storage461_inspect_only',STORAGE)
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    mount_module=storage.mount
    lines=Path('/proc/self/mountinfo').read_text().splitlines()
    exact=[line for line in lines if len(line.split())>4 and line.split()[4]==str(MOUNT)]
    result=dict(schema='samurai-apsd-existing-storage-inspection-v1',
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        storage_entry=str(STORAGE),storage_entry_sha256=sha(STORAGE.read_bytes()),
        resolved_mount_module=str(mount_module.__file__),
        resolved_mount_module_sha256=sha(Path(mount_module.__file__).read_bytes()),
        mounted_build_function=inspect.getsource(mount_module.mounted_build),
        exact_existing_mountinfo=exact,existing_mount_available=bool(exact),
        mounted_build_called=False,mount_command_attempted=False,mount_command_executed=False,
        sdk_invoked=False,phone_accessed=False,ssh_executed=False,
        requested_source_paths=REQUIRED,snapshots=[],missing=[])
    if not exact:
        result.update(status='existing_mount_missing',actual_r7_source_pinned=False,
            reason='mounted_build would enter its remount branch; not called under no-remount instruction',
            expected_build_config_exists=(MOUNT/'build/.config').is_file(),
            previously_named_source354_exists=(MOUNT/'source354').is_dir(),
            missing=['authoritative selected build/source root','actual R7 generic PHY/glue/EUD bytes',
                     'actual compiled DTS role/connector/PD owner wiring'])
    else:
        real_run=subprocess.run
        def read_only_run(command,*args,**kwargs):
            if not isinstance(command,(list,tuple)) or not command or Path(command[0]).name!='findmnt':
                result['mount_command_attempted']=bool(isinstance(command,(list,tuple)) and command and Path(command[0]).name in ['mount','umount'])
                raise RuntimeError('Only read-only findmnt is permitted inside mounted_build')
            return real_run(command,*args,**kwargs)
        # If the mount disappears after mountinfo was read, its recovery attempt
        # raises here. Never enter storage SDK/bind helpers.
        with patch.object(subprocess,'run',read_only_run):
            result['mounted_build_called']=True
            build=mount_module.mounted_build()
        result['build_path']=str(build)
        candidates=[]
        link=build/'source'
        if link.is_dir():candidates.append(link.resolve())
        makefile=build/'Makefile'
        if makefile.is_file():
            text=makefile.read_text()
            for line in text.splitlines():
                if line.startswith('include ') and line.endswith('/Makefile'):
                    source=Path(line[len('include '):-len('/Makefile')])
                    if not source.is_absolute():source=build/source
                    if source.is_dir():candidates.append(source.resolve())
        candidates=list(dict.fromkeys(candidates))
        if len(candidates)!=1:
            result.update(status='selected_source_ambiguous_or_missing',actual_r7_source_pinned=False,
                          selected_source_candidates=[str(p) for p in candidates])
        else:
            source=candidates[0];destination=HERE/'snapshots';destination.mkdir(exist_ok=False)
            result['selected_source']=str(source)
            for name in REQUIRED:
                path=source/name
                if not path.is_file():result['missing'].append(name);continue
                raw=path.read_bytes()
                if len(raw)>300000:raise ValueError('Unexpectedly large source file: '+name)
                target=destination/name.replace('/','--');target.write_bytes(raw)
                result['snapshots'].append(dict(source_path=str(path),file=target.name,bytes=len(raw),sha256=sha(raw)))
            result.update(status='existing_source_snapshot_only',actual_r7_source_pinned=False,
                reason='source bytes retained; binding to deployed R7 build/config still requires explicit artifact linkage')
    with (HERE/'inspection-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ['status','existing_mount_available','mounted_build_called','mount_command_executed','actual_r7_source_pinned']}))


if __name__=='__main__':main()
