import host
p=host.ssh('python3 -',input=b"from pathlib import Path\np=Path('/var/lib/samurai/k190-evidence-export')\nprint((p/'summary.json').read_text())\nprint('archive_exists',(p/'evidence-private.tar.gz').exists())\n")
print(p.stdout.decode())
