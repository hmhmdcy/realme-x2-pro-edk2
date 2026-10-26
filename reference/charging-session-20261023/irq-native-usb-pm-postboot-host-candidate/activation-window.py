"""Inspect then restart with one source review, checking every retained byte."""
from pathlib import Path
from unittest.mock import patch
import argparse, copy, hashlib, importlib.util, json, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def cached_review(original, stage, fetched):
    reads={};read_bytes=Path.read_bytes
    def observed(path):
        raw=read_bytes(path);resolved=path.resolve();digest=hashlib.sha256(raw).hexdigest()
        if resolved in reads and reads[resolved]!=digest:raise ValueError('source changed during review')
        reads[resolved]=digest;return raw
    with patch.object(Path,'read_bytes',observed): result=original(stage,fetched)
    def retained(actual_stage,actual_fetch):
        if (actual_stage,actual_fetch)!=(stage,fetched):raise ValueError('different source selection')
        for path,digest in reads.items():
            if hashlib.sha256(read_bytes(path)).hexdigest()!=digest:raise ValueError('reviewed source changed: '+str(path))
        return copy.deepcopy(result)
    return retained,reads

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--transaction',required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--window-confirmed',action='store_true');a=p.parse_args()
    if not (a.execute and a.window_confirmed):raise ValueError('explicit restart and exclusive window required')
    path=HERE.parent/'irq-native-usb-pm-retained-source-candidate/activation-controller.py'
    spec=importlib.util.spec_from_file_location('pm_current_activation_window',path);adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    c=adapter.c;directory,request,binding,pins=c.bound(a.transaction)
    c.reviewed,reads=cached_review(c.reviewed,binding['stage_directory'],binding['stage_fetch_directory'])
    # Original bound repeats guard/owner/endpoint checks. Only the expensive
    # unchanged historical review is reused; device checks remain independent.
    c.bound(a.transaction,revalidate=True)
    out=directory/'restart-window-sources-private.json'
    c.save(out,dict(schema='samurai-pm-restart-window-v1',source_files={str(k):v for k,v in reads.items()},
                    adapter_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),original_dispatch_reused=True))
    inspected=c.run('inspect',a.transaction,True,True)
    if not inspected.get('inspect_only'):raise ValueError('inspect pending or unsuccessful; observe original')
    print(json.dumps(dict(inspect_passed=True,source_files=len(reads))),flush=True)
    print(json.dumps(c.run('restart',a.transaction,True,True)),flush=True)

if __name__=='__main__':main()
