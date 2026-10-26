from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'preparation-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='47475238dc6a0d4b28a5db22b0c1af223dc50297' and not git('status','--porcelain')
names=['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h'];before={n:(source/relative/n).read_text() for n in names};after=dict(before)
after[names[0]]+='\n'+(HERE/'bypass-partitions.c').read_text()
declaration='''
/* Inclusive ranges in descending output order for the disabled-IQ,
 * full-frame 1:1 NV12/NV21 path. No scaling or geometric warp is implied.
 */
struct camss_a5_ipe_partition {
\tu16 fetch_first, fetch_last;
\tu16 output_first, output_last;
};
int camss_a5_ipe_bypass_partitions(u32 width, u32 cores,
\t\t\t\t struct camss_a5_ipe_partition *output,
\t\t\t\t u32 capacity, u32 *count);
'''
assert after[names[1]].count('\n#endif')==1;after[names[1]]=after[names[1]].replace('\n#endif','\n'+declaration+'\n#endif')
patch=''
for name in names:
 (P/(name+'.before')).write_text(before[name]);(P/(name+'.proposed')).write_text(after[name])
 patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
(HERE/'bypass-partitions.patch').write_text(patch)
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=383,parent=git('rev-parse','HEAD'),changed=names,complete_striping_serializer_available=False,installed=False),indent=2)+'\n')
print('Prepared the native inclusive-range partition component; the full firmware serializer remains separate work.')
