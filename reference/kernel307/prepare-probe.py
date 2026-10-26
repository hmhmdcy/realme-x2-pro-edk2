"""Reuse the native optical probe, adding the RGB metadata block."""
from pathlib import Path
import shutil
import subprocess
import sys
import host

HERE = Path(__file__).resolve().parent
tele = len(sys.argv) > 1 and sys.argv[1] == 'tele'
TREE = Path('/home/cy122/x2pro-linux/camera307-rgb-kernel')
s = (HERE.parent / 'kernel298/samurai-scene.c').read_text()
s = s.replace('frame<126', 'frame<36')
# Existing parameter validation was already covered; this run measures new DMA.
a = s.index('static int reject_invalid_params(')
b = s.index('static int open_params(', a)
s = s[:a] + s[b:]
s = s.replace('reject_invalid_params()||', '')
s = s.replace('sizeof(struct params_envelope)+sizeof(struct camss_stats_bhist)',
              'sizeof(struct params_envelope)+CAMSS_STATS_MAX_PAYLOAD')
s = s.replace('e->data_size!=sizeof(*h)', 'e->data_size!=b.bytesused-sizeof(*e)')
needle = ' uint64_t sum=0,weighted=0;'
insert = r'''
 const struct camss_stats_awb_bg *bg=(const void*)(data+sizeof(*e)+sizeof(*h));
 const unsigned regions=bg->columns*bg->rows;
 if(bg->header.type!=CAMSS_STATS_AWB_BG||bg->header.flags||regions!=768||
    bg->header.size!=sizeof(*bg)+regions*sizeof(struct camss_stats_bg_region)||
    bg->header.size+sizeof(*h)!=e->data_size||bg->input_bits!=14||bg->high_threshold!=16383||
    bg->left+bg->columns*bg->region_width>1632||bg->top+bg->rows*bg->region_height>1224||
    (bg->left|bg->top|bg->region_width|bg->region_height)&1){errno=EPROTO;return -1;}
 uint64_t rgb_sum[4]={0},rgb_count[4]={0};
 unsigned maximum=bg->region_width*bg->region_height/4;
 for(unsigned i=0;i<regions;i++){
  const struct camss_stats_bg_region *r=&bg->regions[i];
  uint32_t sums[4]={r->r_sum,r->b_sum,r->gr_sum,r->gb_sum};
  uint16_t counts[4]={r->r_count,r->b_count,r->gr_count,r->gb_count};
  for(unsigned c=0;c<4;c++){
   if(counts[c]>maximum||sums[c]>(uint64_t)counts[c]*16383){errno=EPROTO;return -1;}
   rgb_sum[c]+=sums[c];rgb_count[c]+=counts[c];
  }
 }
 for(unsigned c=0;c<4;c++)if(!rgb_count[c]){errno=ENODATA;return -1;}
 printf("RGB_BG frame=%u sequence=%u grid=%ux%u offset=%u,%u region=%ux%u counts=%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 " means=%.6f,%.6f,%.6f,%.6f\n",
  frame,b.sequence,bg->columns,bg->rows,bg->left,bg->top,bg->region_width,bg->region_height,
  rgb_count[0],rgb_count[1],rgb_count[2],rgb_count[3],
  (double)rgb_sum[0]/rgb_count[0],(double)rgb_sum[1]/rgb_count[1],
  (double)rgb_sum[2]/rgb_count[2],(double)rgb_sum[3]/rgb_count[3]);
'''
assert s.count(needle) == 1
s = s.replace(needle, insert + needle)
if tele:
    for before,after in [
        ('1632','2104'),('1224','1560'),('816','1052'),('499392','820560'),
        ('imx319 ','s5k3m5 '),('MEDIA_BUS_FMT_SRGGB10_1X10','MEDIA_BUS_FMT_SGRBG10_1X10'),
        ('exposure.minimum>3000||exposure.maximum<3000','exposure.minimum>500||exposure.maximum<500'),
        ('gain.minimum>512||gain.maximum<768','gain.minimum>64||gain.maximum<128'),
        ('V4L2_CID_EXPOSURE,.value=3000','V4L2_CID_EXPOSURE,.value=500'),
        ('V4L2_CID_ANALOGUE_GAIN,.value=512','V4L2_CID_ANALOGUE_GAIN,.value=64'),
        ('V4L2_CID_ANALOGUE_GAIN,.value=768','V4L2_CID_ANALOGUE_GAIN,.value=128'),
        ('code=768','code=128'),
        ('gain_code=512,768 exposure=3000','gain_code=64,128 exposure=500'),
    ]:
        s=s.replace(before,after)
source = HERE / ('rgb-tele-probe.c' if tele else 'rgb-probe.c')
source.write_text(s)
headers = host.PRIVATE / 'uapi/linux'
headers.mkdir(parents=True, exist_ok=True)
shutil.copyfile(TREE / 'include/uapi/linux/qcom-camss-config.h', headers / 'qcom-camss-config.h')
(headers/'media').mkdir(exist_ok=True)
shutil.copyfile(TREE / 'include/uapi/linux/media/v4l2-isp.h', headers/'media/v4l2-isp.h')
cmd = ['aarch64-linux-gnu-gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
       '-Wno-misleading-indentation', '-D__counted_by(x)=', '-D__EXPORTED_HEADERS__',
       '-static', '-s', '-I'+str(headers.parent),
       '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',
       str(source), '-o', str(host.PRIVATE/('rgb-tele-probe' if tele else 'rgb-probe'))]
q = subprocess.run(cmd, capture_output=True)
(host.PRIVATE/'probe-build.log').write_bytes(q.stdout+q.stderr)
print(q.stderr.decode())
raise SystemExit(q.returncode)
