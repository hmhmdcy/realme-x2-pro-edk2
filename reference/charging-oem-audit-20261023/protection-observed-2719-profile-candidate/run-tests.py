"""Only changed profile functions/cached parser; reuse old OS stubs, not old tests."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'protection-query-observer-candidate'
PARSER=HERE.parent/'protection-evidence-parser-candidate/parse-evidence.py'
STUBS=Path('/home/cy122/charging-management-20261023/protection-query-observer-tests-r2/stubs')
OLD_DECODER=Path('/home/cy122/charging-management-20261023/protection-evidence-parser-01/frame-decoder')
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def function(text,name):
    start=text.index(name+'('); start=text.rfind('\n',0,start)+1; brace=text.index('{',start); depth=0
    for i in range(brace,len(text)):
        depth+=(text[i]=='{')-(text[i]=='}')
        if depth==0:return text[start:i+1]
    raise ValueError(name)

def owned(argv,out,label):
    with (out/(label+'-stdout-private.log')).open('xb') as stdout,(out/(label+'-stderr-private.log')).open('xb') as stderr:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:pass
        finally:rc=child.wait()
    return {'argv':argv,'pid':child.pid,'terminal':True,'returncode':rc,
        'stdout_sha256':sha((out/(label+'-stdout-private.log')).read_bytes()),'stderr_sha256':sha((out/(label+'-stderr-private.log')).read_bytes())}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    report_path=args.input_directory/'raw/cache-after-private.txt'; report=report_path.read_bytes()
    before={str(path):sha(path.read_bytes()) for path in [report_path,PARSER,OLD_DECODER,*(BASE/name for name in
        ['gauge-protocol.h','gauge-i2c.h','samurai-gauge-protection.c','test-observer.c'])]}
    old=load(PARSER,'unchanged_runtime_parser')
    original=old.parse_saved(report,OLD_DECODER,'58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2')
    assert original['header']['error']==-90 and original['header']['stage']==4 and original['header']['battery_after_valid']==0
    assert original['frames'][7]['raw'].endswith('3807') and original['frames'][7]['validate_rc']==-90
    out=args.output.resolve();out.mkdir(mode=0o700,exist_ok=False)
    packetfile=out/'saved-real8-frames-private.bin'
    packetfile.write_bytes(b''.join(frame['cmd'].to_bytes(2,'little')+bytes.fromhex(frame['raw']) for frame in original['frames']))
    source=(HERE/'samurai-gauge-protection.c').read_text()
    assert 'module_param(observed_2719_diagnostic, bool, 0444);' in source
    extracted='static bool observed_2719_diagnostic;\n'+source[source.index('static const unsigned int sm_evidence_commands'):source.index('static int sm_protection_get(')]
    extracted='\n'.join(line for line in extracted.split('\n') if not line.startswith('static DEVICE_ATTR(') and line!='static struct platform_device *sm_board;')
    (out/'actual-provider.inc').write_text(extracted)
    prefix=(BASE/'test-observer.c').read_text().split('int main(int argc,char **argv)')[0]
    prefix=prefix.replace('packets[6][36]','packets[8][36]').replace('commands[6]','commands[8]')
    start=prefix.index('static void reply(');end=prefix.index('int __i2c_smbus_xfer(',start)
    prefix=prefix[:start]+'''static void reply(unsigned int cmd,unsigned char *raw)
{for(unsigned i=0;i<8;i++)if(commands[i]==cmd){memcpy(raw,packets[i],36);return;}assert(!"unsupported fake command");}
'''+prefix[end:]
    prefix=prefix.replace('io_count=selected_count=word_count=selector=0;', 'observed_2719_diagnostic=false;io_count=selected_count=word_count=selector=0;')
    harness=prefix+(HERE/'test-profile.c').read_text();(out/'test-profile-full.c').write_text(harness)
    flags=['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare',
        '-Wno-misleading-indentation','-Wno-unused-function','-Wno-unused-variable','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread',
        '-I'+str(STUBS),'-I'+str(HERE),'-I'+str(out)]
    build=owned(flags+[str(out/'test-profile-full.c'),'-o',str(out/'test-profile')],out,'build-test')
    assert build['returncode']==0 and not (out/'build-test-stderr-private.log').read_bytes()
    run=owned([str(out/'test-profile'),str(packetfile),str(out)],out,'actual-functions')
    assert run['returncode']==0 and not (out/'actual-functions-stderr-private.log').read_bytes()
    actual=json.loads((out/'actual-functions-stdout-private.log').read_bytes());assert actual['passed'] and actual['new_actual_function_groups']==11
    decoder=out/'frame-decoder-profile'
    decoder_build=owned(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(HERE/'frame-decoder-profile.c'),'-o',str(decoder)],out,'build-decoder')
    assert decoder_build['returncode']==0 and not (out/'build-decoder-stderr-private.log').read_bytes()
    decoder_sha=sha(decoder.read_bytes()); parser=load(HERE/'parse-saved-profile.py','explicit_saved_profile_parser'); cases=[]
    def parse(name,profile):return parser.parse_saved_profile((out/name).read_bytes(),decoder,decoder_sha,profile=profile)
    for name,profile,complete in [('standard-failed.txt','standard',False),('same-attempt-not-relabelled.txt','standard',False),
        ('observed-before-attempt.txt','observed-2719-0056-3',False),('observed-synthetic-after.txt','observed-2719-0056-3',True),
        ('wrong-id.txt','observed-2719-0056-3',False),('invalid-id-frame.txt','observed-2719-0056-3',False),
        ('failure-3.txt','observed-2719-0056-3',False),('failure-4.txt','observed-2719-0056-3',False),
        ('failure-5.txt','observed-2719-0056-3',False),('wrong-length8.txt','observed-2719-0056-3',False)]:
        result=parse(name,profile);assert result['sequence_complete'] is complete and result['compatibility_verified'] is False and result['TCA_classification']=='UNVERIFIED'
        (out/(name+'.analysis-private.json')).write_text(json.dumps(result,indent=2)+'\n')
        cases.append({'cache_from_actual_functions':name,'explicit_profile':profile,'passed':True,'after0A_if_present_is_simulated':complete})
    def reject(label,data,profile):
        try:parser.parse_saved_profile(data,decoder,decoder_sha,profile=profile)
        except ValueError:cases.append({'rejection':label,'passed':True})
        else:raise AssertionError(label)
    reject('real legacy schema1 attempt cannot become new-profile cache',report,'observed-2719-0056-3')
    reject('new schema2 profile0 cannot be relabelled as profile1',(out/'standard-failed.txt').read_bytes(),'observed-2719-0056-3')
    reject('profile1 requires explicit caller selection',(out/'observed-synthetic-after.txt').read_bytes(),None)
    altered=(out/'standard-failed.txt').read_bytes().replace(b'diagnostic_profile=0',b'diagnostic_profile=1')
    reject('profile marker alone cannot rewrite original expected_size4/-90',altered,'observed-2719-0056-3')
    altered=altered.replace(b'cmd=0x0056 attempted=1 expected_size=4',b'cmd=0x0056 attempted=1 expected_size=3')
    reject('rewriting size still contradicts actual original validate_rc',altered,'observed-2719-0056-3')
    raw0=original['frames'][0]['raw'];raw56=original['frames'][7]['raw']
    for profile,expected in [('standard',-90),('observed-2719-0056-3',0)]:
        r=subprocess.run([str(decoder),'--profile',profile,'0001',raw0,'0056',raw56],capture_output=True)
        assert r.returncode==0 and not r.stderr and json.loads(r.stdout)[1]['validate_rc']==expected
        cases.append({'real_saved36byte0056_profile':profile,'validate_rc':expected,'passed':True})
    r=subprocess.run([str(decoder),'0056',raw56],capture_output=True);assert r.returncode==2
    r=subprocess.run([str(decoder),'--profile','observed-2719-0056-3','0056',raw56],capture_output=True)
    assert r.returncode==0 and json.loads(r.stdout)[0]['validate_rc']==-19
    cases.append({'rejection':'missing explicit codec profile or complete prior2719 identity','passed':True})
    unchanged={}
    function_groups={'gauge-protocol.h':['sm_mac_data_size','sm_mac_observe_data_size','sm_mac_validate_sized','sm_mac_validate','sm_gauge_protection_state'],
      'gauge-i2c.h':['sm_gauge_word_locked','sm_gauge_mac_transfer_locked','sm_gauge_mac_locked','sm_gauge_mac_observe_locked'],
      'samurai-gauge-protection.c':['sm_protection_read','sm_protection_get']}
    for name,names in function_groups.items():
        a=(BASE/name).read_text();b=(HERE/name).read_text()
        for item in names:
            assert function(a,item)==function(b,item),item;unchanged[item]=sha(function(a,item).encode())
    assert before=={name:sha(Path(name).read_bytes()) for name in before}
    result={'passed':True,'actual_function_groups':11,'saved_parser_and_codec_cases':len(cases),'cases':cases,
       'build_commands':[build,decoder_build],'actual_function_run':run,'actual_function_source_sha256':sha(extracted.encode()),
       'private_output':str(out),'decoder_sha256':decoder_sha,'original_input_hashes':before,'original_inputs_unchanged':True,
       'unchanged_production_functions':unchanged,'source_files':{name:sha((HERE/name).read_bytes()) for name in
       ['gauge-protocol.h','gauge-i2c.h','samurai-gauge-protection.c','parse-saved-profile.py','frame-decoder-profile.c','test-profile.c','run-tests.py']},
       'real_after0A_read_or_new_query':False,'candidate_batch_after0A_is_only_fake_boundary':True,'old_suites_rerun':False,'module_or_Image_built':False}
    (HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'actual_function_groups':11,'saved_parser_and_codec_cases':len(cases),'decoder_sha256':decoder_sha}))

if __name__=='__main__':main()
