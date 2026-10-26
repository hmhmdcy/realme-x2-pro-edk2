from pathlib import Path
import ast, hashlib, host, json, shutil, subprocess
here = Path(__file__).resolve().parent; repo = here.parents[1]; radio = repo / 'linux-port/radio'
helper = radio / 'samurai-wifi.sh'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == 'ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd'
shutil.copyfile(helper, host.PRIVATE / 'samurai-wifi-before-mcfg-private.sh')
text = helper.read_text(); needle = '    umount "$base/stock-modem"'
assert text.count(needle) == 1
text = text.replace(needle, '''    /usr/sbin/samurai-modem-configs "$base/stock-modem/image" "$base/firmware/$firmware" "$base/mcfg-source-manifest-private.json" > "$base/mcfg-prepare.log"
''' + needle)
helper.write_text(text)
subprocess.run(['sh', '-n', str(helper)], check=True)
program = radio / 'samurai-modem-configs.py'; ast.parse(program.read_text())
lock_path = radio / 'source-lock.json'; lock = json.loads(lock_path.read_text())
for p in [helper, program]: lock['own_sources'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
lock_path.write_text(json.dumps(lock, indent=2) + '\n')
out = '/var/lib/samurai/k207-mcfg-stage'
code = "from pathlib import Path; import os; os.umask(0o077); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k207-runtime/boot-id-private.txt').read_bytes(); Path(" + repr(out) + ").mkdir(mode=0o700)"
host.ssh('python3 -', input=code.encode())
hashes = {}
for name, path in [('samurai-wifi-new.sh', helper), ('samurai-modem-configs-new.py', program)]:
    host.upload(path, out + '/' + name); hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
code = "from pathlib import Path; import json; p=Path(" + repr(out) + "); (p/'artifacts-private.json').write_text(json.dumps(" + repr(hashes) + "))"
host.ssh('python3 -', input=code.encode())
(here / 'mcfg-startup-source-validation.json').write_text(json.dumps(dict(stage=207, staged_sources=hashes, stock_modem_source_read_only=True, runtime_copy_target_tmpfs=True, firmware_binary_data_not_in_repository=True, shell_and_python_syntax_passed=True), indent=2) + '\n')
print(json.dumps(dict(new_source_hashes=hashes, runtime_not_yet_installed=True)))
