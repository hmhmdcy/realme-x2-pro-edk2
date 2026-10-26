from pathlib import Path
import importlib.util,json

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel204')
spec=importlib.util.spec_from_file_location('authenticated_wifi',here/'host-wifi-before-transition.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
p=transport.ssh('python3 -',input=(here/'collect-newboot.py').read_bytes(),timeout=160)
(private/'newboot-wifi-private.log').write_bytes(p.stdout+p.stderr);r=json.loads(p.stdout);assert r['new_boot_identity_verified'] and r['uart_rx_wake_enabled']
(here/'runtime-validation.json').write_text(json.dumps(r,indent=2)+'\n')
backup=here/'host-usb-before-newboot.py';assert not backup.exists();backup.write_bytes((here/'host.py').read_bytes())
(here/'host.py').write_bytes((here/'host-wifi-before-transition.py').read_bytes())
transport.download('/var/lib/samurai/k204-runtime/boot-id-private.txt',private/'new-boot-id-private.txt')
print(json.dumps(r))
