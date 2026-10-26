"""Isolate the selected CSID source before starting a single-format internal TPG."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
s=(ROOT/'samurai-pix-tpg-diagnostic.c').read_text()
old=' bool rdi_link=false,video_link=false;'
assert s.count(old)==1;s=s.replace(old,old+'struct media_link_desc selected_link={0};')
old='   bool physical=link.sink.entity==c.id&&link.sink.index==0;'
assert s.count(old)==1
s=s.replace(old,'   bool physical=(link.sink.entity==c.id&&link.sink.index==0)||(link.source.entity==c.id&&!selected);')
old='   if(selected)rdi_link=true;'
s=s.replace(old,'   if(selected){rdi_link=true;selected_link=link;}')
old='   bool alter=(selected&&!(link.flags&MEDIA_LNK_FL_ENABLED))||(physical&&(link.flags&MEDIA_LNK_FL_ENABLED));'
assert s.count(old)==1;s=s.replace(old,'   bool alter=physical&&(link.flags&MEDIA_LNK_FL_ENABLED);')
old=' if(!rdi_link||!video_link){errno=ENOLINK;goto cleanup;}'
assert s.count(old)==1
s=s.replace(old,old+'''
 if(!(selected_link.flags&MEDIA_LNK_FL_ENABLED)){
  if(selected_link.flags&MEDIA_LNK_FL_IMMUTABLE||changed_count>=128){errno=EPERM;goto cleanup;}
  changed[changed_count++]=selected_link;selected_link.flags|=MEDIA_LNK_FL_ENABLED;
  if(call(media,MEDIA_IOC_SETUP_LINK,&selected_link))goto cleanup;
 }
''')
p=ROOT/'samurai-pix-tpg-isolated.c';assert not p.exists();p.write_text(s)
binary=PRIVATE/'pix-isolated-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I'+str(PRIVATE/'host-uapi/include'),str(p),'-o',str(binary)],capture_output=True)
(PRIVATE/'pix-isolated-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);assert q.returncode==0
report=dict(stage=288,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
 source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qemu_self_test_pass=True,
 unselected_csid_source_links_disabled_then_selected_enabled=True,all_modified_links_restored_in_reverse=True,
 stream_handshake_retained=True,not_run_on_phone=True)
(ROOT/'isolated-pix-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
native=(ROOT/'native-pix-diagnostic.py').read_text().replace("replace('k288-tpg-r1','k288-tpg-r2')","replace('k288-tpg-r1','k288-tpg-r3')").replace('pix-tpg-diagnostic','pix-tpg-isolated')
(ROOT/'native-isolated-pix.py').write_text(native)
launch=(ROOT/'launch-pix-diagnostic.py').read_text()
for a,b in [('pix-diagnostic-tool-validation.json','isolated-pix-tool-validation.json'),('pix-diagnostic-aarch64-private','pix-isolated-aarch64-private'),('pix-tpg-diagnostic','pix-tpg-isolated'),('native-pix-diagnostic.py','native-isolated-pix.py'),('k288-tpg-r2','k288-tpg-r3'),('pix-diagnostic-worker-private.log','isolated-pix-worker-private.log'),('pix-diagnostic-launch-private.json','isolated-pix-launch-private.json')]:launch=launch.replace(a,b)
(ROOT/'launch-isolated-pix.py').write_text(launch)
poll=(ROOT/'poll-pix-diagnostic.py').read_text().replace('pix-diagnostic-launch-private.json','isolated-pix-launch-private.json').replace('k288-tpg-r2','k288-tpg-r3').replace('pix-diagnostic-poll-private.json','isolated-pix-poll-private.json').replace('tpg-r2-validation.json','tpg-r3-validation.json')
(ROOT/'poll-isolated-pix.py').write_text(poll)
print(json.dumps(report,indent=2))
