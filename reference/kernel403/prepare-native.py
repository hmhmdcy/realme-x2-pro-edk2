"""Prepare the checked LTM partition primitive without changing runtime flow."""
from pathlib import Path
import difflib,importlib.util,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'partitions-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';base=source/'drivers/media/platform/qcom/camss'
changed=['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h'];patches=[]
for name in changed:(P/(name+'.before')).write_bytes((base/name).read_bytes())
text=(P/'camss-icp-a5-ipe.c.before').read_text();start=text.index('/* Full-frame, unity-scale, 8-bit linear YUV with IQ modules disabled.');stop=text.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_bypass_partitions);',start)+len('EXPORT_SYMBOL_GPL(camss_a5_ipe_bypass_partitions);')
old=text[start:stop];fn=old[old.index('int camss_a5_ipe_bypass_partitions'):old.index('EXPORT_SYMBOL_GPL')]
fn=fn.replace('int camss_a5_ipe_bypass_partitions(u32 width, u32 cores,','static int ipe_partitions(u32 width, u32 cores, u32 step, u32 halo,').replace('(width + 327) / 328','(width + step - 1) / step').replace('first < 4 ? 0 : first - 4','first < halo ? 0 : first - halo').replace('last + 4 < width ? last + 4 : width - 1','last + halo < width ? last + halo : width - 1')
new='''/* Full-frame unity-scale 8-bit YUV. Common range checks preserve output
 * and count on rejection; the two target policies differ in step and halo.
 * This is a partition primitive, not a complete LTM striping serializer.
 */
'''+fn+'''
int camss_a5_ipe_bypass_partitions(u32 width, u32 cores,
				 struct camss_a5_ipe_partition *output,
				 u32 capacity, u32 *count)
{
	return ipe_partitions(width, cores, 328, 4, output, capacity, count);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_bypass_partitions);

int camss_a5_ipe_ltm_partitions(u32 width, u32 cores,
			      struct camss_a5_ipe_partition *output,
			      u32 capacity, u32 *count)
{
	return ipe_partitions(width, cores, 324, 6, output, capacity, count);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_ltm_partitions);'''
text=text[:start]+new+text[stop:];(P/'camss-icp-a5-ipe.c.proposed').write_text(text)
header=(P/'camss-icp-a5-ipe.h.before').read_text();match=re.search(r'int camss_a5_ipe_bypass_partitions\([^;]+;',header,re.S);assert match
header=header[:match.end()]+'''
/* LTM image-processing partition ranges only. Callers still need the LTM
 * processing crops, grid and firmware blob before submitting enabled LTM.
 */
int camss_a5_ipe_ltm_partitions(u32 width, u32 cores,
			      struct camss_a5_ipe_partition *output,
			      u32 capacity, u32 *count);
'''+header[match.end():];(P/'camss-icp-a5-ipe.h.proposed').write_text(header)
for name in changed:patches+=difflib.unified_diff((P/(name+'.before')).read_text().splitlines(True),(P/(name+'.proposed')).read_text().splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name)
(HERE/'ltm-partitions.patch').write_text(''.join(patches));(HERE/'build-intree.py').write_text((HERE.parent/'kernel402/build-intree.py').read_text().replace('stage=402','stage=403'))
print('Prepared shared checked partition helper; runtime remains on bypass serializer.')
