/* SPDX-License-Identifier: GPL-2.0-only */
int main(void)
{
	u8 stripe[8192], saved[8192], out[3816], before[3816];
	u32 used = 0xdeadbeef, bytes = 0xdeadbeef;
	struct camss_a5_ipe_io io = {
		.input = {640,480,640,480,false}, .output = {640,480,640,480,false},
		.output_port = 8 }, bad;
	struct camss_a5_ipe_ltm_geometry geo = { true,true,true }, test;
	struct camss_a5_ipe_frame frame = {
		.striping={0x6030000,4140}, .iq={0x6040000,8944},
		.scratch={0x6080000,71488}, .bl={0x6100000,524256},
		.input={0x20000000,460800}, .output={0x24000000,460800},
		.coarse={0x20800000,46080}, .striping_cpu=stripe,
		.required_scratch_bytes=71488, .required_bl_bytes=181024,
		.request_id=1, .max_cores=2, .target_time_ns=100000000,
	}, invalid;
	memset(stripe,0xa7,sizeof(stripe));memcpy(saved,stripe,sizeof(stripe));
	for (unsigned i=0;i<12;i++) {
		bad=io;test=geo;u32 cores=2,capacity=sizeof(stripe);
		switch(i) {
		case 0:bad.input.width=650;bad.output.width=650;bad.input.stride=650;bad.output.stride=650;break;
		case 1:bad.input.height=482;bad.output.height=482;bad.input.slice_height=482;bad.output.slice_height=482;break;
		case 2:bad.output_port=9;break;
		case 3:bad.input.uv_swap=bad.output.uv_swap=true;break;
		case 4:cores=3;break;
		case 5:test.image_processing=false;break;
		case 6:test.mask_filter=false;break;
		case 7:capacity=4139;break;
		case 8:bad.input.width=0xffffffff;break;
		case 9:bad.output.width=638;break;
		case 10:bad.input.stride=639;break;
		case 11:cores=0;break;
		}
		assert(camss_a5_ipe_encode_ltm_pd10_striping(stripe,capacity,&bad,cores,&test,&used)<0);
		assert(used==0xdeadbeef && !memcmp(stripe,saved,sizeof(stripe)));
	}
	assert(camss_a5_ipe_ltm_pd10_size(NULL,2,&geo,&bytes)==-EINVAL && bytes==0xdeadbeef);
	assert(camss_a5_ipe_encode_ltm_pd10_striping(NULL,sizeof(stripe),&io,2,&geo,&used)==-EINVAL);
	assert(camss_a5_ipe_encode_ltm_pd10_striping(stripe,sizeof(stripe),&io,2,&geo,NULL)==-EINVAL);
	assert(!camss_a5_ipe_ltm_pd10_size(&io,2,&geo,&bytes) && bytes==4140);
	assert(!camss_a5_ipe_encode_ltm_pd10_striping(stripe,sizeof(stripe),&io,2,&geo,&used) && used==4140);
	assert(!memcmp(stripe+used,saved+used,sizeof(stripe)-used));
	assert(get_unaligned_le32(stripe+20)==2);
	assert(!camss_a5_ipe_encode_ltm_pd10_striping(saved,sizeof(saved),&io,1,&geo,&bytes) && bytes==used && !memcmp(stripe,saved,used));
	assert(!camss_a5_ipe_encode_frame(out,sizeof(out),&io,&frame));
	assert(get_unaligned_le32(out+108)==frame.coarse.iova && get_unaligned_le32(out+112)==0);
	assert(fwrite(stripe,1,used,stdout)==used && fwrite(out,1,sizeof(out),stdout)==sizeof(out));
	for (unsigned i=0;i<12;i++) {
		invalid=frame;memset(out,0xa7,sizeof(out));memcpy(before,out,sizeof(out));
		switch(i) {
		case 0:invalid.coarse.iova=0;break;
		case 1:invalid.coarse.bytes--;break;
		case 2:invalid.coarse.bytes++;break;
		case 3:invalid.coarse.iova++;break;
		case 4:invalid.coarse.iova=0xfffff000;break;
		case 5:invalid.coarse.bytes=0;break;
		default: {
			struct camss_a5_ipe_buffer *b[]={&frame.striping,&frame.iq,&frame.scratch,&frame.bl,&frame.input,&frame.output};
			invalid.coarse.iova=b[i-6]->iova;break;
		}
		}
		assert(camss_a5_ipe_encode_frame(out,sizeof(out),&io,&invalid)==-EINVAL && !memcmp(out,before,sizeof(out)));
	}
	/* Without DC, the existing full-pass geometry remains byte-identical. */
	geo.data_collection=false;
	assert(!camss_a5_ipe_encode_ltm_pd10_striping(stripe,sizeof(stripe),&io,2,&geo,&used) && used==3516);
	assert(!camss_a5_ipe_encode_ltm_striping(saved,sizeof(saved),&io,2,&geo,&bytes) && bytes==used && !memcmp(stripe,saved,used));
	assert(fwrite(stripe,1,used,stdout)==used);
	return 0;
}
