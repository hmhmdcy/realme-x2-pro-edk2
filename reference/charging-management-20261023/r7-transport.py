"""Original pinned-key USB IPv6 transport; only the observed NCM peer."""
from pathlib import Path
import importlib.util
import ipaddress
import json
import subprocess

PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
ENDPOINT=PRIVATE/'r7-postboot/usb-ipv6-transport-private.json'
REF=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('original_key',REF.parent/'kernel184/host.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def raw_ssh(command,**kwargs):
    data=json.loads(ENDPOINT.read_text())
    assert data['kind']=='usb-ipv6' and data['original_key_verified'] is True
    assert data['host_key_alias']=='169.254.42.1' and data['interface_index']==29
    assert data['peer']=='fe80::62:bcff:fe28:a101%29'
    assert ipaddress.IPv6Address(data['peer'].split('%')[0]).is_link_local
    q=subprocess.run([base.SSH,'-6','-T',*base.OPTIONS,'-o','HostKeyAlias=169.254.42.1',
                     'root@'+data['peer'],command],input=kwargs.get('input'),
                     capture_output=True,timeout=kwargs.get('timeout',30))
    if kwargs.get('check',True) and q.returncode:
        raise RuntimeError('Original-key USB IPv6 SSH failed: '+q.stderr.decode(errors='replace')[-1200:])
    return q


if __name__=='__main__':
    import hashlib,os
    assert not ENDPOINT.exists()
    peer='fe80::62:bcff:fe28:a101%29'  # observed by interface29 multicast/ND, not guessed
    code="""from pathlib import Path
import hashlib,json,os
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'release':os.uname().release,'version':os.uname().version,
 'taint':Path('/proc/sys/kernel/tainted').read_text().strip(),
 'manifest_sha256':hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()}))
"""
    import shlex
    q=subprocess.run([base.SSH,'-6','-T',*base.OPTIONS,'-o','HostKeyAlias=169.254.42.1',
                      'root@'+peer,'python3 -c '+shlex.quote(code)],capture_output=True,timeout=20)
    (ENDPOINT.parent/'ipv6-probe-stdout-private.json').write_bytes(q.stdout)
    (ENDPOINT.parent/'ipv6-probe-stderr-private.txt').write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    observed=json.loads(q.stdout)
    previous=json.loads((PRIVATE/'r7-restart/prepare-stdout-private.json').read_text())['guard']
    assert observed['boot_id']!=previous['boot_id']
    assert observed['release']==previous['kernel_release'] and observed['version']==previous['kernel_version']
    assert observed['taint']=='0' and observed['manifest_sha256']=='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
    data={'kind':'usb-ipv6','peer':peer,'interface_index':29,'host_key_alias':'169.254.42.1',
          'original_key_verified':True,'observed_new_boot':observed['boot_id']}
    with ENDPOINT.open('x') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
    print(json.dumps({'original_key_verified':True,'new_boot':True,'taint':0,'r7_manifest':True}))
