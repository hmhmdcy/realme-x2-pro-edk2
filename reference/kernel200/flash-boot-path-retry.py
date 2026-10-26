from pathlib import Path
import hashlib,json,re,subprocess,host

ref=Path(__file__).resolve().parent;out=host.PRIVATE
failed=(out/'fastboot-flash-boot-private.log').read_text()
assert "fastboot: error: cannot load '/mnt/e/edk2-samurai-out/kernel200/boot-partition-k200-mmcx.img': No such file or directory" in failed
assert 'Sending ' not in failed and 'Writing ' not in failed and 'OKAY' not in failed
prior=json.loads((out/'boot-flash-request-private.json').read_text());assert prior['request_count']==1 and prior['partitions']==['boot']
assert not (out/'fastboot-reboot-request-private.json').exists()
s=(ref/'flash-boot.py').read_text()
s=s.replace("marker=out/'boot-flash-request-private.json'", "marker=out/'boot-flash-path-corrected-request-private.json'")
s=s.replace("path=out/(name+'-private.log')", "path=out/('path-corrected-'+name+'-private.log')")
s=s.replace("assert observed[0]==expected", "assert observed[0]==expected==prior['actual_serial']")
s=s.replace("runtime_readback_pending=True)", "runtime_readback_pending=True,initial_local_file_open_failure_before_transfer=True,flash_tool_invocations=2,successful_image_transfer_count=1)")
exec(compile(s,'<fresh-identity-corrected-Windows-path-flash>','exec'))
