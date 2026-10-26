"""Prepare a NEW 451/452 attempt with a monotonic kernel-log cutoff."""
from pathlib import Path
import argparse,ast,hashlib,json,re,sys

HERE=Path(__file__).resolve().parent
OLD="start_uptime=float(Path('/proc/uptime').read_text().split()[0])"
NEW='start_uptime=time.monotonic()'

def transformed_source(kind):
    stage=451 if kind=='comparison' else 452
    path=HERE.parent/('kernel'+str(stage))/('prepare-'+kind+'.py')
    source=path.read_text()
    pattern=r'''^([ \t]*body\s*=\s*\(HERE\.parent\s*/\s*["']kernel434/capture-worker-body\.py["']\)\.read_text\(\))$'''
    matches=list(re.finditer(pattern,source,re.M))
    assert len(matches)==1
    source=re.sub(pattern,lambda m:m[0]+'.replace('+repr(OLD)+','+repr(NEW)+')',source,flags=re.M)
    ast.parse(source)
    return path,source

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=['comparison','diagnostic'])
    args,remaining=parser.parse_known_args()
    assert '--attempt' in remaining,'Supply a new numbered attempt; never replay r1'
    attempt=remaining[remaining.index('--attempt')+1]
    assert re.fullmatch(r'r([2-9]|1[0-9]|20)',attempt)
    path,source=transformed_source(args.kind)
    body=(HERE.parent/'kernel434/capture-worker-body.py').read_text()
    assert body.count(OLD)==1
    sys.argv=[str(path),*remaining]
    namespace={'__name__':'__main__','__file__':str(path)}
    exec(compile(source,str(path)+' [monotonic wrapper]','exec'),namespace)
    stage=451 if args.kind=='comparison' else 452
    private=Path('/mnt/e/edk2-samurai-out')/('kernel'+str(stage))
    worker=private/(args.kind+'-prepared-'+attempt)/'worker.py'
    text=worker.read_text();assert NEW in text and OLD not in text
    report=dict(stage=stage,attempt=attempt,legacy_prepare_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rendered_worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),kernel_fault_cutoff_clock='CLOCK_MONOTONIC',historical_worker_or_receipts_modified=False,phone_accessed=False,passed=True)
    (private/(args.kind+'-monotonic-'+attempt+'-private.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
