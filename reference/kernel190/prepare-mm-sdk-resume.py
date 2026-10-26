from pathlib import Path
import host
ref=Path(__file__).resolve().parent
code=(ref/'prepare-mm-sdk.py').read_text().replace("out.mkdir(mode=0o700)","out.mkdir(mode=0o700,exist_ok=True)").replace("sdk.mkdir(mode=0o755)","sdk.mkdir(mode=0o755,exist_ok=True)")
code=code.replace("extra=out/'extra-apks';extra.mkdir()\nrun(['apk','--no-cache','fetch','--recursive','--output',str(extra),'dbus-dev','libgudev-dev','eudev-dev','elogind-dev','polkit-dev'], 'fetch-extra')", "assert not (out/'extract-0-private.log').exists()\nextra=Path('/var/lib/samurai/k190-mm-sdk-host-apks');assert len(list(extra.glob('*.apk')))==5")
assert 'fetch-extra' not in code
(ref/'prepare-mm-sdk-host-staged-expanded.py').write_text(code)
p=host.ssh('python3 -',input=code.encode(),timeout=900)
(host.PRIVATE/'prepare-mm-sdk-staged-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode()[-1200:]);print('exit',p.returncode);raise SystemExit(p.returncode)
