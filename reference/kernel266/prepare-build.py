from pathlib import Path
R=Path(__file__).parent
s=(R.parent/'kernel235/build-imx319.py').read_text().replace("kernel235')","kernel266')").replace("out = P / 'imx319-build-r4'","out = P / 'imx319-build-r1'").replace('stage=235','stage=266').replace('canonical_after228_restored=True','canonical_source_tree_restored=True').replace('actual_of_runtime_candidate_built=True','standard_metadata_candidate_built=True')
needle="assert before == json.loads((P / 'kernel-before-private.json').read_text())";assert s.count(needle)==1;s=s.replace(needle,"(P / 'kernel-before-private.json').write_text(json.dumps(before, indent=2)+'\\n')")
p=R/'build-imx319.py';assert not p.exists();p.write_text(s)
print('Prepared current-tree snapshot/restore in-tree W=1 module build')

