from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
proof=json.loads((here.parent/'kernel214/gst-client-build-validation.json').read_text())
original=(here.parent/'kernel214/run-default-clients.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("base=Path('/var/lib/samurai/k214-baseline')","base=Path('/var/lib/samurai/k215-baseline')")
code=code.replace("out=Path('/var/lib/samurai/k214-default-clients');assert not (out/'capture-summary.json').exists()","out=Path('/var/lib/samurai/k215-default-clients');out.mkdir(mode=0o700)")
code=code.replace("listing=(out/'cam-list-stdout-private.txt').read_text()","listing=subprocess.check_output(['cam','-l'],text=True,timeout=15);(out/'cam-list-stdout-private.txt').write_text(listing)")
code=code.replace('/samurai-camera214-client-registry.bin','/samurai-camera215-client-registry.bin').replace('stage=214,uid=10000','stage=215,uid=10000')
code=code.replace('__HASH__',repr(proof['sha256']));compile(code,'native-default-clients215','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'default-clients-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'default-clients-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
