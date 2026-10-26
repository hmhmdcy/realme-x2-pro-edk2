from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=(here/'build-helper-candidate.py').read_text().replace(" and not build.exists()", " and build.is_dir()")
marker="db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((out/'build-environment-private.json').read_text())"
extra="""active=json.loads((out/'active-build-private.json').read_text());assert active['phase']=='configure-helper' and not Path('/proc',str(active['pid'])).exists()
assert 'Dependency lookup for egl' in (out/'configure-helper-private.log').read_text()
(out/'configure-helper-first-meson-log-private.txt').write_bytes((build/'meson-logs/meson-log.txt').read_bytes())
"""
assert marker in code;code=code.replace(marker,extra+marker).replace("('configure-helper',args)","('configure-helper-r2',args)")
p=host.ssh('python3 -',input=code.encode(),timeout=1400);(host.PRIVATE/'build-helper-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'helper-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
