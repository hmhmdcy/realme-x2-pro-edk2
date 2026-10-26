from pathlib import Path
import hashlib, host, json, shutil, subprocess
here = Path(__file__).resolve().parent; radio = here.parents[1] / 'linux-port/radio'
helper = radio / 'samurai-wifi.sh'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '32f33e30ab8bf1e366a2a0b5f0b4de8550b12b68fdbfaf3f150d0c09cb3d75f3'
shutil.copyfile(helper, host.PRIVATE / 'samurai-wifi-mcfg-first-stage-private.sh')
text = helper.read_text()
needle = '    /usr/sbin/samurai-modem-configs "$base/stock-modem/image" "$base/firmware/$firmware" "$base/mcfg-source-manifest-private.json" > "$base/mcfg-prepare.log"'
assert text.count(needle) == 1
text = text.replace(needle, '    mkdir -m 0700 "$base/mcfg-state"\n' + needle.replace('$base/mcfg-source-manifest-private.json', '$base/mcfg-state/source-manifest-private.json'))
helper.write_text(text); subprocess.run(['sh', '-n', str(helper)], check=True)
lock_path = radio / 'source-lock.json'; lock = json.loads(lock_path.read_text())
lock['own_sources'][helper.name] = hashlib.sha256(helper.read_bytes()).hexdigest()
lock_path.write_text(json.dumps(lock, indent=2) + '\n')
remote = '/var/lib/samurai/k207-mcfg-stage'
host.upload(helper, remote + '/samurai-wifi-new-r2.sh')
hashes = {'samurai-wifi-new-r2.sh': hashlib.sha256(helper.read_bytes()).hexdigest(), 'samurai-modem-configs-new.py': hashlib.sha256((radio / 'samurai-modem-configs.py').read_bytes()).hexdigest()}
code = "from pathlib import Path; import json; p=Path(" + repr(remote) + "); (p/'artifacts-r2-private.json').write_text(json.dumps(" + repr(hashes) + "))"
host.ssh('python3 -', input=code.encode())
native = (here / 'deploy-stock-mcfg.py').read_text().replace("out = root / 'k207-mcfg-deploy'", "out = root / 'k207-mcfg-deploy-r2'")
native = native.replace("stage / 'artifacts-private.json'", "stage / 'artifacts-r2-private.json'")
native = native.replace("manifest = Path('/run/samurai-wifi/mcfg-source-manifest-private.json'); assert not manifest.exists()", "state_dir=Path('/run/samurai-wifi/mcfg-state'); state_dir.mkdir(mode=0o700)\nmanifest = state_dir/'source-manifest-private.json'; assert not manifest.exists()")
native = native.replace("stage / 'samurai-wifi-new.sh'", "stage / 'samurai-wifi-new-r2.sh'")
compile(native, 'deploy-stock-mcfg-r2.py', 'exec'); (here / 'deploy-stock-mcfg-r2.py').write_text(native)
print(json.dumps(dict(private_state_directory_added=True, new_wifi_helper_sha256=hashes['samurai-wifi-new-r2.sh'], first_failure_preserved=True)))
