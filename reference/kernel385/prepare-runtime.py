"""Adapt the guarded transaction to declared image parameters."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel384'
for name in ['boot-worker.py','launch-boot.py','poll-boot.py','preflight.py','snapshot-collector.py','firmware-context-validation.json','check-worker.py']:
 s=(OLD/name).read_text().replace('stage=384','stage=385').replace('k384-boot-','k385-boot-').replace('Prepared384','Prepared385')
 if name=='boot-worker.py':
  a=" meta=json.loads((ROOT/'manifest.json').read_text())";assert a in s
  s=s.replace(a,a+"\n image_case=meta['image_test'];expected_frames=image_case['frames'];expected_image_bytes=image_case['width']*image_case['height']*3//2")
  a="'enable_frame=1'])";assert a in s
  s=s.replace(a,"'enable_frame=1',*['test_'+k+'='+str(int(image_case[k]) if k=='uv_swap' else image_case[k]) for k in ['width','height','port','cores','frames','uv_swap']]])")
  for key in ['image_frames','frames_completed','transfer_maps','transfer_unmaps']:
   s=s.replace("result.get('"+key+"')==1","result.get('"+key+"')==expected_frames")
  s=s.replace("result.get('image_bytes')==460800","result.get('image_bytes')==expected_image_bytes")
  s=s.replace("len(image)==460800","len(image)==expected_image_bytes")
  a=" observation['image_control_completion_passed']=frame";assert a in s
  s=s.replace(a," frame=bool(frame and len(result.get('frame_results',[]))==expected_frames and all(result.get('test_'+k)==image_case[k] for k in ['width','height','port','cores','frames','uv_swap']))\n"+a)
 if name=='launch-boot.py':
  a="root='/var/lib/samurai/k385-boot-'+run";assert a in s
  s=s.replace(a,a+"\ncase=sys.argv[2] if len(sys.argv)>2 else 'small';image=json.loads((HERE/'image-cases.json').read_text())[case]\npreflight=json.loads((HERE/'runtime-preflight-validation.json').read_text());assert preflight['passed'] and preflight['run']==run and preflight['image_case']==image")
  s=s.replace("['serializer','formats','transfer','worker','intree-build']","['diagnostic','worker','intree-build']")
  s=s.replace("manifest=dict(kernel_release=","manifest=dict(image_test=image,kernel_release=")
 if name=='poll-boot.py':
  s=s.replace("assert path.stat().st_size<=2*1024*1024","assert path.stat().st_size<=(64*1024*1024 if path.name=='ipe-output-private.nv12' else 2*1024*1024)")
  s=s.replace("timeout=25","timeout=90")
 if name=='preflight.py':
  s=s.replace('import ast,json,shlex','import ast,json,shlex,sys,re')
  s=s.replace("HERE=Path(__file__).resolve().parent","HERE=Path(__file__).resolve().parent\nrun=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\\d+',run)\ncase=sys.argv[2] if len(sys.argv)>2 else 'small';image=json.loads((HERE/'image-cases.json').read_text())[case]")
  s=s.replace('dict(snapshot_profile=profile)','dict(snapshot_profile=profile,image_test=image)')
  s=s.replace("dict(ROOT=Path('/fixture'),meta=","dict(ROOT=Path('/fixture'),image_case=image,meta=")
  a="assert args[5]=='enable_frame=1'";assert a in s
  s=s.replace(a,a+"\nassert args[6:]==['test_'+k+'='+str(int(image[k]) if k=='uv_swap' else image[k]) for k in ['width','height','port','cores','frames','uv_swap']]")
  s=s.replace("d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)","code=code.replace('/var/lib/samurai/k385-boot-r1','/var/lib/samurai/k385-boot-'+run)\nd=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)")
  s=s.replace("report=dict(stage=385,","report=dict(stage=385,run=run,image_case=image,")
 if name=='check-worker.py':
  s=s.replace('image_frames=1,frames_completed=1,transfer_maps=1,transfer_unmaps=1','image_frames=2,frames_completed=2,transfer_maps=2,transfer_unmaps=2')
  a=" (root/'collector-result.json').write_text";assert a in s
  s=s.replace(a," if case=='ready':initial.update(test_width=640,test_height=480,test_port=9,test_cores=2,test_frames=2,test_uv_swap=True,frame_results=[{},{}])\n"+a)
  a="scope=dict(ROOT=root,";assert a in s
  s=s.replace(a,"scope=dict(expected_frames=2,expected_image_bytes=460800,image_case=dict(width=640,height=480,port=9,cores=2,frames=2,uv_swap=True),ROOT=root,")
 (HERE/name).write_text(s)
print('Prepared declared variable-frame cases and per-transaction worker assertions.')
