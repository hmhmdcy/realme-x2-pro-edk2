"""Prepare a native LTM geometry serializer alongside the unchanged bypass."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(P/'camss-icp-a5-ipe.c.before').read_text();start=text.index('int camss_a5_ipe_encode_bypass_striping(');end=text.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_bypass_striping);',start)
fn=text[start:end].replace('camss_a5_ipe_encode_bypass_striping','camss_a5_ipe_encode_ltm_striping').replace('u32 cores, u32 *used)','u32 cores, const struct camss_a5_ipe_ltm_geometry *ltm,\n\t\t\t\t   u32 *used)')
fn=fn.replace('if (!output || !used)','if (!output || !used || !ltm)').replace('camss_a5_ipe_bypass_size(io, cores, &bytes)','camss_a5_ipe_ltm_size(io, cores, ltm, &bytes)')
fn=fn.replace('ret = camss_a5_ipe_bypass_partitions(io->input.width, cores, parts,','ret = ltm->image_processing ?\n\t\tcamss_a5_ipe_ltm_partitions(io->input.width, cores, parts,\n\t\t\t\t\t ARRAY_SIZE(parts), &count) :\n\t\tcamss_a5_ipe_bypass_partitions(io->input.width, cores, parts,')
fn=fn.replace('u32 length = p->output_last - p->output_first + 1;','u32 first = ltm->image_processing && p->output_first >= 2 ?\n\t\t\tp->output_first - 2 : p->output_first;\n\t\tu32 last = ltm->image_processing && p->output_last + 2U < width ?\n\t\t\tp->output_last + 2 : p->output_last;\n\t\tu32 length = last - first + 1;')
fn=fn.replace('u32 length = last - first + 1;', 'u32 length = p->output_last - p->output_first + 1;')
needle='put_unaligned_le16(p->output_first, stripe + 568);'
assert needle in fn
fn=fn.replace(needle, '''if (ltm->image_processing) {
			u32 grid = (max(width, 320U) + 11) / 12;
			u32 phase = first % grid;

			put_unaligned_le16(last - first, stripe + 48 + 34);
			put_unaligned_le16(first / grid, stripe + 48 + 88);
			put_unaligned_le16(phase, stripe + 48 + 90);
			put_unaligned_le16(phase * (65536 / grid), stripe + 48 + 92);
			put_unaligned_le16(first - p->fetch_first, stripe + 48 + 276);
			put_unaligned_le16(last - p->fetch_first, stripe + 48 + 278);
		}
		'''+needle)
fn=fn.replace('put_unaligned_le32(22, output + 424);','''/* DC full-pass input inherits IP only with a valid quarter pass. */
	put_unaligned_le32(ltm->data_collection && ltm->image_processing &&
			   (((width + 7) / 4) & ~1U) >= 72 &&
			   (((height + 7) / 4) & ~1U) >= 54, output + 416);
	put_unaligned_le32(22, output + 424);''')
size='''int camss_a5_ipe_ltm_size(const struct camss_a5_ipe_io *io, u32 cores,
			 const struct camss_a5_ipe_ltm_geometry *ltm, u32 *bytes)
{
	u32 checked, stripes;
	int ret;

	if (!ltm || !bytes)
		return -EINVAL;
	ret = camss_a5_ipe_bypass_size(io, cores, &checked);
	if (ret)
		return ret;
	if (!ltm->image_processing) {
		*bytes = checked;
		return 0;
	}
	stripes = (io->input.width + 323) / 324;
	stripes = ((stripes + cores - 1) / cores) * cores;
	*bytes = 2268 + 624 * stripes;
	return 0;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_ltm_size);

'''
fn=fn.replace('int camss_a5_ipe_encode_ltm_striping(', 'static int ipe_encode_striping(')
fn=fn.replace('ltm->image_processing ?', '(ltm->image_processing && ltm->mask_filter) ?').replace('ltm->image_processing && p->', 'ltm->image_processing && ltm->mask_filter && p->').replace('if (ltm->image_processing)', 'if (ltm->image_processing && ltm->mask_filter)')
size=size.replace('!ltm->image_processing', '!(ltm->image_processing && ltm->mask_filter)')
fn=fn.replace('(ltm->image_processing && ltm->mask_filter)', 'mask').replace('ltm->image_processing && ltm->mask_filter &&', 'mask &&')
fn=fn.replace('u8 *output = buffer;', 'u8 *output = buffer;\n\tbool mask;').replace('ret = camss_a5_ipe_ltm_size', 'mask = ltm->image_processing && ltm->mask_filter;\n\tret = camss_a5_ipe_ltm_size').replace('if mask', 'if (mask)')
fn=fn[:fn.index('\n{')]+fn[fn.index('\n{'):]
head_end=fn.index('\n{')
fn='''static int ipe_encode_striping(void *buffer, u32 capacity,
			       const struct camss_a5_ipe_io *io, u32 cores,
			       const struct camss_a5_ipe_ltm_geometry *ltm,
			       u32 *used)'''+fn[head_end:]
fn=fn.replace('\n}\n', '\n}\n\n')
wrappers='''int camss_a5_ipe_encode_bypass_striping(void *buffer, u32 capacity,
				      const struct camss_a5_ipe_io *io,
				      u32 cores, u32 *used)
{
	const struct camss_a5_ipe_ltm_geometry disabled = {};

	return ipe_encode_striping(buffer, capacity, io, cores, &disabled, used);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_bypass_striping);

int camss_a5_ipe_encode_ltm_striping(void *buffer, u32 capacity,
				   const struct camss_a5_ipe_io *io, u32 cores,
				   const struct camss_a5_ipe_ltm_geometry *ltm,
				   u32 *used)
{
	return ipe_encode_striping(buffer, capacity, io, cores, ltm, used);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_ltm_striping);
'''
assert not text[end+len('EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_bypass_striping);'):].strip()
text=text[:start]+size+fn+wrappers;(P/'camss-icp-a5-ipe.c.proposed').write_text(text)
header=(P/'camss-icp-a5-ipe.h.before').read_text();assert header.endswith('#endif\n')
header=header.replace('/* LTM image-processing partition ranges only.', '/* LTM image-processing plus mask-filter partition ranges only.')
header=header[:-7]+'''/* Full-frame 1:1 geometry only; IQ/LUT ownership and runtime submission
 * remain the caller's responsibility. This does not activate LTM.
 */
struct camss_a5_ipe_ltm_geometry {
	bool data_collection;
	bool image_processing;
	bool mask_filter;
};
int camss_a5_ipe_ltm_size(const struct camss_a5_ipe_io *io, u32 cores,
			 const struct camss_a5_ipe_ltm_geometry *ltm, u32 *bytes);
int camss_a5_ipe_encode_ltm_striping(void *buffer, u32 capacity,
				 const struct camss_a5_ipe_io *io, u32 cores,
				 const struct camss_a5_ipe_ltm_geometry *ltm,
				 u32 *used);

#endif
''';(P/'camss-icp-a5-ipe.h.proposed').write_text(header)
print('Prepared native prototype; not applied or submitted.')
