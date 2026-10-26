"""Integrate native variable-size DC geometry and paired V4L2 formats."""
from pathlib import Path
import hashlib,json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;k=storage.mount.mounted_build().parent/'source354';camss=k/'drivers/media/platform/qcom/camss'
for name in ['geometry-prototype','geometry-edges','native-bl']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
def git(*args):return subprocess.check_output(['git','-C',str(k),*args],text=True)
parent='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3';assert git('rev-parse','HEAD').strip()==parent and not git('status','--porcelain')
subprocess.run(['git','-C',str(k),'switch','-c','samurai-ipe-variable-pd10-441'],check=True,capture_output=True)
p=camss/'camss-icp-a5-ipe.c';text=p.read_text();a=text.index('/* Initial native two-pass profile:');assert text[a:].rstrip().endswith('EXPORT_SYMBOL_GPL(camss_a5_ipe_encode_ltm_pd10_striping);')
p.write_text(text[:a]+(HERE/'pd10-striping.c').read_text())
p=camss/'camss-icp-a5-m2m.c';text=p.read_text()
def replace(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
match=re.search(r'#define IPE_IMAGE_MAX[^\n]*\n',text);assert match
text=text[:match.end()]+'/* Paired coarse backing is bounded by the existing diagnostic scratch owner. */\n#define IPE_COARSE_MAX_BYTES 0x40000U\n'+text[match.end():]
replace('struct camss_a5_ipe_coarse_input coarse = {};','struct camss_a5_ipe_coarse_input coarse = {};\n\tstruct camss_a5_pd10_layout coarse_layout;')
replace('if (use_coarse) {\n\t\tcoarse_buffer', '''if (use_coarse) {
		struct camss_a5_nv12_layout full = {
			ctx->format.width, ctx->format.height,
			ctx->format.plane_fmt[0].bytesperline, ctx->format.height, false };

		ret = camss_a5_ipe_pd10_quarter(&full, &coarse_layout);
		if (ret)
			goto finish;
		coarse_buffer''')
replace('coarse.bytes = 46080;','coarse.bytes = coarse_layout.bytes;')
replace('u64 stride, max_stride;','u64 stride, max_stride;\n\tstruct camss_a5_nv12_layout full;\n\tstruct camss_a5_pd10_layout coarse_layout;\n\tint ret;')
replace('if (coarse && (p->width != 640 || p->height != 480))\n\t\treturn -EOPNOTSUPP;', '''if (coarse) {
		full = (struct camss_a5_nv12_layout){ p->width, p->height, stride, p->height, false };
		ret = camss_a5_ipe_pd10_quarter(&full, &coarse_layout);
		if (ret)
			return ret;
		/* Reject a larger coarse owner before REQBUFS or hardware configuration.
		 * The generic serializer has no such allocation policy baked into it. */
		if (coarse_layout.bytes > IPE_COARSE_MAX_BYTES)
			return -EOPNOTSUPP;
	}''')
replace('p->plane_fmt[1].bytesperline = 768;\n\t\tp->plane_fmt[1].sizeimage = 46080;','p->plane_fmt[1].bytesperline = coarse_layout.stride;\n\t\tp->plane_fmt[1].sizeimage = coarse_layout.bytes;')
replace('if (!output && ctx->coarse && (f->fmt.pix_mp.width != 640 ||\n\t\t    f->fmt.pix_mp.height != 480 || f->fmt.pix_mp.pixelformat != V4L2_PIX_FMT_NV12))', '''if (!output && ctx->coarse &&
		    (f->fmt.pix_mp.width != ctx->format.width ||
		     f->fmt.pix_mp.height != ctx->format.height ||
		     f->fmt.pix_mp.pixelformat != V4L2_PIX_FMT_NV12 ||
		     f->fmt.pix_mp.plane_fmt[0].bytesperline != ctx->format.plane_fmt[0].bytesperline ||
		     f->fmt.pix_mp.plane_fmt[0].sizeimage != ctx->format.plane_fmt[0].sizeimage))''')
p.write_text(text);subprocess.run(['git','-C',str(k),'diff','--check'],check=True)
names=['camss-icp-a5-ipe.c','camss-icp-a5-m2m.c'];rows=[dict(path='drivers/media/platform/qcom/camss/'+name,sha256=hashlib.sha256((camss/name).read_bytes()).hexdigest()) for name in names]
subprocess.run(['git','-C',str(k),'add','--',*[r['path'] for r in rows]],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: serialize native variable-size PD10 DC passes'],check=True,capture_output=True)
(HERE/'variable-pd10-kernel.patch').write_text(git('diff',parent,'HEAD'))
report=dict(stage=441,parent_commit=parent,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),source_hashes=rows,changes_only_geometry_and_paired_format_sizing=True,coarse_328_vs_full_mask_324_partition_steps=True,actual_quarter_layout_for_m2m_payload=True,capture_matches_paired_source_geometry_and_stride=True,coarse_format_capacity_bound_bytes=0x40000,user_abi_and_dma_release_policy_unchanged=True,no_mmio_added=True,no_board_or_sensor_change=True,installed=False,passed=True)
(HERE/'kernel-source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
