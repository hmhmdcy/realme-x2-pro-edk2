"""Exercise the actual new AArch64 DSO, including one-time LSC parameters."""
from pathlib import Path
import json,shutil,subprocess,yaml,sys
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera321-lsc-built/src/libcamera-v0.7.2'
stage=SDK/'private/camss321-contract';stage.mkdir(exist_ok=True)
s=(HERE.parent/'kernel313/ipa-contract.cpp').read_text()
s=s.replace('assert(argc==3||argc==4);','assert(argc==3||argc==4);\n const bool lsc=argc==4 && std::string(argv[3])=="lsc";')
needle='assert(!ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration));'
s=s.replace(needle,'''if(argc==4 && std::string(argv[3])=="reject-lsc") {
 assert(ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration)==-EINVAL);
 std::cout<<"LSC_REJECT_PASS"<<std::endl;return 0;
 }
 '''+needle,1)
s=s.replace('assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes==56);','''assert(!ipa->prepareParameters(1,1,0,&bytes)&&bytes==(lsc?1848:56));
 if(lsc) {
  const auto *mesh=reinterpret_cast<const camss_params_lsc*>(parameters+56);
  assert(mesh->header.type==CAMSS_PARAMS_LSC && mesh->header.size==sizeof(*mesh) && mesh->header.flags==V4L2_ISP_PARAMS_FL_BLOCK_ENABLE);
  assert(mesh->cell_width==52 && mesh->cell_height==52 && mesh->x_start==8 && mesh->y_start==6 && mesh->subdivision==1);
  for(unsigned y=0;y<13;y++)for(unsigned x=0;x<17;x++) {
   double sx=(4+(int(x*52)-8)*2)/1639.0*16;
   double sy=(4+(int(y*52)-6)*2)/1231.0*12;
   std::array<double,4> expected={2*(1.25+.01*sx+.02*sy),1.25+.0175*sx+.01*sy,1.25+.0175*sx+.01*sy,1.5*(2.25+.04*sx+.015*sy)};
   for(unsigned c=0;c<4;c++)assert(std::abs(int(mesh->gains[c][y*17+x])-int(std::lround(expected[c]*1024)))<=1);
  }
  for(auto value:mesh->_pad)assert(!value);
  std::cout<<"LSC_PARAMETERS_PASS calibrated affine mesh and ABI"<<std::endl;
 }''')
for name in ['first','manual','update']:
 needle='assert(!ipa->prepareParameters(1,1,'+name+'.revision,&bytes));'
 s=s.replace(needle,needle.replace('));',') && bytes==56);'))
(HERE/'ipa-contract.cpp').write_text(s);(stage/'ipa-contract.cpp').write_text(s)
profile=yaml.safe_load((HERE.parent/'kernel313/imx319.yaml').read_text())
(stage/'legacy.yaml').write_text(yaml.safe_dump(profile,sort_keys=False))
lsc=dict(source_span=[1639.,1231.],first_quad=[4.,4.],quad_step=[2.,2.],gains={},golden={},unit={})
for c,(name,base,dx,dy,factor) in enumerate([('r',1.25,.01,.02,2),('gr',1.5,.02,.01,1),('gb',2,.03,.02,.5),('b',2.25,.04,.015,1.5)]):
 lsc['gains'][name]=[base+x*dx+y*dy for y in range(13) for x in range(17)]
 lsc['golden'][name]=[100.*factor]*221;lsc['unit'][name]=[100.]*221
profile['modes'][0]['lens_shading']=lsc
(stage/'lsc.yaml').write_text(yaml.safe_dump(profile,sort_keys=False))
lsc['enabled']=False;(stage/'disabled.yaml').write_text(yaml.safe_dump(profile,sort_keys=False))
lsc['enabled']=True;lsc['unit']['b'][52]=0.;(stage/'invalid.yaml').write_text(yaml.safe_dump(profile,sort_keys=False))
args=['chroot',str(SDK),'g++','-std=c++20','-O0','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include',
 '/private/camss321-contract/ipa-contract.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-ldl','-o','/private/camss321-contract/contract']
q=subprocess.run(args,capture_output=True);(host.PRIVATE/'contract-build.log').write_bytes(q.stdout+q.stderr)
assert not q.returncode,q.stderr.decode()
runs=[]
previous=HERE/'ipa-contract-validation.json'
retained={r['case']:r for r in json.loads(previous.read_text())['runs']} if previous.exists() else {}
for name,extra,marker in [('legacy',[],'AWB_CONTRACT_PASS'),('lsc',['lsc'],'LSC_PARAMETERS_PASS'),('disabled',[],'AWB_CONTRACT_PASS'),('invalid',['reject-lsc'],'LSC_REJECT_PASS')]:
 if len(sys.argv)>1 and name not in sys.argv[1:]:
  runs.append(retained[name]);continue
 q=subprocess.run(['chroot',str(SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base','/private/camss321-contract/contract',TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss321-contract/'+name+'.yaml',*extra],capture_output=True,timeout=70)
 (host.PRIVATE/('contract-'+name+'.log')).write_bytes(q.stdout+q.stderr)
 runs.append(dict(case=name,exit_code=q.returncode,passed=q.returncode==0 and marker.encode() in q.stdout))
report=dict(stage=321,actual_aarch64_ipa_dso=True,runs=runs,passed=all(r['passed'] for r in runs),installed=False)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if not report['passed']:print(q.stderr.decode()[-2500:]);raise SystemExit(1)
