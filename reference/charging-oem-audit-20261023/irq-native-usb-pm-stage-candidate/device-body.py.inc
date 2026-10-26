    def __init__(self, request_raw):
        self.request_raw=request_raw;self.request=None;self.out=None;self.lock=None;self.mac_fd=None
        self.mac_baseline=None;self.events=[];self.uncertain=False

    def begin(self, request):
        self.request=request;self.identity(request);self.check_window(request)
        root=Path(ROOT)/request['transaction_id'];info=root.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o700 and not root.is_symlink(),'owned transaction directory')
        need(Path(__file__).resolve()==root/'stage-worker.py' and sha(Path(__file__).read_bytes())==request['worker_sha256'],'actual worker source/path')
        self.lock_existing(False);self.board_client();self.open_mac();self.verify_carriers()
        out=root/'device-stage';out.mkdir(mode=0o700,exist_ok=False);self.out=out
        self.write_new(self.out/'request-private.json',self.request_raw)
        self.log('process-private.json',dict(transaction_id=request['transaction_id'],boot_id=request['identity']['boot_id'],
                 pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                 argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x]))
        self.check_window(request)

    def notes_match(self,manager,old,backups=False):
        for name,entry in old['modules'].items():
            need(self.module_state(name)=='live','original live module retained')
            path=self.out/(Path(entry['target']).name+'.before') if backups and entry['target'] in ORDER else Path(entry['target'])
            manager['loaded_matches'](path,name.replace('-','_'))
            need(sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes())==NOTES[name],'original resident note')

    def manager_command(self,manager,meta,action):
        need(action=='stop','only the original synchronous INHIBIT action exists')
        return super().manager_command(manager,meta,action)

    def event(self,value):
        self.events.append(value)
        if self.out is not None:
            with (self.out/'events-private.jsonl').open('ab') as stream:
                stream.write((json.dumps(value)+'\n').encode());stream.flush();os.fsync(stream.fileno())

    def write_new(self,path,raw):
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o600);os.fsync(stream.fileno())
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def log(self,name,value):
        if self.out is not None:self.write_new(self.out/name,encode(value))

    def backup(self,files,before):
        for name,(raw,mode) in files.items():
            need(mode==0o600,'exact original mode');self.write_new(self.out/(Path(name).name+'.before'),raw)
        self.log('before-private.json',before)
        self.log('files-before-private.json',{name:dict(sha256=sha(raw),mode='0600',bytes=len(raw)) for name,(raw,_) in files.items()})

    def replace(self,name,raw,restore=False):
        need(name in ORDER and sha(raw)==(OLD_FILES if restore else NEW_FILES)[name],'only exact fixed two-file bytes')
        current,mode=self.read_owned(name)
        need(mode==0o600 and sha(current) in (OLD_FILES[name],NEW_FILES[name]),'known protected old/new disk object')
        if restore and current==raw:
            self.event(dict(step='restore-already-original',target=name,sha256=sha(current)));return
        transaction=self.request['transaction_id']+('-restore' if restore else '')
        atomic_replace(name,raw,transaction,sha(current),self.event)

    def finish(self,result):
        if self.out is None:return
        final={}
        for name in ORDER:
            try:
                raw,mode=self.read_owned(name);digest=sha(raw)
                final[name]=dict(sha256=digest,mode=oct(mode),classification='old' if mode==0o600 and digest==OLD_FILES[name] else 'new' if mode==0o600 and digest==NEW_FILES[name] else 'unexpected')
            except BaseException as error:final[name]=dict(error=detail(error),classification='unknown')
        result['final_files']=final
        temporary={}
        for name in ORDER:
            for suffix in ('','-restore'):
                path=Path(name).with_name('.'+Path(name).name+'.'+self.request['transaction_id']+suffix+'.next')
                try:
                    raw,mode=read_owned(path);temporary[str(path)]=dict(state='retained',sha256=sha(raw),bytes=len(raw),mode=oct(mode))
                except FileNotFoundError:temporary[str(path)]=dict(state='absent')
                except BaseException as error:temporary[str(path)]=dict(state='unknown',error=detail(error))
        result['temporary_files']=temporary
        labels={row['classification'] for row in final.values()}
        result['disk_state']='all_new_fsynced' if labels=={'new'} and result['staged'] else 'all_old' if labels=={'old'} else 'partial_known' if labels<={'old','new'} else 'unknown_inspect_before_boot'
        if result['staged'] and result['disk_state']!='all_new_fsynced':result.update(staged=False,phase='failed',status='final_readback_changed')
        if result['staged'] and any(row['state']!='absent' for row in temporary.values()):result.update(staged=False,phase='failed',status='temporary_retained_or_unknown')
        self.log('events-private.json',self.events)

    def publish(self,result):
        if self.out is not None:self.log('result.json',result)
