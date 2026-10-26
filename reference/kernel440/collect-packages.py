from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel420/collect-packages.py').read_text()
source=source.replace('stage=420','stage=440').replace('420-r31','440-r32').replace('camera420-package-prefix','camera440-package-prefix').replace('99990.7.2-r31','99990.7.2-r32').replace('0.1.0-r26','0.1.0-r27')
source=source.replace('kernel391/package-artifact-validation.json','kernel420/package-artifact-validation.json').replace('kernel391/runtime-repository/forward','kernel420/runtime-repository/forward').replace('camera391-package-prefix','camera420-package-prefix')
source=source.replace('CAMSS420','CAMSS440')
source=source.replace("assert all(ipa_equal.values()),'Inspect changed packaged IPA before reusing unchanged numerical evidence'", "assert not ipa_equal['ipa_camss_vfe.so'] and all(v for n,v in ipa_equal.items() if n!='ipa_camss_vfe.so'),'Inspect unexpected non-CAMSS changes'")
source=source.replace('packaged_ipa_binary_identical_to_r30=ipa_equal','packaged_ipa_equality_to_r31=ipa_equal').replace('unchanged_ipa_mathematical_contract_reused_from_stage362=True','packaged_camss_mathematical_contract_still_to_run=True').replace('signed_forward_and_r30_r25_rollback_repositories=True','signed_forward_and_r31_r26_rollback_repositories=True').replace('all_ipa_binaries_match_r30=True','noncamss_ipa_binaries_match_r31=True')
source=source.replace('440-r32','440-r32-r2').replace('camera440-package-prefix','camera440-package-prefix-r2')
source=source.replace("repository=P/'runtime-repository'", "repository=P/'runtime-repository-r2'")
exec(compile(source,str(HERE/'collect-packages.py'),'exec'))
