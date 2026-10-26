"""Resume only the Image phase after an intentional parallelism adjustment."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
prior=json.loads((P/'boot-build-state-private.json').read_text());assert prior['terminal'] and prior['phase']=='failed'
assert len(prior['phases'])==4 and all(x['exit']==0 for x in prior['phases'][:3]) and prior['phases'][3]['name']=='image-modules'
assert (P/'parallelism-adjustment-private.json').exists()
(P/'boot-before-resume-private.json').write_text(json.dumps(prior,indent=2)+'\n')
s=(HERE/'build-boot-kernel.py').read_text()
s=s.replace("assert sha(BUILD/'.config')=='b103243f1545f053913fc040cc77815729132fce6ccec1250e2d9918395f2715'", "assert 'CONFIG_LOCALVERSION=\"-rmx1931-samurai-k363\"' in (BUILD/'.config').read_text()")
a=s.index("marker=PRIVATE/");b=s.index('\ndef snapshot',a)
s=s[:a]+"marker=PRIVATE/'boot-build-state-private.json'\nbackup=PRIVATE/'previous-build-artifacts'\nassert backup.is_dir()\n"+s[b:]
s=s.replace('and not payload.exists()','and payload.is_dir()')
s=s.replace("subprocess.run(['cp','-a',str(original),str(payload)],check=True);assert snapshot(payload)==initial", "existing_input=snapshot(payload)\nassert {n for n in initial if initial[n]!=existing_input[n]}=={'lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']}")
s=s.replace("before=(BUILD/'.config').read_text()", "before=(backup/'.config').read_text()")
a=s.index('for key,value in ');b=s.index('\nepoch=',a);s=s[:a]+s[b:]
s=s.replace("'-j3'","'-j8'")
s=s.replace("phases=[];start_all=", "phases=json.loads((PRIVATE/'boot-before-resume-private.json').read_text())['phases'][:3];start_all=")
s=s.replace("('boot-'+name+'-private.log')", "('boot-'+name+'-resume1-private.log')")
a=s.index(" phase('configure'");b=s.index(" phase('image-modules'",a)
s=s[:a]+" release=(BUILD/'include/config/kernel.release').read_text().strip()\n assert release=='7.3.0-rc6-rmx1931-samurai-k363+'\n changed=['lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']]\n final_input=snapshot(payload)\n"+s[b:]
s=s.replace("assert report['camss_component_count']>=40", "assert report['camss_component_count']>=40\n report.update(intentional_parallelism_resume=True,parallel_jobs=8,previous_attempt_seconds=json.loads((PRIVATE/'boot-before-resume-private.json').read_text())['seconds'])")
(HERE/'resume-boot-kernel.py').write_text(s);compile(s,str(HERE/'resume-boot-kernel.py'),'exec')
print('Prepared Image-phase continuation; existing modules/config/initramfs reused, j8.')
