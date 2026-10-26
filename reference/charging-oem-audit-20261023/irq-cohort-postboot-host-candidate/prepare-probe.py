"""Extract the frozen device's actual small read-only identity path; no collection."""
from pathlib import Path
import ast
import hashlib
import json
HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'irq-cohort-postboot-readonly/device.py'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    raw = SOURCE.read_bytes()
    assert sha(raw) == '78337b7801b21e120f7814a2f8857e52dc1056ef80364821a6507d5faf2a444d'
    source = raw.decode(); tree = ast.parse(source)
    names = ['attempt', 'read', 'file_fact', 'check_file', 'identity', 'check_identity']
    functions = {node.name: ast.get_source_segment(source, node) for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names}
    assert set(functions) == set(names)
    header = '''"""Actual frozen identity functions only. Default never reads the device."""
from pathlib import Path
import base64, hashlib, json, os, re, stat, sys, time
sha = lambda raw: hashlib.sha256(raw).hexdigest()
'''
    tail = '''

def main(request=None):
 if sys.flags.optimize:raise RuntimeError('optimized Python is unsupported')
 if request is None:
  print(json.dumps({'source_only':True,'device_accessed':False}));return 0
 assert request['schema']=='samurai-irq-postboot-identity-probe-v1'
 started=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
 before=identity();check_identity(before,request['guard'])
 after=identity();check_identity(after,request['guard'])
 assert before['boot_id']==after['boot_id']
 print(json.dumps({'schema':request['schema'],'request':request,
  'identity_before':before,'identity_after':after,'started_boottime_ns':started,
  'ended_boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)}),flush=True)
 return 0

if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
'''
    target = header + '\n\n'.join(functions[n] for n in names) + tail
    (HERE / 'identity-probe.py').write_text(target, encoding='utf-8', newline='\n')
    (HERE / 'probe-source-reuse.json').write_text(json.dumps({'source_sha256':sha(raw),
        'probe_sha256':sha((HERE/'identity-probe.py').read_bytes()),
        'actual_functions':{n:sha(functions[n].encode()) for n in names},
        'device_accessed':False}, indent=2)+'\n')
    print(json.dumps({'passed':True,'function_count':len(names),'device_accessed':False}))


if __name__ == '__main__': main()
