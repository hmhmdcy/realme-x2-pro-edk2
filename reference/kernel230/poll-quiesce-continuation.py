from pathlib import Path
import host
source=(Path(__file__).resolve().parent/'poll-quiesce.py').read_text().replace('k230-quiesce-runner','k230-quiesce-runner-r2').replace('quiesce-poll-host-private.json','quiesce-continuation-poll-host-private.json')
exec(compile(source,'poll-quiesce-continuation','exec'))
