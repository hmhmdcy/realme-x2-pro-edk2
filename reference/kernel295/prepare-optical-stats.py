"""Add the verified stats node to the unrun real-scene probe, retaining its first build."""
from pathlib import Path
import re,shutil
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel295')
assert not (P/'optical-launch-private.json').exists()
for a,b in [(ROOT/'samurai-optical.c',ROOT/'samurai-optical-image-only.c'),(ROOT/'optical-tool-validation.json',ROOT/'optical-image-only-tool-validation.json'),(P/'optical-aarch64-private',P/'optical-image-only-aarch64-private')]:
 assert not b.exists();shutil.copyfile(a,b)
s=(ROOT/'samurai-optical.c').read_text().replace('#include <linux/media.h>','#include <linux/media.h>\n#include <linux/qcom-camss-config.h>')
stats=(ROOT/'samurai-stats.c').read_text();start=stats.index('static int stats_fd=');end=stats.index('struct format_save {',start)
helpers=stats[start:end]
helpers=re.sub(r'static int stats_drain_stopped\(void\) \{.*?\n\}\n','',helpers,flags=re.S)
helpers=helpers.replace('frame/9','frame/6').replace('frame%9==8','frame%6==5')
helpers='struct params_envelope {uint32_t version,data_size;};\n'+helpers
s=s.replace('struct format_save {',helpers+'\nstruct format_save {',1)
s=s.replace('s={0},p={0};','s={0},p={0},statistics={0};')
s=s.replace('if(!strcmp(item.name,"msm_vfe0_video3"))capture=item;','if(!strcmp(item.name,"msm_vfe0_video3"))capture=item;\n   if(!strcmp(item.name,"msm_vfe0_stats"))statistics=item;')
s=s.replace('capture.id&&s.id)break;','capture.id&&s.id&&statistics.id)break;')
s=s.replace(' phase="streamon";',' phase="stats-open";if(stats_open(&statistics))goto cleanup;\n phase="streamon";',1)
s=s.replace('  last_sequence=buffer.sequence;last_time=timestamp;','  last_sequence=buffer.sequence;last_time=timestamp;\n  if(stats_dequeue(frame,argv[2]))goto cleanup;',1)
s=s.replace(' for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);',' if(stats_close()){perror("stats cleanup");result=1;}\n for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);',1)
assert 'statistics=item' in s and 'stats_drain_stopped' not in s
(ROOT/'samurai-optical.c').write_text(s)
p=ROOT/'native-optical.py';s=p.read_text();needle=" report['passed']=ret==0"
assert needle in s
s=s.replace(needle," report['statistics']=[dict((k,int(v,16) if k=='hash' else int(v)) for k,v in re.findall(r'(\\w+)=([0-9a-f]+)',line)) for line in text.splitlines() if line.startswith('STATS frame=')]\n report['statistics_frames']=len(report['statistics'])\n report['passed']=report['statistics_frames']==18 and ret==0")
compile(s,str(p),'exec');p.write_text(s)
s=(ROOT.parent/'kernel294/prepare-tools.py').read_text().split("s=(OLD/'native-wb-params.py')")[0]
s=s.replace('/kernel294','/kernel295').replace('stage=294','stage=295').replace('wrong-kernel-k294','wrong-kernel-k295').replace("['stats','optical']","['optical']")
exec(compile(s,'compile-optical-stats.py','exec'),{'__file__':__file__})
print('Compiled physical IMX319 image+BHIST exposure sweep; image-only first build retained and never run.')
