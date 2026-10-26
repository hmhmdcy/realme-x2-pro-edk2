from pathlib import Path
import json,hashlib,shutil
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
import sys
af='--af' in sys.argv
if af:sys.argv.remove('--af')
replay='--replay' in sys.argv
if replay:sys.argv.remove('--replay')
no_lsc='--no-lsc' in sys.argv
if no_lsc:sys.argv.remove('--no-lsc')
restore_bls='--restore-bls' in sys.argv
if restore_bls:sys.argv.remove('--restore-bls')
assert sum([replay,no_lsc,restore_bls])<=1
assert not af or restore_bls
uncorrected='--uncorrected-baseline' in sys.argv
if uncorrected:sys.argv.remove('--uncorrected-baseline')
assert not (uncorrected and restore_bls)
assert json.loads((HERE/'baseline-validation.json').read_text())['passed']
assert json.loads((HERE/'preflight-validation.json').read_text())['passed']
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed']
previous=json.loads((HERE.parent/'kernel435/build-validation.json').read_text())
for name in ['ipa_camss_vfe.so','ipa_camss_vfe.so.sign','camss_ipa_proxy']:
 assert next(r['sha256'] for r in build['runtime_files'] if r['name']==name)==next(r['sha256'] for r in previous['runtime_files'] if r['name']==name)
shutil.copyfile(P.parent/'kernel435/factory-s5kgw1-private.yaml',P/'factory-s5kgw1-private.yaml')
if not uncorrected:
 assert json.loads((HERE/'profile-export-validation.json').read_text())['passed']
 shutil.copyfile(P/'bls-corrected-s5kgw1-private.yaml',P/'factory-s5kgw1-private.yaml')
if no_lsc:
 profile=P/'factory-s5kgw1-private.yaml';original=profile.read_text()
 needle='  lens_shading:\n';assert original.count(needle)==2
 changed=original.replace(needle,needle+'    enabled: false\n')
 assert changed.replace(needle+'    enabled: false\n',needle)==original
 profile.write_text(changed)
 (P/'lsc-counterfactual-profile-private.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),counterfactual_sha256=hashlib.sha256(changed.encode()).hexdigest(),only_lsc_enabled_false_added=True)))
if restore_bls:
 assert json.loads((HERE/'main-factory-bls-export-validation.json').read_text())['independent_reader_and_direct_decoder_agree']
 shutil.copyfile(P/'bls-corrected-s5kgw1-private.yaml',P/'factory-s5kgw1-private.yaml')
source=(HERE.parent/'kernel435/stage-runtime.py').read_text()
source=source.replace("for name in ['ipa','history','native-gtm','profile-export','preflight','source','retention']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']", "assert json.loads((HERE/'baseline-validation.json').read_text())['passed']")
source=source.replace("(HERE/'ipa-validation.json')","(HERE.parent/'kernel435/ipa-validation.json')")
source=source.replace("'stage':435","'stage':436").replace('k435-gtm-auto-','k436-tone-domain-')
if af:
 body=(HERE/'auto-capture-body.py').read_text()
 body=body.replace(" state['candidate_final_status']=status();", " assert re.search(r'ADAPT_FRAME .* af-state=2 ',text),'AF did not report Focused'\n state['autofocus_focused']=True\n state['candidate_final_status']=status();")
 (P/'af-capture-body-private.py').write_text(body)
 source=source.replace("(HERE/'auto-capture-body.py')","(P/'af-capture-body-private.py')")
 source=source.replace("P.parent/'kernel423/capture'","P.parent/'kernel424/capture'")
if replay:
 assert json.loads((HERE/'replay-build-validation.json').read_text())['passed']
 source=source.replace("(HERE/'auto-capture-body.py')","(HERE/'replay-body.py')")
 source=source.replace("'baseline-private.json':P/'preflight-stdout-private.json'", "'baseline-private.json':P/'preflight-stdout-private.json','tone-replay':P/'tone-replay','full-private.bin':P/'full-private.bin','pd10-private.bin':P/'pd10-private.bin','parameters-private.bin':P/'parameters-private.bin'")
 source=source.replace("['capture','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','pipeline-fixture','proxy/camss_ipa_proxy','tone-replay']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
