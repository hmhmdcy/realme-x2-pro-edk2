"""Prepare independent exact-source deltas; never edit an input leaf."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/apsd-session-owner-candidate'
PD=REF/'charging-oem-audit-20261023/pd5v-owner-context-r2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={}
for n in ['core.c','core.h','gadget.c','samurai-apsd-owner.h','samurai-apsd-backend.h','Makefile.fragment']:
 (HERE/n).write_bytes((OLD/n).read_bytes());inputs[str((OLD/n).relative_to(REF))]=sha(OLD/n)
(HERE/'samurai-apsd-owner.h').write_text((OLD/'samurai-apsd-owner.h').read_text().replace('DWC3_APSD_EXIT = 16,','DWC3_APSD_EXIT = 16,\n DWC3_APSD_PD = 32,'))
for n in ['samurai-usb-input-decode.h','samurai-apsd-once.h']:
 p=REF/'charging-oem-audit-20261023'/('apsd-input-backend-candidate' if 'decode' in n else 'apsd-once-candidate')/n
 (HERE/n).write_bytes(p.read_bytes());inputs[str(p.relative_to(REF))]=sha(p)
for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h']:
 inputs[str((PD/n).relative_to(REF))]=sha(PD/n)
s=(PD/'qcom_pmic_typec_5v.h').read_text()
s=s.replace('int qcom_pmic_typec_5v_acquire(','''/* Metadata only: not a lease or PD permission. Exact source/Type-C parent
 * and regmap identity are checked. No physical I/O or supply operation.
 * binding_id never reuses a removed instance's identity. */
struct samurai_pd5v_status {
 unsigned long long binding_id;
 bool initialized, blocked;
 int error;
};
int qcom_pmic_typec_5v_status(struct device *typec, struct device *source,
 struct samurai_pd5v_status *status);
int qcom_pmic_typec_5v_acquire(''')
(HERE/'qcom_pmic_typec_5v.h').write_text(s)
s=(PD/'qcom_pmic_typec_5v.c').read_text()
s=s.replace('unsigned long long generation;', 'unsigned long long generation, binding_id;')
s=s.replace('static struct samurai_pd5v *pd5v_bound;', 'static struct samurai_pd5v *pd5v_bound;\nstatic unsigned long long pd5v_binding_serial;')
s=s.replace('int qcom_pmic_typec_5v_acquire(','''int qcom_pmic_typec_5v_status(struct device *typec, struct device *source,
 struct samurai_pd5v_status *status)
{
 struct samurai_pd5v *p = NULL;
 struct samurai_pd5v_status value = { };
 int ret = 0;
 if (!typec || !source || !status || !source->parent)
  return -EINVAL;
 mutex_lock(&pd5v_registry_lock);
 if (pd5v_bound && pd5v_bound->dev == typec && try_module_get(THIS_MODULE)) {
  p = pd5v_bound;
  kref_get(&p->ref);
 }
 mutex_unlock(&pd5v_registry_lock);
 if (!p)
  return -ENODEV;
 mutex_lock(&p->lock);
 if (p->removed)
  ret = -ESHUTDOWN;
 else if (p->dev->parent != source->parent ||
     !dev_get_regmap(source->parent, NULL) ||
     p->regmap != dev_get_regmap(source->parent, NULL))
  ret = -EXDEV;
 else {
  value.binding_id = p->binding_id;
  value.initialized = p->initialized;
  value.blocked = p->blocked;
  value.error = p->error;
  *status = value;
 }
 mutex_unlock(&p->lock);
 kref_put(&p->ref, pd5v_free);
 module_put(THIS_MODULE);
 return ret;
}

int qcom_pmic_typec_5v_acquire(''')
s=s.replace('\tpd5v_bound = p;\n\tkref_get(&p->ref);', '''\tif (pd5v_binding_serial == ~0ULL) {
\t\tmutex_unlock(&pd5v_registry_lock);
\t\tkref_put(&p->ref, pd5v_free);
\t\treturn ERR_PTR(-EOVERFLOW);
\t}
\tp->binding_id = ++pd5v_binding_serial;
\tpd5v_bound = p;
\tkref_get(&p->ref);''')
(HERE/'qcom_pmic_typec_5v.c').write_text(s)
s=(OLD/'samurai-apsd-owner.c').read_text();inputs[str((OLD/'samurai-apsd-owner.c').relative_to(REF))]=sha(OLD/'samurai-apsd-owner.c')
s=s.replace('''/* Optional, single-controller DWC lifetime consumer. Not enabled on device.
 * No PD/route or EUD/PHY pre-remove lease exists in the fixed source yet.
 * The entry fence below therefore refuses EVERY hardware attempt, including
 * with an installed bus backend. Do not remove it to "enable" this candidate.
 */''','''/* Optional, single-controller DWC lifetime consumer, default off.
 * The separately opted-in PD5V client prepares real disabled-PD control only
 * after physical off. Route/PHY-withdrawal/final-transfer coverage is absent:
 * every APSD window/1341 attempt is still refused, not every PD control I/O.
 */''')
a=s.index('/* This is a proven-missing prerequisite,');b=s.index('static int owner_entry_gate',a)
s=s[:a]+'''/* A real PD5V lease alone is insufficient. Trusted EUD-off route, PHY
 * provider withdrawal and final-transfer revalidation remain unimplemented.
 * Keep a concrete failure before all analog/window/command entry. */
'''+s[b:]
s=s.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/kref.h>\n#include <linux/of_platform.h>\n#include <linux/platform_device.h>')
s=s.replace('#include "core.h"', '#include "core.h"\n#include <linux/usb/samurai-pd5v.h>\n#include "samurai-usb-input-decode.h"')
s=s.replace('struct samurai_apsd_owner {','''enum owner_pd_phase {
 OWNER_PD_OFF, OWNER_PD_WAIT_BINDING, OWNER_PD_WAIT_FIRST_OFF,
 OWNER_PD_WAIT_ATTACH, OWNER_PD_SINK_EPOCH, OWNER_PD_FAILED,
};
struct samurai_apsd_owner {''')
s=s.replace('\tstruct dwc3 *dwc;', '''\tstruct dwc3 *dwc;
 struct kref ref;
 struct device *typec;
 struct samurai_pd5v_lease pd_lease;
 enum owner_pd_phase pd_phase;
 u64 pd_binding;
 bool pd_bridge, pd_prepared;
 int pd_error;''',1)
s=s.replace('static struct samurai_apsd_once protocol_history;', '''static struct samurai_apsd_once protocol_history;
static u64 pd_history_binding;
static bool pd_history_prepared;
static int owner_join(struct samurai_apsd_owner *, unsigned int, bool);

static void owner_free(struct kref *ref)
{
 struct samurai_apsd_owner *o = container_of(ref, struct samurai_apsd_owner, ref);
 if (o->typec)
  put_device(o->typec);
 kfree(o);
}
static bool owner_pd_get(void *context)
{
 struct samurai_apsd_owner *o = context;
 return kref_get_unless_zero(&o->ref);
}
static void owner_pd_put(void *context)
{
 struct samurai_apsd_owner *o = context;
 kref_put(&o->ref, owner_free);
}
static void owner_pd_release(struct samurai_apsd_owner *o)
{
 if (IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) && o->pd_lease.owner)
  samurai_pd5v_release(&o->pd_lease);
}''')
insert=(HERE/'bridge-functions.inc').read_text()
anchor='/* A real PD5V lease alone is insufficient.'
assert s.count(anchor)==1
s=s.replace(anchor,insert+'\n'+anchor)
s=s.replace('\treturn -EOPNOTSUPP;\n}', ''' /* Real PD acquisition is separate from these still-missing capabilities.
  * This unconditional refusal MUST remain: no EUD/DWC/PHY begin or1341 path
  * becomes reachable through the new PD bridge. */
 return -EOPNOTSUPP; /* route + PHY withdrawal + final-write contract absent */
}''',1)
s=s.replace('if (o->once.phase == SAMURAI_APSD_DETACHED) {', '''if (o->pd_bridge) {
  ret = owner_pd_observe(o, &sample);
  if (ret)
   return ret;
 }
 if (o->once.phase == SAMURAI_APSD_DETACHED) {''',1)
# An actual off observation has to prepare PD before returning ENOLINK.
s=s.replace('\t\treturn -ENOLINK;\n\t}', '''  if (o->pd_bridge) {
   ret = owner_pd_observe(o, &sample);
   if (ret)
    return ret;
  }
  return -ENOLINK;
 }''',1)
s=s.replace('o->primary_error = ret;\n\t\t\treturn; /* no begin', 'o->primary_error = ret;\n\t\t\treturn; /* no begin')
# Bridge waits keep the real worker observer alive without arming a command.
s=s.replace('\tret = owner_read(o);\n\tif (ret == SAMURAI_APSD_REQUEST', '''\tret = owner_read(o);
 if (o->pd_bridge && (ret == -EAGAIN || ret == -ENOLINK) && o->pd_phase != OWNER_PD_FAILED) {
  owner_queue(o, msecs_to_jiffies(1000));
  return;
 }
\tif (ret == SAMURAI_APSD_REQUEST''',1)
s=s.replace('\tret = owner_restore(o, retiring);\n\tif (ret)', '''\tret = owner_restore(o, retiring);
 if (!ret)
  owner_pd_release(o);
\tif (ret)''',1)
s=s.replace('\to->dwc = dwc;\n\to->bus', ''' kref_init(&o->ref);
\to->dwc = dwc;
 o->pd_bridge = device_property_read_bool(dwc->dev, "samurai,apsd-pd5v-bridge");
 if (o->pd_bridge) {
  o->pd_phase = OWNER_PD_WAIT_BINDING;
  if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT) ||
      !IS_BUILTIN(CONFIG_TYPEC_QCOM_PMIC)) {
   o->pd_error = -EOPNOTSUPP;
   o->pd_phase = OWNER_PD_FAILED;
  }
 }
\to->bus''',1)
s=s.replace('\t\tkfree(o);\n\t\tgoto out;', '\t\tkref_put(&o->ref, owner_free);\n\t\tgoto out;',1)
s=s.replace('\tprotocol_history = o->once;', '''\tprotocol_history = o->once;
 pd_history_binding = o->pd_binding;
 pd_history_prepared = o->pd_prepared;''',1)
s=s.replace('\tbound_owner = NULL;\n\tkfree(o);', '\tbound_owner = NULL;\n o->dwc = NULL;\n\tkref_put(&o->ref, owner_free);')
(HERE/'samurai-apsd-owner.c').write_text(s)
(HERE/'Kconfig.fragment').write_text((OLD/'Kconfig.fragment').read_text()+'''
config USB_DWC3_SAMURAI_APSD_PD5V_CLIENT
 bool "Samurai pre-attach PD-disabled client bridge (no APSD command)"
 depends on USB_DWC3_SAMURAI_APSD_OWNER && OF
 depends on TYPEC_TCPM=y && TYPEC_QCOM_PMIC=y
 default n
 help
   Same-Image internal client only; also requires the explicit DWC
   samurai,apsd-pd5v-bridge and samurai,apsd-typec properties plus the
   PD5V driver's double opt-in. Current TYPEC_QCOM_PMIC=m is refused.
   Establishes real disabled-PD control only after physical detach.
   Missing route/PHY/transfer gates still deny every APSD command.
''')
diff=[]
for base,n in [(OLD,'samurai-apsd-owner.c'),(OLD,'samurai-apsd-owner.h'),(OLD,'Kconfig.fragment'),(PD,'qcom_pmic_typec_5v.c'),(PD,'qcom_pmic_typec_5v.h')]:
 diff+=difflib.unified_diff((base/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='frozen/'+n,tofile='bridge/'+n)
(HERE/'bridge.patch').write_text(''.join(diff))
(HERE/'source-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
print(json.dumps(dict(prepared=True,inputs=len(inputs))))
