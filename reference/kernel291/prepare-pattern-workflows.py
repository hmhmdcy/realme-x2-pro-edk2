"""Generate separately identified sensor-pattern workers; do not launch in parallel."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for kind,base in [('raw','raw'),('pix','physical')]:
 worker=(ROOT/f'native-{base}.py').read_text()
 worker=worker.replace(f'k291-{base}-r1',f'k291-pattern-{kind}-r1').replace(f'k291-tools/physical-{kind}',f'k291-tools/pattern-{kind}')
 worker=worker.replace("'--capture'","'--pattern'").replace('sensor_and_csid_tpg_disabled=True','sensor_pattern=2,csid_pattern=0')
 (ROOT/f'native-pattern-{kind}.py').write_text(worker)
 launcher=(ROOT/'launch-raw.py').read_text()
 launcher=launcher.replace("proof=json.loads((ROOT/'raw-tool-validation.json').read_text())",f"proof=json.loads((ROOT/'pattern-tool-validation.json').read_text())['tools']['{kind}']")
 launcher=launcher.replace('physical-raw-aarch64-private',f'pattern-{kind}-aarch64-private').replace('physical-raw',f'pattern-{kind}')
 launcher=launcher.replace('native-raw.py',f'native-pattern-{kind}.py').replace('k291-raw-r1',f'k291-pattern-{kind}-r1')
 launcher=launcher.replace('raw-worker',f'pattern-{kind}-worker').replace('raw-launch',f'pattern-{kind}-launch')
 (ROOT/f'launch-pattern-{kind}.py').write_text(launcher)
 poll=(ROOT/'poll-raw.py').read_text().replace('raw-launch',f'pattern-{kind}-launch').replace('k291-raw-r1',f'k291-pattern-{kind}-r1')
 poll=poll.replace('raw-poll',f'pattern-{kind}-poll').replace('raw-capture-validation',f'pattern-{kind}-capture-validation')
 (ROOT/f'poll-pattern-{kind}.py').write_text(poll)
print('Prepared sequential raw and PIX sensor-pattern workflows.')
