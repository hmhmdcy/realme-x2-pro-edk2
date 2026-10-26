"""Use declared outputs to gate pad formats, then expose the VFE175 parameter queue."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='15c8639d8badf5d4146bfd1b2c2fcb2460a137e5' and not git('status','--porcelain')
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-params292'],check=True,capture_output=True)
prefix=TREE/'drivers/media/platform/qcom/camss'
common=prefix/'camss-vfe.c';s=common.read_text();old=s
insert='''/* Sparse PIX outputs retain their shared pad numbers, but not formats. */
static bool vfe_pad_supported(const struct vfe_line *line, unsigned int pad)
{
	unsigned int o;

	if (pad >= line->num_pads)
		return false;
	if (pad == MSM_VFE_PAD_SINK || pad == MSM_VFE_PAD_SRC)
		return true;

	for (o = 1; o < line->num_outputs; o++)
		if (line->output[o].pad == pad)
			return true;

	return false;
}

'''
needle='/*\n * __vfe_get_format - Get pointer to format structure';assert s.count(needle)==1;s=s.replace(needle,insert+needle)
needle='''	if (which == V4L2_SUBDEV_FORMAT_TRY)
		return v4l2_subdev_state_get_format(sd_state, pad);'''
assert s.count(needle)==1;s=s.replace(needle,'''\tif (!vfe_pad_supported(line, pad))
		return NULL;

'''+needle)
for signature,arg in [('static int vfe_enum_mbus_code(', 'code'),('static int vfe_enum_frame_size(', 'fse')]:
 start=s.index(signature);brace=s.index('\n{',start);end=s.index('\n}',brace)
 fragment=s[brace:end];needle='\n\tswitch (code->pad)' if arg=='code' else '\n\t/* Metadata has no frame size */'
 assert fragment.count(needle)==1
 replacement=f'\n\tif (!vfe_pad_supported(line, {arg}->pad))\n\t\treturn -EINVAL;\n'+needle
 fragment=fragment.replace(needle,replacement);s=s[:brace]+fragment+s[end:]
assert s!=old;common.write_text(s)
ops=prefix/'camss-vfe-17x.c';s=ops.read_text();old=s
needle='''		vfe_add_yuv(&pix->output[0], 3, 4, 0);
		vfe_set_pix(pix, 1);
		/* Only sink and FULL are implemented; no DS or metadata pads yet. */
		pix->num_pads = MSM_VFE_PAD_NUM_RDI;'''
assert s.count(needle)==1;s=s.replace(needle,'''\t\tvfe_add_yuv(&pix->output[0], 3, 4, 0);
		vfe_add_params(&pix->output[1], 0);
		/* Keep shared pad indices; undeclared DS/stats reject formats. */
		vfe_set_pix(pix, 2);''');assert s!=old;ops.write_text(s)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--binary'])
(ROOT/'vfe175-params-candidate.patch').write_bytes(patch)
check=subprocess.run(['git','-C',str(TREE),'diff','--check'],capture_output=True);assert check.returncode==0,check.stderr.decode()
report=dict(stage=292,parent=git('rev-parse','HEAD'),branch=git('branch','--show-current'),
 patch_sha256=hashlib.sha256(patch).hexdigest(),files=['camss-vfe.c','camss-vfe-17x.c'],
 same_typed_params_uapi=True,full_and_params_outputs_only=True,no_stats_or_ds_format_advertised=True,
 no_dt_firmware_or_userspace_changes=True,not_compiled_or_deployed=True)
(ROOT/'params-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
