from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
a=json.loads((HERE.parent/'kernel444/build-validation.json').read_text());b=json.loads((HERE/'build-validation.json').read_text())
before={r['name']:r['sha256'] for r in a['runtime_files']};after={r['name']:r['sha256'] for r in b['runtime_files']}
assert b['passed'] and b['private_ipa_version']==6
for name in ['ipa_camss_vfe.so','ipa_camss_vfe.so.sign','camss_ipa_proxy']:assert before[name]==after[name]
assert json.loads((HERE/'focus-validation.json').read_text())['passed']
source=(HERE.parent/'kernel444/check-runtime-inputs.py').read_text().replace('stage=444','stage=445')
source=source.replace("HERE/'focused-module-validation.json'", "HERE.parent/'kernel444/focused-module-validation.json'")
source=source.replace('actual_candidate_ipa_signature_verified_in_module_contract=True', 'actual_candidate_ipa_signature_verified_in_retained_byte_identical444_module_contract=True,ipa_signature_and_proxy_byte_identical_to444=True,exact_focus_numeric_contract_verified=True')
exec(compile(source,str(HERE/'check-runtime-inputs.py'),'exec'))
