"""Bind frozen SOURCE inputs only. Requires the separately frozen adoption helper pins."""
from pathlib import Path
import argparse, hashlib, json
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--helper-sha256', required=True); p.add_argument('--helper-pins-sha256', required=True)
    args=p.parse_args()
    helper=REF/'charging-session-20261023/icon-capture-irq-cohort-candidate'
    assert sha((helper/'adoption-review.py').read_bytes())==args.helper_sha256
    assert sha((helper/'source-pins.json').read_bytes())==args.helper_pins_sha256
    old=HERE.parent/'usb-irq-protection-stage-host-candidate-r2'
    parser=HERE.parent/'protection-evidence-parser-candidate'
    files={'adoption_review':helper/'adoption-review.py','adoption_review_pins':helper/'source-pins.json',
        'original_delivery':old/'delivery.json','original_host':old/'host.py','original_remote':old/'remote.py',
        'original_supervisor':old/'supervisor.py','key_transport':REF/'kernel184/host.py',
        'worker':HERE/'stage-worker.py','host':HERE/'host.py','remote':HERE/'remote.py','supervisor':HERE/'supervisor.py',
        'parser':parser/'parse-evidence.py','parser_delivery':parser/'delivery.json','parser_tests':parser/'test-result.json',
        'decoder_source':parser/'frame-decoder.c','gauge_protocol':HERE.parent/'protection-query-observer-candidate/gauge-protocol.h',
        'observer_module_receipt':HERE.parent/'protection-query-observer-module-candidate/ko-result.json',
        'cohort_delivery':REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/delivery.json'}
    rows={}
    for name,path in files.items():
        raw=path.read_bytes(); rows[name]={'path':str(path).replace('\\','/'),'sha256':sha(raw),'bytes':len(raw)}
    with (HERE/'source-pins.json').open('xb') as stream: stream.write((json.dumps(rows,indent=2)+'\n').encode())
    print(json.dumps({'source_only':True,'source_pins_sha256':sha((HERE/'source-pins.json').read_bytes()),'runtime_identity_created':False}))

if __name__=='__main__': main()
