# Appended to the existing service save/restore helpers.
meta=json.loads((root/'manifest.json').read_text());dev=Path('/sys/bus/platform/devices/ac10000.icp')
items={};started={};client=None;collector=None;stopped=False;failure=None;verified=False;captures={}
anchor=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines()[-1]
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def released():return not any(core()[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
def idle():
 wait_idle();assert released() and not any(m2m()[k] for k in ['users','running','fatal','pinned','orphans']);return m2m()
def unchanged():
 assert all(sha(n)==h for n,h in meta['normal_files'].items())
 assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
def owner_zero():
 end=time.monotonic()+5
 while m2m()['owner_refs']:assert time.monotonic()<end;time.sleep(.02)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
 assert int(Path('/proc/sys/kernel/tainted').read_text())==512;unchanged()
 for n,h in meta['payload_sha256'].items():assert sha(root/n)==h
 items=services();(root/'services-private.json').write_text(json.dumps(items)+'\n');stopped=True;stop_services(items);state['before']=idle();owner_zero()
 with (root/'collector.log').open('xb') as output:
  collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);end=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<end;time.sleep(.01)
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 for item in meta['captures']:
  name=item['name'];folder=root/name;folder.mkdir();before=idle();owner_zero()
  env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(folder))
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(item['profile']+'-s5kgw1-private.yaml')))
  if item.get('isolated'):env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
  args=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),'s5kgw1','/dev/'+nodes[0].name,'4608x3456',str(item['pattern'])]
  with (root/(name+'.log')).open('xb') as output:
   client=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True);save('capture-'+name,client_pid=client.pid)
   try:code=client.wait(timeout=55)
   except subprocess.TimeoutExpired:
    os.killpg(client.pid,signal.SIGTERM)
    try:client.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(client.pid,signal.SIGKILL);client.wait(timeout=5)
    raise
  text=(root/(name+'.log')).read_text(errors='replace');assert code==0 and 'ADAPT_RESULT ' in text and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,name+' failed'
  after=idle();owner_zero();frames=text.count('ADAPT_FRAME ')
  assert after['completed']-before['completed']>=frames and not any(after[k] for k in ['failed','fatal','cancelled','first_error'])
  assert len(list(folder.glob('*.nv12')))==frames
  captures[name]=dict(frames=frames,ipe_completed=after['completed']-before['completed'],tone_prepares=text.count('IPE_TONE_PREPARE '),tone_receipts=text.count('IPE_TONE_RECEIPT '),passed=True)
  assert 'IPE_TONE_REJECT' not in text
  if item['profile']!='bypass':assert captures[name]['tone_prepares']>0 and captures[name]['tone_receipts']>0
 unchanged();verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  assert client is None or client.poll() is not None
  idle();unchanged();state['formal_files_verified_after']=True
  if stopped:restart(items,'restored',started);wait_idle()
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and not state['collector_result']['captured']
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 lines=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines();assert lines.count(anchor)==1
 logs=lines[lines.index(anchor)+1:];(root/'kernel-log-private.txt').write_text('\n'.join(logs)+'\n')
 faults=[l for l in logs if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',l)]
 state.update(failure=failure,captures=captures,formal420_unchanged=verified,new_fault_count=len(faults),taint=int(Path('/proc/sys/kernel/tainted').read_text()),after=m2m(),core_after=core(),services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 save('finished',terminal=True,passed=bool(verified and failure is None and not faults and state['taint']==512 and released() and all(len(v)==1 for v in state['services'].values())))
