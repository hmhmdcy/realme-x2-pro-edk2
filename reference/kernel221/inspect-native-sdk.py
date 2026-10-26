import host
code=r'''
from pathlib import Path
import json
sdk=Path('/var/lib/samurai/k190-mm-sdk');env=json.loads(Path('/var/lib/samurai/k190-mm-build/build-environment-private.json').read_text())
print(json.dumps(dict(sdk_present=sdk.is_dir(),header=(sdk/'usr/include/libqmi-glib/qmi-device.h').is_file(),compiler=[str(p) for p in (sdk/'usr/bin').glob('*gcc')],environment={k:v for k,v in env.items() if k in ['CC','CFLAGS','LDFLAGS','PKG_CONFIG','PKG_CONFIG_PATH','PKG_CONFIG_SYSROOT_DIR','PATH','GCC_EXEC_PREFIX','LD_LIBRARY_PATH']})))
for name in ['qmi-device.h','qmi-message.h']:
 lines=(sdk/'usr/include/libqmi-glib'/name).read_text().splitlines();terms=['qmi_device_command_full','qmi_device_new_from_node','qmi_device_open (','qmi_device_allocate_client','SIGNAL_INDICATION','qmi_message_foreach_raw_tlv','qmi_message_new (','qmi_message_get_raw_tlv','qmi_message_response_get_result','qmi_message_get_raw (']
 ix=[i for i,l in enumerate(lines) if any(s in l for s in terms)]
 print(name+'\n'+'\n'.join(str(i+1)+': '+l for i,l in enumerate(lines) if any(0<=i-j<12 for j in ix)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'native-sdk-inspect-private.log').write_bytes(p.stdout+p.stderr);print(p.stdout.decode())
