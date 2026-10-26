"""Test the actual metadata link validator, including malformed links and sink errors."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
s=(TREE/'drivers/media/platform/qcom/camss/camss-video.c').read_text();start=s.index('static int video_meta_out_link_validate(');fn=s[start:s.index('\n}',start)+2]
prelude=r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <linux/media-bus-format.h>
#include <linux/v4l2-subdev.h>
struct media_entity {unsigned int type;};
struct media_pad {struct media_entity *entity;unsigned int index;};
struct media_link {struct media_pad *source,*sink;};
struct video_device {struct media_entity entity;};
struct camss_video {struct video_device vdev;struct media_pad pad;unsigned int type;};
struct v4l2_subdev {struct media_entity entity;};
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define is_media_entity_v4l2_video_device(e) ((e)->type==1)
#define is_media_entity_v4l2_subdev(e) ((e)->type==2)
#define media_entity_to_video_device(e) container_of(e,struct video_device,entity)
#define media_entity_to_v4l2_subdev(e) container_of(e,struct v4l2_subdev,entity)
static unsigned int calls,last_pad,last_which,code=MEDIA_BUS_FMT_METADATA_FIXED;static int result;
static int get_fmt(struct v4l2_subdev *sd,void *state,struct v4l2_subdev_format *f){assert(sd&&sd->entity.type==2&&!state);calls++;last_pad=f->pad;last_which=f->which;f->format.code=code;return result;}
#define v4l2_subdev_call(sd,kind,op,state,f) get_fmt(sd,state,f)
'''
tests=r'''
int main(void){
 struct camss_video video={.vdev.entity.type=1,.type=V4L2_BUF_TYPE_META_OUTPUT};video.pad.entity=&video.vdev.entity;
 struct v4l2_subdev sd={.entity.type=2};struct media_pad sink={.entity=&sd.entity,.index=5};struct media_link link={&video.pad,&sink};
 assert(video_meta_out_link_validate(&link)==0&&calls==1&&last_pad==5&&last_which==V4L2_SUBDEV_FORMAT_ACTIVE);
 result=-EINVAL;assert(video_meta_out_link_validate(&link)==-EINVAL);result=-EIO;assert(video_meta_out_link_validate(&link)==-EIO);result=0;
 code=MEDIA_BUS_FMT_SRGGB10_1X10;assert(video_meta_out_link_validate(&link)==-EPIPE);code=MEDIA_BUS_FMT_METADATA_FIXED;
 unsigned int before=calls;video.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;assert(video_meta_out_link_validate(&link)==-EPIPE&&calls==before);video.type=V4L2_BUF_TYPE_META_OUTPUT;
 struct media_pad other=video.pad;link.source=&other;assert(video_meta_out_link_validate(&link)==-EPIPE&&calls==before);link.source=&video.pad;
 sd.entity.type=1;assert(video_meta_out_link_validate(&link)==-EPIPE&&calls==before);sd.entity.type=2;
 video.vdev.entity.type=2;assert(video_meta_out_link_validate(&link)==-EPIPE&&calls==before);video.vdev.entity.type=1;
 assert(video_meta_out_link_validate(&link)==0);
 puts("PASS: actual metadata output link validation, fixed format, source ownership and sink failure propagation");return 0;
}
'''
p=host.PRIVATE/'metadata-link-tests-private.c';p.write_text(prelude+fn+tests);binary=p.with_suffix('')
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=20);(host.PRIVATE/'metadata-link-tests-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
report=dict(stage=292,actual_function=True,asan_ubsan=True,source_ownership_checked=True,only_fixed_metadata_accepted=True,sink_errors_propagated=True,output=q.stdout.decode().strip(),harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),not_deployed=True)
(ROOT/'metadata-link-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
