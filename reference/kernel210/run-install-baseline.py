from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
source=(here/'collect-install-baseline.py').read_text().replace("root/'k210-install-before'","root/'k210-install-before-r2'").replace("sum(n.endswith('.ko') for n in files)==784","sum(n.endswith('.ko') for n in files)==770 and len(files)==784").replace('installed_module_count=784','installed_module_count=770,installed_regular_files=784,first_count_assertion_confused_files_with_modules=True')
(host.PRIVATE/'install-baseline-r2-source-private.py').write_text(source)
p=host.ssh('python3 -',input=source.encode(),timeout=90)
(host.PRIVATE/'install-baseline-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'install-baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
