from pathlib import Path
import runpy,re,difflib,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';runpy.run_path(str(ref/'ensure-build-volume.py'));k=Path('/home/cy122/pmos-samurai-build126/kernel');base=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
assert not (ref/'sm8150-tpg-dma-guards-7.3.patch').exists()
changes={}
rel='drivers/media/platform/qcom/camss/camss-video.c';old=(k/rel).read_text();start=old.index('static int video_buf_init(')
helper='''/* Verify every byte the SM8150 write master may address, including SG joins. */
static int video_check_dma_mapping(struct camss_video *video,
				   struct sg_table *sgt, size_t size)
{
	struct scatterlist *sg;
	dma_addr_t address, expected;
	size_t remaining = size;
	unsigned int i;

	if (video->camss->res->version != CAMSS_8150)
		return 0;
	if (!sgt || !sgt->sgl || !sgt->nents || !size)
		return -EINVAL;
	address = sg_dma_address(sgt->sgl);
	if (address < 0x07400000 || address >= 0xe0000000 ||
	    size > 0xe0000000 - address)
		return -ERANGE;
	expected = address;
	for_each_sgtable_dma_sg(sgt, sg, i) {
		size_t length = sg_dma_len(sg);

		if (!length || sg_dma_address(sg) != expected)
			return -EINVAL;
		if (length >= remaining)
			return 0;
		remaining -= length;
		expected += length;
	}
	return -EINVAL;
}

'''
new=old[:start]+helper+old[start:]
new=new.replace('\tunsigned int i;\n\n\tfor (i = 0; i < format->num_planes; i++) {\n\t\tsgt = vb2_dma_sg_plane_desc(vb, i);','\tunsigned int i;\n\tint ret;\n\n\tfor (i = 0; i < format->num_planes; i++) {\n\t\tsgt = vb2_dma_sg_plane_desc(vb, i);',1)
needle='\t\tbuffer->addr[i] = sg_dma_address(sgt->sgl);'
assert new.count(needle)==1
new=new.replace(needle,'''\t\tret = video_check_dma_mapping(video, sgt, vb2_plane_size(vb, i));
\t\tif (ret)
\t\t\treturn ret;
\t\tbuffer->addr[i] = sg_dma_address(sgt->sgl);
\t\tdev_dbg(video->camss->dev, "DMA plane %u address %pad size %lu\\n",
\t\t\ti, &buffer->addr[i], vb2_plane_size(vb, i));''')
a=new.index('static int video_buf_prepare(');b=new.index('\n}',a)+2;part=new[a:b]
needle='\tunsigned int i;\n\n\tfor (i = 0; i < format->num_planes; i++) {'
assert needle in part
part=part.replace(needle,'''\tunsigned int i;
\tint ret;

\t/* Imports can change their mapped SG list between preparations. */
\tret = video_buf_init(vb);
\tif (ret)
\t\treturn ret;

\tfor (i = 0; i < format->num_planes; i++) {''')
new=new[:a]+part+new[b:];assert old!=new;changes[rel]=(old,new)
rel='drivers/media/platform/qcom/camss/camss-csid.c';old=(k/rel).read_text();a=old.index('static int csid_set_power(');b=old.index('\n}',a)+2;part=old[a:b];m=part.index('\t\tret = pm_runtime_resume_and_get(dev);');tail=part[m:]
assert tail.count('\t\t\treturn ret;')==5
tail=tail.replace('\t\t\treturn ret;','\t\t\tgoto put_parent;')
tail=tail.removesuffix('\n}')+'''

put_parent:
\tcsid->res->parent_dev_ops->put(camss, csid->id);
\treturn ret;
}'''
new=old[:a]+part[:m]+tail+old[b:];changes[rel]=(old,new)
rel='drivers/media/platform/qcom/camss/camss-cpas.c';old=(k/rel).read_text();new=old.replace('both actual allocator reservations','both reservation callback policies');assert new!=old;changes[rel]=(old,new)
rel='arch/arm64/boot/dts/qcom/sm8150-samurai.dts';old=(k/rel).read_text();needle='&camss {\n\tvdda-phy-supply = <&vreg_l3c_1p2>;\n};';assert old.count(needle)==1
new=old.replace(needle,'&camss {\n\t/* Internal CSID TPG; CCI and all external sensors remain disabled. */\n\tstatus = "okay";\n\tvdda-phy-supply = <&vreg_l3c_1p2>;\n};');changes[rel]=(old,new)
for rel,(old,new) in changes.items():assert (base/rel).read_text()==old
for rel,(old,new) in changes.items():(k/rel).write_text(new)
patch=''.join(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)) for rel,(old,new) in changes.items());(ref/'sm8150-tpg-dma-guards-7.3.patch').write_text(patch)
(ref/'tpg-port-validation.json').write_text(json.dumps(dict(candidate=126,base=125,changed_files=list(changes),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),sm8150_each_mapped_plane_native_range_and_contiguous_sg_required=True,dmabuf_prepare_rechecks_mapping=True,csid_parent_put_on_five_power_failures=True,camss_enabled_internal_tpg_only=True,cci_and_external_sensors_disabled=True,phone_not_deployed=True),indent=2)+'\n');print('K126_TPG_DMA_MAPPING_AND_CSID_FAILURE_UNWIND_PORTED')
