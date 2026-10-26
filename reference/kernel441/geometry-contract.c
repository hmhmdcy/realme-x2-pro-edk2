/* SPDX-License-Identifier: GPL-2.0-only */
int main(void)
{
	u8 output[32768], before[32768], single[32768];
	u32 used, bytes, other;
	struct camss_a5_ipe_io io = {
		.input={1280,720,1280,720,false}, .output={1280,720,1280,720,false}, .output_port=8 }, bad;
	struct camss_a5_ipe_ltm_geometry ltm={true,true,true}, modified;

	memset(before,0xa7,sizeof(before));
	for (unsigned int i=0;i<20;i++) {
		bad=io;modified=ltm;u32 cores=1,capacity=sizeof(output);int expected=-EINVAL;
		switch(i) {
		case 0:bad.input.width=641;break;
		case 1:bad.input.height=721;break;
		case 2:bad.input.stride=1278;break;
		case 3:bad.output.stride=1278;break;
		case 4:bad.input.slice_height=718;break;
		case 5:bad.output.slice_height=719;break;
		case 6:bad.output.width=1278;break;
		case 7:bad.output.height=718;break;
		case 8:bad.input.width=8194;break;
		case 9:bad.input.height=8194;break;
		case 10:bad.input.width=0xffffffff;break;
		case 11:bad.input.uv_swap=bad.output.uv_swap=true;expected=-EOPNOTSUPP;break;
		case 12:bad.output_port=9;expected=-EOPNOTSUPP;break;
		case 13:cores=0;break;
		case 14:cores=3;break;
		case 15:modified.image_processing=false;expected=-EOPNOTSUPP;break;
		case 16:modified.mask_filter=false;expected=-EOPNOTSUPP;break;
		case 17:capacity=5387;expected=-ENOSPC;break;
		case 18:bad.input.height=0;break;
		case 19:bad.output.uv_swap=true;break;
		}
		memcpy(output,before,sizeof(output));used=0xdeadbeef;
		assert(camss_a5_ipe_encode_ltm_pd10_striping(output,capacity,&bad,cores,&modified,&used)==expected);
		assert(used==0xdeadbeef && !memcmp(output,before,sizeof(output)));
	}
	bytes=0xdeadbeef;
	assert(camss_a5_ipe_ltm_pd10_size(NULL,1,&ltm,&bytes)==-EINVAL && bytes==0xdeadbeef);
	assert(camss_a5_ipe_ltm_pd10_size(&io,1,NULL,&bytes)==-EINVAL && bytes==0xdeadbeef);
	assert(camss_a5_ipe_ltm_pd10_size(&io,1,&ltm,NULL)==-EINVAL);
	assert(camss_a5_ipe_encode_ltm_pd10_striping(NULL,sizeof(output),&io,1,&ltm,&bytes)==-EINVAL && bytes==0xdeadbeef);
	assert(camss_a5_ipe_encode_ltm_pd10_striping(output,sizeof(output),&io,1,NULL,&bytes)==-EINVAL && bytes==0xdeadbeef);
	assert(camss_a5_ipe_encode_ltm_pd10_striping(output,sizeof(output),&io,1,&ltm,NULL)==-EINVAL);
	for (unsigned int i=0;i<3;i++) for (unsigned int cores=1;cores<=2;cores++) {
		u32 width[]={640,1280,1920},height[]={480,720,1080};
		io=(struct camss_a5_ipe_io){.input={width[i],height[i],width[i],height[i],false},.output={width[i],height[i],width[i],height[i],false},.output_port=8};
		modified=ltm;modified.data_collection=false;
		assert(!camss_a5_ipe_encode_ltm_striping(single,sizeof(single),&io,cores,&modified,&other));
		memcpy(output,before,sizeof(output));
		assert(!camss_a5_ipe_ltm_pd10_size(&io,cores,&modified,&bytes) && bytes==other);
		assert(!camss_a5_ipe_encode_ltm_pd10_striping(output,sizeof(output),&io,cores,&modified,&used) && used==other);
		assert(!memcmp(output,single,used) && !memcmp(output+used,before+used,sizeof(output)-used));
	}
	puts("GEOMETRY_CONTRACT invalid=26 dc-off=6 result=0");
	return 0;
}
