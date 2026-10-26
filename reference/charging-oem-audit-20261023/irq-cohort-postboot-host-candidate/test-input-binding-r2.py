"""Only R2's new input binding; never execute old 18/13/31 suites."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import importlib.util
import json
import tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    spec=importlib.util.spec_from_file_location('actual_irq_host_r2',HERE/'host.py')
    host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    cases=[]
    with tempfile.TemporaryDirectory(prefix='irq-input-binding-r2-') as temp:
        directory=Path(temp);payload=b'# explicitly synthetic exact read-only input\n'
        stdout,stderr=b'{"synthetic":true}\n',b''
        argv=['original-key','synthetic-popen']
        child=dict(pid=891,start_ticks=1234,argv=argv,stdin_sha256=sha(payload))
        terminal=dict(child,terminal=True,returncode=0,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
        for name,raw in [('executed-device-source.py',payload),('stdout-private.json',stdout),('stderr-private.txt',stderr)]:
            (directory/name).write_bytes(raw)
        def receipts(c,t):
            (directory/'child-private.json').write_text(json.dumps(c))
            (directory/'terminal-private.json').write_text(json.dumps(t))
        with patch.object(host,'transport_argv',return_value=argv):
            receipts(child,terminal)
            assert host.saved_transport(directory,payload,host.PEER)==(stdout,stderr,terminal)
            cases.append('both original receipts bind the same exact payload')
            for name,role,missing in [('missing child input hash','child',True),('missing terminal input hash','terminal',True),
                                     ('different child input hash','child',False),('different terminal input hash','terminal',False)]:
                c,t=dict(child),dict(terminal);target=c if role=='child' else t
                if missing:target.pop('stdin_sha256')
                else:target['stdin_sha256']=sha(payload+b'different')
                receipts(c,t)
                try:host.saved_transport(directory,payload,host.PEER)
                except ValueError as error:assert 'exact input payload' in str(error)
                else:raise AssertionError(name)
                cases.append(name)
    result=dict(passed=True,cases=cases,count=len(cases),new_negative_categories=['missing','different'],
        actual_saved_transport_function=True,only_existing_transport_argv_boundary_fake=True,
        old_18_13_31_suites_rerun=False,actual_payload_transmitted=False,device_or_transport_accessed=False,
        files={name:sha((HERE/name).read_bytes()) for name in ('host.py','test-input-binding-r2.py')})
    with (HERE/'input-binding-r2-result.json').open('x') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


if __name__=='__main__':main()
