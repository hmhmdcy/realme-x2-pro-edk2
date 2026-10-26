"""Small saved0056 diagnosis. No original suite, new module or device access."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, subprocess
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
HEADER = HERE.parent / 'protection-query-observer-candidate/gauge-protocol.h'
OLD_PARSER = HERE.parent / 'protection-evidence-parser-candidate/parse-evidence.py'
OLD_DECODER = Path('/home/cy122/charging-management-20261023/protection-evidence-parser-01/frame-decoder')
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def module():
    spec=importlib.util.spec_from_file_location('saved0056_diagnosis',HERE/'analyze-saved.py')
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result

def run_owned(argv,out,label):
    with (out/(label+'-stdout-private.log')).open('xb') as stdout,(out/(label+'-stderr-private.log')).open('xb') as stderr:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,close_fds=True)
        try: pass
        finally: rc=child.wait()
    return {'argv':argv,'pid':child.pid,'terminal':True,'returncode':rc,
            'stdout_sha256':sha((out/(label+'-stdout-private.log')).read_bytes()),
            'stderr_sha256':sha((out/(label+'-stderr-private.log')).read_bytes())}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); inputs=args.input_directory.resolve(); out=args.output.resolve()
    report_path=inputs/'raw/cache-after-private.txt'; analysis_path=inputs/'capture-analysis-private.json'
    paths=[report_path,analysis_path,HEADER,OLD_PARSER,OLD_DECODER]
    before={str(path):sha(path.read_bytes()) for path in paths}
    assert before[str(HEADER)]=='98148c0701d000c21c7a9be60d0d14e412887f90fc1b83d0a3de8168359c28df'
    assert before[str(OLD_DECODER)]=='58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2'
    report=report_path.read_bytes(); analysis=analysis_path.read_bytes(); m=module()
    parsed=m.parser_module().parse_saved(report,OLD_DECODER,m.OLD_DECODER_SHA)
    packet=bytes.fromhex(parsed['frames'][7]['raw'])
    out.mkdir(mode=0o700,exist_ok=False)
    decoder=out/'frame-decoder-r2'
    command=['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'frame-decoder-r2.c'),'-o',str(decoder)]
    build=run_owned(command,out,'build'); assert build['returncode']==0 and not (out/'build-stderr-private.log').read_bytes()
    decoder_sha=sha(decoder.read_bytes()); cases=[]
    def check(label,raw,rc,expected=None):
        run=subprocess.run([str(decoder),raw],capture_output=True,check=False)
        assert run.returncode==rc and not run.stderr,(label,run.stderr)
        if expected is not None:
            value=json.loads(run.stdout)
            assert all(value[key]==item for key,item in expected.items()),(label,value)
        cases.append({'case':label,'passed':True})
    check('actual full36 retains legacy size4 EMSGSIZE and validates observed payload3',packet.hex(),0,
          {'legacy_payload4_validate_rc':-90,'observed_2719_payload3_validate_rc':0,'raw_value_u24':0x091850,'length_byte':7})
    changed=bytearray(packet); changed[34]^=1
    check('synthetic checksum mutation rejected by actual validator',changed.hex(),0,{'observed_2719_payload3_validate_rc':-74,'raw_value_u24':None})
    changed=bytearray(packet); changed[0]^=1
    check('synthetic echo mutation rejected',changed.hex(),0,{'observed_2719_payload3_validate_rc':-11,'raw_value_u24':None})
    changed=bytearray(packet); changed[35]=8
    check('observed profile refuses declared length8 rather than silently widening',changed.hex(),0,{'observed_2719_payload3_validate_rc':-90,'raw_value_u24':None})
    check('short physical36 input rejected',packet[:-1].hex(),2)
    check('nonhex input rejected','x'+packet.hex()[1:],2)
    result=m.analyze_saved(report,analysis,OLD_DECODER,decoder,decoder_sha)
    assert result['observed_frame_valid'] is True and result['original_validate_rc']==-90 and result['raw_value_u24']==0x091850
    assert result['original_sequence_complete'] is result['batch_sequence_complete'] is result['stability_verified'] is False
    assert result['battery_after_read'] is result['compatibility_verified'] is result['source_authentication_newly_verified'] is False
    (out/'analysis-r2-private.json').write_text(json.dumps(result,indent=2)+'\n')
    cases.append({'case':'actual saved full batch remains stage4 error-90 and no trailing0A despite isolated R2 frame success','passed':True})
    def reject(label,fn):
        try:fn()
        except ValueError:cases.append({'case':label,'passed':True})
        else:raise AssertionError(label)
    altered=json.loads(analysis); altered['parsed']['input_sha256']='0'*64
    reject('mismatched original analysis input is not consumed',lambda:m.analyze_saved(report,json.dumps(altered).encode(),OLD_DECODER,decoder,decoder_sha))
    altered_report=report.replace(b'cmd=0x0056 attempted=1 expected_size=4',b'cmd=0x0056 attempted=1 expected_size=3')
    reject('R1 runtime expected_size cannot be rewritten to reinterpret report',lambda:m.analyze_saved(altered_report,analysis,OLD_DECODER,decoder,decoder_sha))
    reject('wrong new decoder binary identity rejected',lambda:m.analyze_saved(report,analysis,OLD_DECODER,decoder,'0'*64))
    assert before=={name:sha(Path(name).read_bytes()) for name in before}
    receipt={'passed':True,'new_cases':len(cases),'cases':cases,'actual_C_header_sha256':before[str(HEADER)],
       'actual_same_validator_used_for_both_lengths':True,'diagnostic_decoder_sha256':decoder_sha,'build':build,
       'original_inputs':before,'original_inputs_unchanged':True,'private_output':str(out),'source_files':{name:sha((HERE/name).read_bytes()) for name in
       ['frame-decoder-r2.c','analyze-saved.py','test-saved.py']},'old_suites_rerun':False,'new_queries_or_modules':False,'device_accessed':False}
    (HERE/'test-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'new_cases':len(cases),'diagnostic_decoder_sha256':decoder_sha,
                      'original_size4_rc':-90,'observed_size3_rc':0,'raw_value_u24':result['raw_value_u24'],'private_output':str(out)}))

if __name__=='__main__':main()
