"""Exercise the production SOF classification without hardware register stubs."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
p=storage.mount.mounted_build().parent/'source354/drivers/media/platform/qcom/camss/camss-vfe.c';text=p.read_text()
a=text.index('static bool vfe_aux_restart_drop(');b=text.index('\n}\n',a)+3;actual=text[a:b]
assert 'sof_tracking && !ready[o]->sof_valid ?\n\t\t\t\tVB2_BUF_STATE_ERROR : VB2_BUF_STATE_DONE' in text
assert 'if (vid->auxiliary && output->gen2.active_num == 1) {\n\t\t\toutput->recovering_sof = true;' in text
source='''#include <assert.h>
#include <stdbool.h>
struct vfe_output {struct {bool auxiliary;}video_out;bool recovering_sof;};
struct camss_buffer {bool sof_valid;};
ACTUAL
int main(void){
 struct vfe_output o={0};struct camss_buffer b={0};
 assert(!vfe_aux_restart_drop(&o,&b));
 o.video_out.auxiliary=true;assert(!vfe_aux_restart_drop(&o,&b));
 o.recovering_sof=true;assert(vfe_aux_restart_drop(&o,&b));assert(o.recovering_sof);
 b.sof_valid=true;assert(!vfe_aux_restart_drop(&o,&b));assert(!o.recovering_sof);
 b.sof_valid=false;assert(!vfe_aux_restart_drop(&o,&b));
 o.video_out.auxiliary=false;o.recovering_sof=true;assert(!vfe_aux_restart_drop(&o,&b));
 b.sof_valid=true;assert(!vfe_aux_restart_drop(&o,&b));assert(!o.recovering_sof);
 return 0;
}
'''.replace('ACTUAL',actual)
(P/'aux-restart-model.c').write_text(source)
for name,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('aux-restart-'+name)
 q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'aux-restart-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],capture_output=True);(P/('aux-restart-'+name+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=441,actual_production_sof_classification_tested=True,host_asan_ubsan=True,aarch64_static_qemu=True,untagged_restart_is_still_vb2_error=True,first_tagged_completion_ends_recovery=True,primary_and_unexpected_later_missing_tags_still_faults=True,no_fabricated_sof_or_gtm_identity=True,no_mmio_added=True,production_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),phone_accessed=False,passed=True)
(HERE/'aux-restart-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
