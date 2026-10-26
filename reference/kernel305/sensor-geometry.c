/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <linux/v4l2-subdev.h>

static int rectangle(int fd,unsigned int which,unsigned int target)
{
 struct v4l2_subdev_selection selection={.which=which,.pad=0,.target=target};
 if(ioctl(fd,VIDIOC_SUBDEV_G_SELECTION,&selection))return 1;
 if(selection.r.left||selection.r.top||selection.r.width!=4208||selection.r.height!=3120)return 2;
 return 0;
}
int main(int argc,char **argv)
{
 if(argc!=2)return 2;
 int fd=open(argv[1],O_RDWR|O_CLOEXEC);if(fd<0)return 3;
 struct v4l2_subdev_format before={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
 if(ioctl(fd,VIDIOC_SUBDEV_G_FMT,&before))return 4;
 if(before.format.width!=2104||before.format.height!=1560)return 5;
 const unsigned int targets[]={V4L2_SEL_TGT_NATIVE_SIZE,V4L2_SEL_TGT_CROP_BOUNDS,V4L2_SEL_TGT_CROP_DEFAULT,V4L2_SEL_TGT_CROP};
 unsigned int checked=0;
 for(unsigned int which=0;which<=1;which++){
  struct v4l2_subdev_format format=before;format.which=which;
  if(which==V4L2_SUBDEV_FORMAT_TRY&&ioctl(fd,VIDIOC_SUBDEV_S_FMT,&format))return 6;
  for(unsigned int n=0;n<4;n++){
   if(rectangle(fd,which,targets[n]))return 7;
   checked++;
  }
 }
 struct v4l2_subdev_selection bad={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=1,.target=V4L2_SEL_TGT_CROP};
 if(ioctl(fd,VIDIOC_SUBDEV_G_SELECTION,&bad)!=-1||errno!=EINVAL)return 8;
 bad.pad=0;bad.target=V4L2_SEL_TGT_COMPOSE;
 if(ioctl(fd,VIDIOC_SUBDEV_G_SELECTION,&bad)!=-1||errno!=EINVAL)return 9;
 struct v4l2_subdev_format after={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
 if(ioctl(fd,VIDIOC_SUBDEV_G_FMT,&after)||memcmp(&before.format,&after.format,sizeof(before.format)))return 10;
 close(fd);
 printf("{\"selection_checks\":%u,\"active_and_try\":true,\"bad_pad_target_rejected\":true,\"active_format_restored\":true,\"crop\":[0,0,4208,3120],\"output\":[2104,1560]}\n",checked);
 return 0;
}
