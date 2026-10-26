"""Derive the authorized single-ko builder from frozen flat build bytes."""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'usb-input-flat-consumer-candidate'
raw=(BASE/'build-ko.py').read_bytes()
delivery=json.loads((BASE/'delivery.json').read_bytes())
assert hashlib.sha256(raw).hexdigest()==delivery['files']['build-ko.py']['sha256']
text=raw.decode()
changes=[
 ('One private R8 flat-consumer USB ko','One private R8 native-PM-link USB ko'),
 ('usb-input-flat-consumer-01','usb-input-native-pm-link-01'),
 ('usb-input-flat-consumer-private-01','usb-input-native-pm-link-private-01'),
 ('ee0f0806c5a51576f10b299aca173c61ab2b4764a5954c1039d1c73327878a88','faa99156b26c1ae3a8147bb2009d5ed2b8c9e99d72a15acfd090bff793b6d9b0'),
 ("author['candidate_source_sha256']","author['source_sha256']"),
 ("assert author['all_other_source_bytes_identical'] and author['legacy_prefix_byte_identical']",
  "assert author['changed_old_function'] == 'samurai_usb_probe' and len(author['old_functions_byte_identical']) == 12"),
 ("tests['actual_function_result']['actual_function_cases'] == 11","tests['actual_result']['actual_function_cases'] == 21"),
 ("'flat_source_receipt_sha256'","'native_pm_source_receipt_sha256'"),
 ('samurai-usb-input-flat-private.ko','samurai-usb-input-pm-link-private.ko'),
]
for old,new in changes:
    assert text.count(old)==1,(old,text.count(old))
    text=text.replace(old,new)
(HERE/'build-ko.py').write_text(text,encoding='utf-8',newline='\n')
result=dict(passed=True,source_builder_sha256=hashlib.sha256(raw).hexdigest(),
    candidate_builder_sha256=hashlib.sha256((HERE/'build-ko.py').read_bytes()).hexdigest(),
    exact_substitutions=changes,only_author_source_receipt_and_private_namespace_changes=True,
    original_guard_and_build_algorithm_preserved=True,executed=False)
(HERE/'build-derivation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
