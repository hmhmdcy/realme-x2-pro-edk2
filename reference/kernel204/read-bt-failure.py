import host
code=b"from pathlib import Path\np=Path('/var/lib/samurai/k204-bt-scan-pm/failure-private.txt')\nprint(p.read_text().splitlines()[-1])\n"
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
