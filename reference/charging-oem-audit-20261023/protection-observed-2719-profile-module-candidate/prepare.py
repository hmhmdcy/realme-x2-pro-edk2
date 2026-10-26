"""Narrow source-pinned derivative of the already used Image502 intree ko builder."""
from pathlib import Path
import hashlib, json, difflib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'protection-query-observer-module-candidate/build-ko.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=BASE.read_bytes()
assert sha(raw)=='6d484f62844c4976c928ab9a6e81fee0851076a33ab188974dd06cbaf689262f'
text=raw.decode()
changes={
"AUTHOR=HERE.parent/'protection-query-observer-candidate'":"AUTHOR=HERE.parent/'protection-observed-2719-profile-candidate'",
"/protection-query-observer-module-01'":"/protection-observed-2719-profile-module-01'",
"/protection-query-observer-module-private-01'":"/protection-observed-2719-profile-module-private-01'",
'3e1e81a341a5df072cde2c57ec7505096c192e7b873cfbb2720375ae7f9b8f6d':'3078c62fdb7ef9f2aefbce3bac64be508b66fb0734fbcac7edcbd95bebbe1015',
'8846d20648dc0b137a2608be9a7ed479ecd692b17db6875a2a18a2d046d7c8b2':'a47a031b66bea9c10d00a0dec271a2d21cb0497ef8e28285642f3115bb48803d',
'98148c0701d000c21c7a9be60d0d14e412887f90fc1b83d0a3de8168359c28df':'080f1d621886c3772f5b0b83ec4e5b4150c0e37007dd8fce707594882ff83e02',
'907fc1245576eee21b3d5231c25359f6d101e1f537ea8ff423ee21139392a304':'45467c6084d04e2149614477595781fe0a329d10fd9cb9d0b61d44ec84d2a509',
'6ed3a351b01b1bf2b75586348b3a87aca62ec0170a86aa30ee62a1baac721033':'6a9a7ec194b67158af16e04a5c12a7ea6aa0ca4a0da098d03afca568018f39fc',
'protection_module_original_storage284':'protection_profile_original_storage284',
'samurai-gauge-protection-observer-private.ko':'samurai-gauge-protection-observed-2719-private.ko',
}
for old,new in changes.items():
    assert old in text,old
    text=text.replace(old,new)
text=text.replace("  assert not run_output(['modinfo','-F','depends',str(ko)]).strip()", "  assert not run_output(['modinfo','-F','depends',str(ko)]).strip()\n  assert 'observed_2719_diagnostic:bool' in run_output(['modinfo','-F','parmtype',str(ko)]).splitlines()")
text=text.replace("  'old21_and_codec149_reused_not_rerun':True,", "  'old21_and_codec149_reused_not_rerun':True,'profile11_and_parser18_reused_not_rerun':True,\n  'default_observed_2719_diagnostic':False,'ordinary_Health_policy_unchanged':True,'new_query_or_attempt_created':False,")
text=text.replace("if __name__=='__main__':raise SystemExit(main())", """if __name__=='__main__':
 if sys.argv[1:]==['--execute']:raise SystemExit(main())
 assert not sys.argv[1:],'only explicit --execute; default source check'
 assert sha(AUTHOR/'delivery.json')=='45467c6084d04e2149614477595781fe0a329d10fd9cb9d0b61d44ec84d2a509'
 author=json.loads((AUTHOR/'delivery.json').read_bytes())
 for name,row in author['files'].items():assert sha(AUTHOR/name)==row['sha256']
 for name,digest in NAMES.items():assert sha(AUTHOR/name)==digest
 source=(AUTHOR/'samurai-gauge-protection.c').read_text()
 assert 'static bool observed_2719_diagnostic;' in source and 'module_param(observed_2719_diagnostic, bool, 0444);' in source
 print(json.dumps({'passed':True,'source_only':True,'default_profile':False,'storage_or_build_accessed':False,'device_accessed':False,'actual_output_created':False}))
""")
(HERE/'build-ko.py').write_text(text,encoding='utf-8',newline='\n')
(HERE/'method-delta.patch').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),text.splitlines(True),fromfile='frozen-observer/build-ko.py',tofile='observed-2719-profile/build-ko.py')),encoding='utf-8',newline='\n')
print(json.dumps({'builder_sha256':sha((HERE/'build-ko.py').read_bytes()),'base_builder_sha256':sha(raw)}))
