"""Runtime helpers appended to the proven package installation worker."""
def driver_notes(kind):
 for item in proof['driver_pair']:
  assert sha('/sys/module/'+item['module']+'/notes/.note.gnu.build-id')==item[kind+'_note_sha256']
  if kind=='new':assert sha(item['target'])==item['new_sha256']
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
 assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
 for n in ['test_cc_mode','test_gamma_mode','test_ltm_mode','test_chain_mode']:
  assert not Path('/sys/module/camss_icp_a5_m2m/parameters',n).exists()

def unload_pair():
 if (dev/'m2m_status').exists():idle();owner_zero()
 for name in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',name).exists():run(['rmmod',name],'unload-'+name,timeout=20)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()

def replace_pair(kind):
 for i,item in enumerate(proof['driver_pair']):
  source=root/item['payload'] if kind=='new' else root/'backup'/('module-'+str(i)+'.ko')
  assert sha(source)==item[kind+'_sha256']
  target=Path(item['target']);temporary=target.with_name(target.name+'.k420-tmp')
  assert not temporary.exists()
  with temporary.open('xb') as f:f.write(source.read_bytes());f.flush();os.fsync(f.fileno())
  temporary.chmod(0o644);os.replace(temporary,target)
  fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 run(['depmod','-a',os.uname().release],'depmod-'+kind,timeout=30)

def load_pair(kind):
 run(['modprobe','qcom_camss'],'load-pair-'+kind,timeout=30)
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp'
 driver_notes(kind);idle();owner_zero()

