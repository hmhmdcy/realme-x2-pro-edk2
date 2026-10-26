"""Build one offline worker from frozen actual helpers; no runtime request."""
from pathlib import Path
import ast
import hashlib
import json
HERE=Path(__file__).resolve().parent
REF=HERE.parent.parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def main():
    stage=REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py'
    proof=HERE.parent/'irq-cohort-postboot-host-candidate/stage-proof.py'
    need={'stage':'47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a',
          'proof':'85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093'}
    helpers=[];reuse={}; sources={}
    for name,path,wanted in [('stage',stage,{'need','sha','detail','encode','read_owned','validate_lease','AtomicFailure','atomic_replace'}),
                             ('proof',proof,{'verify_chain','verify_stage'})]:
        raw=path.read_bytes();assert sha(raw)==need[name];text=raw.decode();sources[name]=dict(path=str(path.resolve()),sha256=sha(raw))
        found=set()
        for node in ast.parse(text).body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in wanted:
                segment=ast.get_source_segment(text,node);helpers.append(segment);found.add(node.name)
                reuse[node.name]=dict(source=name,sha256=sha(segment.encode()),line=node.lineno,end_line=node.end_lineno)
        assert found==wanted
    cohort=REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
    data=json.loads((cohort/'cohort-manifest.json').read_bytes())
    manifest=json.loads((cohort/'manifest.json').read_bytes())
    oldfiles={manifest['modules'][name]['target']:row['old']['sha256'] for name,row in data['modules'].items()}
    oldfiles['/usr/share/samurai-charging/manifest.json']=data['old_manifest_sha256']
    newfiles={manifest['modules'][name]['target']:row['new']['sha256'] for name,row in data['modules'].items()}
    newfiles['/usr/share/samurai-charging/manifest.json']=data['new_manifest_sha256']
    oldnotes={name:row['old']['resident_note_sha256'] for name,row in data['modules'].items()}
    newnotes={name:row['new']['resident_note_sha256'] for name,row in data['modules'].items()}
    oldnotes['samurai-mp2650']=newnotes['samurai-mp2650']=data['unchanged_charger_identity']['resident_note_sha256']
    ptext=proof.read_text();evidence=next(ast.literal_eval(n.value) for n in ast.parse(ptext).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EVIDENCE' for t in n.targets))
    header='''#!/usr/bin/python3
"""Default inert. Explicit exact three-file R8 disk restore; never activate modules."""
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import argparse,base64,copy,hashlib,io,json,math,os,re,runpy,stat,struct,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
'''
    constants='\n'.join(name+' = '+repr(value) for name,value in [('OLD_FILES',oldfiles),('NEW_FILES',newfiles),
        ('OLD_NOTES',oldnotes),('NEW_NOTES',newnotes),('NEW_MANIFEST',manifest),('EVIDENCE',evidence)])
    source=header+constants+'\n\n'+'\n\n'.join(helpers)+'\n\n'+(HERE/'worker-body.py.inc').read_text()
    ast.parse(source)
    target=HERE/'restore-worker.py'
    if target.exists():assert target.read_bytes()==source.encode(), 'existing candidate differs from exact generated source'
    else:
        with target.open('x',encoding='utf-8',newline='\n') as file:file.write(source)
    result=dict(software_sources_only=True,helper_reuse=reuse,source_inputs=sources,
        worker_sha256=sha((HERE/'restore-worker.py').read_bytes()),body_sha256=sha((HERE/'worker-body.py.inc').read_bytes()),
        runtime_request_or_guard_generated=False,device_accessed=False)
    with (HERE/'source-reuse.json').open('w') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,reused_actual_helpers=len(reuse),runtime_request_generated=False)))


if __name__=='__main__':main()
