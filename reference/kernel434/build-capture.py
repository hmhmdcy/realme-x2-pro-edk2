from pathlib import Path
import hashlib,importlib.util,json,re,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage434capture',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354';inc=P/'capture-includes';(inc/'linux/media').mkdir(parents=True,exist_ok=True)
for name in ['qcom-camss-config.h','media/v4l2-isp.h','media-bus-format.h']:shutil.copyfile(kernel/'include/uapi/linux'/name,inc/'linux'/name)
raw_header=inc/'linux/videodev2.h'
if raw_header.exists():raw_header.unlink()
definition=re.search(r'^#define\s+V4L2_META_FMT_QCOM_ISP_STATS\s+(.+)$',(kernel/'include/uapi/linux/videodev2.h').read_text(),re.M);assert definition
compat=inc/'local-formats.h';compat.write_text('#ifndef V4L2_META_FMT_QCOM_ISP_STATS\n#define V4L2_META_FMT_QCOM_ISP_STATS '+definition[1]+'\n#endif\n')
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-include',str(compat),'-I'+str(inc),str(HERE/'gtm-capture.c'),'-o',str(P/'gtm-capture')],capture_output=True);(P/'capture-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
base=(P.parent/'kernel428/params-s5kgw1-private.bin').read_bytes();assert len(base)==56;(P/'params-private.bin').write_bytes(base)
original=[(P.parent/'kernel432'/('sunny_s5kgw1-'+str(i)+'-adrc-lut-private.bin')).read_bytes() for i in [0,2]]
identity=struct.pack('<128I',*([4096,0]*64));half=struct.pack('<128I',*([2048,0]*64));luts=[identity,identity,half,original[0],original[1],original[0],original[0],identity,identity]
packets=[]
for i,lut in enumerate(luts):
 segments=[]
 for j in range(64):
  base,slope=struct.unpack_from('<II',lut,j*8);assert base<=0x3ffff and slope<=0x3ffffff;segments.append(struct.pack('<Ii',base,slope if slope<1<<25 else slope-(1<<26)))
 packet=struct.pack('<HHIQII',9,0,536,0x4340000000000001+i,int(i not in [0,7]),0)+b''.join(segments);assert len(packet)==536;packets.append(packet)
(P/'gtm-packets-private.bin').write_bytes(b''.join(packets))
r=dict(stage=434,source_sha256=hashlib.sha256((HERE/'gtm-capture.c').read_bytes()).hexdigest(),probe_sha256=hashlib.sha256((P/'gtm-capture').read_bytes()).hexdigest(),static_arm64=True,main_mode=[4608,3456],output=[640,480],pd10=[160,120],typed_gtm_packets=9,private_packets_bytes=9*536,pattern_packet_indices=list(range(9)),scene_packet_indices=[0,3,7],original_tmc11_gtm_luts_used=True,explicit_diagnostic_half_gain_not_factory_tuning=True,compiler_warnings=[],passed=True)
(HERE/'capture-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
