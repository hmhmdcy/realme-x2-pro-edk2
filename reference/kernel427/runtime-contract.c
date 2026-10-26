int main(void)
{
	u32 in[5];
	unsigned cases = 0;
	while (fread(in, sizeof(in), 1, stdin) == 1) {
		struct camss_pd10_layout layout, saved_layout = {1, 2, 3};
		struct vfe_device v = {};
		struct camss c = {};
		struct camss_res cr = {CAMSS_8150};
		struct vfe_res vr = {};
		struct vfe_line line = {.owner = &v, .is_pix = true};
		struct camss_buffer buffer = {.addr = {0x10000000, 0, 0}};
		struct camss_params_ife_ds4 params = {};
		struct v4l2_pix_format_mplane *full = &line.output[0].video_out.active_fmt.fmt.pix_mp;
		struct vfe_output *out = &line.output[3];
		struct v4l2_pix_format_mplane *pix = &out->video_out.active_fmt.fmt.pix_mp;
		u32 qw = ALIGN(in[0], 8) / 4, qh = ALIGN(in[1], 8) / 4, packed[18];

		memset(mmio, 0, sizeof(mmio));writes=0;c.res=&cr;v.camss=&c;v.res=&vr;v.base=mmio;
		assert(!camss_format_pd10_layout(qw, qh, &layout));
		assert(camss_format_pd10_layout(3, qh, &saved_layout) == -EINVAL && saved_layout.stride == 1 && saved_layout.slice_height == 2 && saved_layout.bytes == 3);
		out->line=&line;out->pad=MSM_VFE_PAD_SRC_DS4;out->wm_num=1;out->wm[0].bus_client=5;out->comp_group=1;
		full->width=in[0];full->height=in[1];pix->width=qw;pix->height=qh;pix->num_planes=1;pix->pixelformat=V4L2_PIX_FMT_QCOM_PD10_LOCAL;
		pix->plane_fmt[0].bytesperline=layout.stride;pix->plane_fmt[0].sizeimage=layout.bytes;
		assert(!vfe_175_ds4_validate_output(out) && !vfe_175_ds4_validate_buffer(out,&buffer));
		buffer.addr[0]=0xfffffff0;assert(vfe_175_ds4_validate_buffer(out,&buffer)==-ERANGE);
		buffer.addr[0]=0x10000004;assert(vfe_175_ds4_validate_buffer(out,&buffer)==-EINVAL);buffer.addr[0]=0x10000000;
		pix->plane_fmt[0].sizeimage--;assert(vfe_175_ds4_validate_output(out)==-EINVAL);pix->plane_fmt[0].sizeimage++;
		pix->plane_fmt[0].bytesperline+=16;assert(vfe_175_ds4_validate_output(out)==-EINVAL);pix->plane_fmt[0].bytesperline-=16;
		for(unsigned i=0;i<3;i++)params.coefficient[i]=in[i+2];
		assert(!vfe_175_ds4_validate(NULL,&params.header));
		params.reserved=1;assert(vfe_175_ds4_validate(NULL,&params.header)==-EINVAL);params.reserved=0;
		params.header.flags=1;assert(vfe_175_ds4_validate(NULL,&params.header)==-EINVAL);params.header.flags=0;
		vfe_175_ds4_params(&v,&line,&params.header);assert(v.pixel175.ds4_configured && !v.pixel175.ds4_running && !writes);
		mmio[0x4c/4]=0x80000018;mmio[0x200c/4]=0x18;mmio[0x2010/4]=0x18;mmio[0x2014/4]=0x80;
		vfe_175_ds4_start(&v,out);vfe_175_ds4_update(&v,out,&buffer);
		assert(v.pixel175.ds4_running && mmio[0x2708/4]==1 && mmio[0x2714/4]==buffer.addr[0]);
		for(unsigned i=0;i<4;i++)packed[i]=mmio[(0xd60+i*4)/4];
		packed[4]=mmio[0xd84/4];packed[5]=mmio[0xd88/4];packed[6]=mmio[0xda4/4];packed[7]=mmio[0xda8/4];
		packed[8]=mmio[0xd98/4];packed[9]=mmio[0xd9c/4];packed[10]=mmio[0xdb8/4];packed[11]=mmio[0xdbc/4];
		packed[12]=mmio[0x271c/4];packed[13]=mmio[0x2720/4];packed[14]=mmio[0x2728/4];packed[15]=mmio[0x2758/4];
		packed[16]=mmio[0xd8c/4];packed[17]=mmio[0xdac/4];
		assert(packed[15]==layout.bytes && mmio[0x4c/4]==0x80005518 && mmio[0x2014/4]==0xa0 && mmio[0x2010/4]==0x18);
		unsigned before=writes;vfe_175_ds4_params(&v,&line,&params.header);assert(writes==before+4);
		vfe_175_ds4_stop(&v,out);assert(!v.pixel175.ds4_running && !mmio[0x2708/4] && mmio[0x4c/4]==0x80000018 && mmio[0x2014/4]==0x80 && mmio[0x2010/4]==0x18);
		assert(!(mmio[0xd8c/4]&0xe00) && !(mmio[0xdac/4]&0xe00));
		assert(fwrite(packed,sizeof(packed),1,stdout)==1);cases++;
	}
	assert(cases);return 0;
}
