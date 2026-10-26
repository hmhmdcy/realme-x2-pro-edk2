from pathlib import Path
import json,re
private=Path('/mnt/e/edk2-samurai-out/kernel214');active=json.loads((private/'active-camera-build-private.json').read_text());pid=active['pid'];proc=Path('/proc',str(pid));alive=proc.exists()
phase=active['phase'];suffix='-r'+phase.rsplit('-r',1)[1] if re.search(r'-r\d+$',phase) else '';log=private/('full-libcamera-build'+suffix+'-private.log');text=log.read_text(errors='replace');progress=re.findall(r'(?m)^\[(\d+)/(\d+)\]',text)
result=dict(phase=phase,process_exists=alive,process_state=proc.joinpath('status').read_text().split('State:',1)[1].splitlines()[0].strip() if alive else None,last_ninja_progress=list(map(int,progress[-1])) if progress else None,log_lines=len(text.splitlines()),tail=text.splitlines()[-10:],result_record_exists=(private/('full-libcamera-build'+suffix+'-result-private.json')).exists())
print(json.dumps(result))
