import host
p=host.ssh("python3 -",input=b"from pathlib import Path\nimport json\np=Path('/var/lib/samurai/k190-mm-build')\nprint(json.dumps(dict(logs=len(list(p.glob('*-private.log'))),sdk_ready=(p/'sdk-validation-private.json').exists(),last_logs=[x.name for x in sorted(p.glob('*-private.log'),key=lambda p:p.stat().st_mtime)[-3:]])))\n")
print(p.stdout.decode());print(p.stderr.decode());raise SystemExit(p.returncode)
