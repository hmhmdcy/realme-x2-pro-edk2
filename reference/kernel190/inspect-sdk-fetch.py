import host
p=host.ssh('python3 -',input=b"from pathlib import Path\np=Path('/var/lib/samurai/k190-mm-build/fetch-extra-private.log')\nprint(p.read_text()[-1800:])\n")
print(p.stdout.decode());raise SystemExit(p.returncode)
