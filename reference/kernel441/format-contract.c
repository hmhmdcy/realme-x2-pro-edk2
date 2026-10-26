/* SPDX-License-Identifier: GPL-2.0-only */
int main(void)
{
	struct ipe_context ctx={0},before;
	struct file file={&ctx};
	struct v4l2_format output,capture;
	u32 sizes[][2]={{640,480},{1280,720},{1920,1080}};
	unsigned int negotiated=0,rejected=0;

	for (unsigned int i=0;i<3;i++) for (unsigned int pad=0;pad<=16;pad+=16) {
		memset(&output,0,sizeof(output));output.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
		output.fmt.pix_mp.width=sizes[i][0];output.fmt.pix_mp.height=sizes[i][1];
		output.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_QCOM_NV12_PD10;
		output.fmt.pix_mp.plane_fmt[0].bytesperline=sizes[i][0]+pad;
		assert(!set_format(&file,NULL,&output));assert(ctx.coarse && output.fmt.pix_mp.num_planes==2);
		assert(ctx.format.pixelformat==V4L2_PIX_FMT_NV12 && ctx.format.num_planes==1 && !ctx.format.plane_fmt[1].sizeimage);
		struct camss_a5_nv12_layout full={sizes[i][0],sizes[i][1],sizes[i][0]+pad,sizes[i][1],false};
		struct camss_a5_pd10_layout pd;assert(!camss_a5_ipe_pd10_quarter(&full,&pd));
		assert(output.fmt.pix_mp.plane_fmt[1].bytesperline==pd.stride && output.fmt.pix_mp.plane_fmt[1].sizeimage==pd.bytes);
		struct v4l2_pix_format_mplane paired;assert(!queue_format(&ctx,V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,&paired) && !memcmp(&paired,&output.fmt.pix_mp,sizeof(paired)));
		memset(&capture,0,sizeof(capture));capture.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;capture.fmt.pix_mp=ctx.format;
		assert(!set_format(&file,NULL,&capture));assert(capture.fmt.pix_mp.num_planes==1 && capture.fmt.pix_mp.plane_fmt[0].sizeimage==(sizes[i][0]+pad)*sizes[i][1]*3/2);
		before=ctx;
		for (unsigned int bad=0;bad<4;bad++) {
			struct v4l2_format altered=capture;
			switch(bad) {case 0:altered.fmt.pix_mp.width-=2;break;case 1:altered.fmt.pix_mp.height-=2;break;case 2:altered.fmt.pix_mp.plane_fmt[0].bytesperline+=2;break;case 3:altered.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV21;break;}
			assert(set_format(&file,NULL,&altered)==-EINVAL && !memcmp(&ctx,&before,sizeof(ctx)));rejected++;
		}
		negotiated++;
	}
	before=ctx;
	output.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;output.fmt.pix_mp.width=3840;output.fmt.pix_mp.height=2160;output.fmt.pix_mp.plane_fmt[0].bytesperline=3840;output.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_QCOM_NV12_PD10;
	assert(set_format(&file,NULL,&output)==-EOPNOTSUPP && !memcmp(&ctx,&before,sizeof(ctx)));rejected++;
	output.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;assert(set_format(&file,NULL,&output)==-EINVAL && !memcmp(&ctx,&before,sizeof(ctx)));rejected++;
	busy=true;output=capture;assert(set_format(&file,NULL,&output)==-EBUSY && !memcmp(&ctx,&before,sizeof(ctx)));busy=false;
	output.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;output.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12;
	assert(!set_format(&file,NULL,&output) && !ctx.coarse && ctx.format.num_planes==1);
	printf("FORMAT_CONTRACT negotiated=%u rejected=%u legacy=1 busy=1 result=0\n",negotiated,rejected);
	return 0;
}
