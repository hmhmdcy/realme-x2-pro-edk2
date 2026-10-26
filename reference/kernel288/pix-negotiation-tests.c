
static void capture(struct camss_video *video,u32 width,u32 height)
{
 struct v4l2_format f={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 f.fmt.pix_mp.width=width;f.fmt.pix_mp.height=height;f.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV21;
 assert(!__video_try_fmt(video,&f));
 struct v4l2_pix_format_mplane *p=&f.fmt.pix_mp;
 assert(p->pixelformat==V4L2_PIX_FMT_NV12 && p->num_planes==1);
 assert(p->width>=16 && p->width<=4096 && !(p->width%16));
 assert(p->height>=4 && p->height<=4096 && !(p->height%2));
 assert(p->plane_fmt[0].bytesperline==p->width);
 assert(p->plane_fmt[0].sizeimage==p->width*p->height*3/2);
 video->active_fmt=f;
}

int main(void)
{
 struct resources res={.line_num=4,.formats_pix_out=&vfe_formats_pix_out_175,
  .pix_sink_frame_sizes=&vfe_frame_sizes_pix_sink_175,.pix_frame_sizes=&vfe_frame_sizes_pix_175,.pix_no_crop=true};
 struct platform platform={.version=CAMSS_8150};struct camss camss={.res=&platform};
 struct vfe_device v={.res=&res,.camss=&camss};struct device dev={0};
 for(unsigned int i=0;i<4;i++){
  v.line[i].owner=&v;v.line[i].num_pads=2;v.line[i].num_outputs=1;
  v.line[i].output[0].line=&v.line[i];v.line[i].output[0].wm_num=1;
  v.line[i].output[0].wm[0].bus_client=i;
 }
 vfe_subdev_init_175(&dev,&v);assert(base_init_calls==1);
 struct vfe_line *l=&v.line[3];struct vfe_output *o=&l->output[0];
 assert(l->is_pix && l->num_pads==2 && l->num_outputs==1 && o->wm_num==2);
 assert(o->pad==1 && o->comp_group==0 && o->wm[0].bus_client==3 && o->wm[0].plane==0);
 assert(o->wm[1].bus_client==4 && o->wm[1].plane==1);
 assert(v.video_ops==vfe_video_ops_175 && v.isr_ops.comp_done==vfe_175_comp_done);
 for(unsigned int i=0;i<3;i++)assert(!v.line[i].is_pix && v.line[i].output[0].wm[0].bus_client==i);
 l->formats=vfe_formats_pix_175.formats;l->nformats=vfe_formats_pix_175.nformats;
 assert(l->nformats==16);
 struct camss_video *video=&o->video_out;
 video->formats=vfe_formats_pix_out_175.formats;video->nformats=1;video->bpl_alignment=16;video->frame_sizes=res.pix_frame_sizes;video->type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
 struct file file={.private_data=video};struct v4l2_fmtdesc fd={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 assert(!video_enum_fmt(&file,NULL,&fd) && fd.pixelformat==V4L2_PIX_FMT_NV12);
 fd.index=1;assert(video_enum_fmt(&file,NULL,&fd)==-EINVAL);
 fd.index=0;fd.mbus_code=MEDIA_BUS_FMT_SRGGB10_1X10;assert(video_enum_fmt(&file,NULL,&fd)==-EINVAL);
 fd.mbus_code=MEDIA_BUS_FMT_UYVY8_1_5X8;assert(!video_enum_fmt(&file,NULL,&fd));
 struct v4l2_frmsizeenum size={.pixel_format=V4L2_PIX_FMT_NV12};
 assert(!video_enum_framesizes(&file,NULL,&size) && size.type==V4L2_FRMSIZE_TYPE_STEPWISE);
 assert(!memcmp(&size.stepwise,&vfe_frame_sizes_pix_175,sizeof(size.stepwise)));
 size.pixel_format=V4L2_PIX_FMT_NV21;assert(video_enum_framesizes(&file,NULL,&size)==-EINVAL);
 const u32 other[]={0,1,3,4095,4096,4097,65535,UINT32_MAX};
 for(u32 n=0;n<65536;n++)for(unsigned int j=0;j<ARRAY_SIZE(other);j++)capture(video,n,other[j]);
 struct v4l2_subdev sd={.priv=l};assert(!vfe_init_formats(&sd,NULL));
 assert(l->fmt[0].code==MEDIA_BUS_FMT_SBGGR8_1X8 && l->fmt[1].code==MEDIA_BUS_FMT_UYVY8_1_5X8);
 const u32 dims[][2]={{16,4},{640,480},{1920,1080},{2320,1744},{4080,3072},{4608,3456},{8190,8190},{1,1},{8191,8191}};
 for(unsigned int c=0;c<16;c++)for(unsigned int d=0;d<ARRAY_SIZE(dims);d++){
  struct v4l2_subdev_format f={.pad=0,.which=V4L2_SUBDEV_FORMAT_ACTIVE,.format={.code=l->formats[c].code,.width=dims[d][0],.height=dims[d][1]}};
  assert(!vfe_set_format(&sd,NULL,&f));assert(l->fmt[0].code==l->formats[c].code);
  assert(!(l->fmt[0].width&1) && !(l->fmt[0].height&1));
  assert(l->compose.width<=l->fmt[0].width && l->compose.height<=l->fmt[0].height);
  assert(!l->crop.left && !l->crop.top && !memcmp(&l->crop,&l->compose,sizeof(l->crop)));
  struct v4l2_subdev_mbus_code_enum e={.pad=0,.which=V4L2_SUBDEV_FORMAT_ACTIVE,.index=c};
  assert(!vfe_enum_mbus_code(&sd,NULL,&e) && e.code==l->formats[c].code);
  e.index=16;assert(vfe_enum_mbus_code(&sd,NULL,&e)==-EINVAL);
  e.pad=1;e.index=0;assert(!vfe_enum_mbus_code(&sd,NULL,&e) && e.code==MEDIA_BUS_FMT_UYVY8_1_5X8);
  e.index=1;assert(vfe_enum_mbus_code(&sd,NULL,&e)==-EINVAL);
  assert(!vfe_src_pad_code(l,l->formats[c].code,1,0));
  struct v4l2_subdev_selection sel={.pad=0,.which=V4L2_SUBDEV_FORMAT_ACTIVE,.target=V4L2_SEL_TGT_COMPOSE,.r={.left=8,.top=10,.width=639,.height=479}};
  assert(!vfe_set_selection(&sd,NULL,&sel));assert(!sel.r.left && !sel.r.top);
  sel.pad=1;sel.target=V4L2_SEL_TGT_CROP;sel.r=(struct v4l2_rect){.left=5,.top=7,.width=17,.height=19};
  assert(!vfe_set_selection(&sd,NULL,&sel) && !memcmp(&sel.r,&l->compose,sizeof(sel.r)));
  struct v4l2_subdev_selection get={.pad=1,.target=V4L2_SEL_TGT_CROP,.which=V4L2_SUBDEV_FORMAT_ACTIVE};
  assert(!vfe_get_selection(&sd,NULL,&get) && !memcmp(&get.r,&l->compose,sizeof(get.r)));
  capture(video,l->fmt[1].width,l->fmt[1].height);
  assert(!vfe_175_validate_output(o));
  struct vfe_175_mnds_config scale;assert(!vfe_175_mnds_from_line(l,&scale));
  assert(scale.input_width==l->fmt[0].width && scale.output_width==l->fmt[1].width);
 }
 struct v4l2_mbus_framefmt active[2];memcpy(active,l->fmt,sizeof(active));
 struct v4l2_rect active_crop=l->crop,active_compose=l->compose;
 struct v4l2_subdev_state state={0};struct v4l2_subdev_fh fh={.state=&state};
 assert(!vfe_init_formats(&sd,&fh));assert(state.fmt[1].code==MEDIA_BUS_FMT_UYVY8_1_5X8);
 assert(!memcmp(active,l->fmt,sizeof(active)) && !memcmp(&active_crop,&l->crop,sizeof(active_crop)) && !memcmp(&active_compose,&l->compose,sizeof(active_compose)));
 res.formats_pix_out=NULL;res.pix_sink_frame_sizes=NULL;res.pix_frame_sizes=NULL;res.pix_no_crop=false;
 l->is_pix=false;assert(vfe_src_pad_code(l,MEDIA_BUS_FMT_SRGGB10_1X10,0,0)==MEDIA_BUS_FMT_SRGGB10_1X10);
 assert(vfe_src_pad_code(l,MEDIA_BUS_FMT_SRGGB10_1X10,1,0)==0);
 l->is_pix=true;assert(vfe_src_pad_code(l,MEDIA_BUS_FMT_SRGGB10_1X10,0,MEDIA_BUS_FMT_UYVY8_1X16)==MEDIA_BUS_FMT_UYVY8_1X16);
 struct camss_video legacy=*video;legacy.frame_sizes=NULL;
 struct file oldfile={.private_data=&legacy};size=(struct v4l2_frmsizeenum){.pixel_format=V4L2_PIX_FMT_NV12};
 assert(!video_enum_framesizes(&oldfile,NULL,&size) && size.type==V4L2_FRMSIZE_TYPE_CONTINUOUS && size.stepwise.max_width==8191);
 struct v4l2_format oldformat={0};oldformat.fmt.pix_mp=(struct v4l2_pix_format_mplane){.width=13,.height=7,.pixelformat=V4L2_PIX_FMT_NV12};
 assert(!__video_try_fmt(&legacy,&oldformat) && oldformat.fmt.pix_mp.width==13 && oldformat.fmt.pix_mp.height==7);
 puts("PASS: actual PIX descriptors, Bayer-to-NV12 negotiation, selection, TRY isolation, capture layout, MNDS/DMA acceptance and legacy/RDI behavior");
 return 0;
}
