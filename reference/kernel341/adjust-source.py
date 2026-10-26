from pathlib import Path
import shutil
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
p=tree/'src/ipa/camss-vfe/lens_shading.cpp';s=p.read_text().replace('''\tLscGrid grid;
\tLscMesh source, resampled;
\tif (!lscGridForSize(input.width, input.height, &grid) ||
\t    readLensShadingMesh(tuning["gains"], &source))''',''' LscMesh source;
 if (readLensShadingMesh(tuning["gains"], &source))''');p.write_text(s);shutil.copyfile(p,HERE/'ipa'/p.name)
p=tree/'src/ipa/camss-vfe/camss.cpp';s=p.read_text().replace(' if(!ret)*state=result;return ret;',' if(!ret)*state=result;\n return ret;')
a='\t\tmetadata.set(controls::ColourGains, Span<const float, 2>(gains));'
b=a+'''
  if(context->second.lensShading)LOG(IPACamss,Info)<<"LSC_CONTEXT epoch="<<epoch<<" sof="<<sof<<" revision="<<context->second.revision
   <<" mesh-trace="<<lensShadingTrace(context->second.lensShading->parameters);
'''
assert a in s;s=s.replace(a,b);p.write_text(s);shutil.copyfile(p,HERE/'ipa'/p.name)
