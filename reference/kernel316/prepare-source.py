"""One-time preparation of product discovery/caps atop the tested315 handler."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel315'
TREE=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
assert not (HERE/'pipeline').exists()
shutil.copytree(OLD/'pipeline',HERE/'pipeline')
shutil.copytree(OLD/'framework',HERE/'framework')
for name in ['include/libcamera/internal/v4l2_subdevice.h','src/libcamera/v4l2_subdevice.cpp']:
 p=HERE/'framework'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(TREE/name,p)
p=HERE/'framework/include/libcamera/internal/v4l2_subdevice.h';s=p.read_text()
needle='\tint setSelection(const Stream &stream, unsigned int target,\n\t\t\t Rectangle *rect);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
 int setSelection(const Stream &stream, unsigned int target, Rectangle *rect, Whence whence);
 int setSelection(unsigned int pad, unsigned int target, Rectangle *rect, Whence whence)
 {
  return setSelection({pad,0},target,rect,whence);
 }
''');p.write_text(s)
p=HERE/'framework/src/libcamera/v4l2_subdevice.cpp';s=p.read_text()
a=s.index('int V4L2Subdevice::setSelection(');b=s.index('\n}',a)+2
old=s[a:b]
assert 'sel.which = V4L2_SUBDEV_FORMAT_ACTIVE;' in old
new=old.replace('Rectangle *rect)','Rectangle *rect, Whence whence)').replace('sel.which = V4L2_SUBDEV_FORMAT_ACTIVE;','sel.which = whence;')
original=old[:old.index('{')+1]+'\n\treturn setSelection(stream,target,rect,ActiveFormat);\n}'
s=s[:a]+original+'\n\n'+new+s[b:];p.write_text(s)
p=HERE/'pipeline/camss_vfe.cpp';s=p.read_text()
assert 'if (!enabled || std::strcmp(enabled, "1"))' in s
s=s.replace('/* Keep the installed RAW handler as the default while this backend is experimental. */','/* An explicit opt-out retains the generic simple handler for diagnostics. */').replace('if (!enabled || std::strcmp(enabled, "1"))','if (enabled && !std::strcmp(enabled, "0"))')
s=s.replace('pix_ = subdevs_.at(endpoint.pix).get();','pix_ = subdevs_.at(endpoint.pix).get();\n if (!pix_->caps().hasStreams()) return -ENOTSUP;')
s=s.replace('void restoreLinks();','void restoreLinks();\n StreamFormats streamFormats(bool raw);')
a=s.index('  const Size size = raw ? sensorFormat_.size :');b=s.index('\n  if (cfg.pixelFormat',a)
s=s[:a]+'''  Size size = sensorFormat_.size;
  if (!raw) {
   V4L2SubdeviceFormat trial = sensorFormat_;
   if (data_->pix_->setFormat(0,&trial,V4L2Subdevice::TryFormat)) return Invalid;
   Rectangle compose(cfg.size);
   if (data_->pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&compose,V4L2Subdevice::TryFormat)) return Invalid;
   size=compose.size();
  }'''+s[b:]
s=s.replace('  StreamConfiguration cfg;\n  if (role == StreamRole::Raw)', '  StreamConfiguration cfg(d->streamFormats(role==StreamRole::Raw));\n  if (role == StreamRole::Raw)')
addition='''
StreamFormats CamssVfeData::streamFormats(bool raw)
{
 std::map<PixelFormat,std::vector<SizeRange>> formats;
 const auto video=image_->formats();
 auto nv12=video.find(V4L2PixelFormat(V4L2_PIX_FMT_NV12));
 for (unsigned int code:sensor_->mbusCodes()) {
  BayerFormat bayer=BayerFormat::fromMbusCode(code);
  if (!bayer.isValid() || bayer.bitDepth!=10) continue;
  bayer.packing=BayerFormat::Packing::CSI2;
  for (const Size &size:sensor_->sizes(code)) {
   if (raw) {formats[bayer.toPixelFormat()].emplace_back(size);continue;}
   if (nv12==video.end()) continue;
   V4L2SubdeviceFormat trial{code,size,{}};
   if (pix_->setFormat(0,&trial,V4L2Subdevice::TryFormat)) continue;
   for (const SizeRange &range:nv12->second) {
    Rectangle minimum(range.min),maximum(range.max);
    if (pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&minimum,V4L2Subdevice::TryFormat) ||
        pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&maximum,V4L2Subdevice::TryFormat)) continue;
    formats[libcamera::formats::NV12].emplace_back(minimum.size(),maximum.size(),range.hStep,range.vStep);
   }
  }
 }
 return StreamFormats(formats);
}

'''
a=s.index('CameraConfiguration::Status CamssVfeConfiguration::validate()');s=s[:a]+addition+s[a:]
p.write_text(s)
print('Prepared316 capability selection, negotiated formats and TRY compose validation.')
