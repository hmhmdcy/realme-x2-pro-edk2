"""Only writes measured-start. Keep the preceding 8-source delivery frozen."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent
REF=OLD.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(text,a,b):
    assert text.count(a)==1,a
    return text.replace(a,b)

frozen=json.loads((OLD/'delivery.json').read_bytes())
for row in frozen['sources'].values():assert sha(OLD/row['file'])==row['sha256']
inputs={
 'qcom_pmic_typec_pdphy.c':OLD/'qcom_pmic_typec_pdphy.c',
 'qcom_pmic_typec_pdphy.h':REF/'tcpm-contract-shutdown-candidate/qcom_pmic_typec_pdphy.h',
 'qcom_pmic_typec.h':REF/'tcpm-contract-shutdown-candidate/qcom_pmic_typec.h',
}
texts={name:p.read_text() for name,p in inputs.items()}
texts['qcom_pmic_typec.h']=replace(texts['qcom_pmic_typec.h'],
 '\tstruct samurai_pd5v\t*pd5v;\n',
 '\tstruct samurai_pd5v\t*pd5v;\n\tstruct qcom_pmic_typec_apsd *apsd_handoff;\n')
api='''/* Pre-TCPM real-supply lifecycle callbacks for measured APSD takeover.
 * context is the original struct pmic_typec, before tcpm_register_port().
 */
int qcom_pmic_typec_pdphy_apsd_begin(void *context);
int qcom_pmic_typec_pdphy_apsd_verify(void *context);
int qcom_pmic_typec_pdphy_apsd_release(void *context);
'''
texts['qcom_pmic_typec_pdphy.h']=replace(texts['qcom_pmic_typec_pdphy.h'],
 '/* API */\n','/* API */\n'+api)
phy=texts['qcom_pmic_typec_pdphy.c']
phy=replace(phy,'\tbool\t\t\tsupply_held;\n',
 '\tbool\t\t\tsupply_held;\n\tbool\t\t\thandoff_powered; /* actual untransferred regulator reference */\n')
extra='''/* The bound probe/devres lifecycle serializes these pre-start callbacks.
 * No TCPM worker/port or IRQ is active when begin is allowed. Regulator APIs
 * run outside the PHY spinlock; only actual register reads run inside it.
 */
static int qcom_pmic_typec_pdphy_handoff_quiet(struct pmic_typec_pdphy *p)
{
\tstatic const unsigned int controls[] = {
\t\tUSB_PDPHY_BIST_MODE_REG, USB_PDPHY_TX_CONTROL_REG,
\t\tUSB_PDPHY_FRAME_FILTER_REG, USB_PDPHY_EN_CONTROL_REG,
\t};
\tunsigned long flags;
\tunsigned int i, value;
\tint ret = 0;

\tif (!p->handoff_powered || p->supply_held || p->tcpm_port || p->irqs_started)
\t\treturn -EBUSY;
\tspin_lock_irqsave(&p->lock, flags);
\tfor (i = 0; i < ARRAY_SIZE(controls); i++) {
\t\tret = regmap_read(p->regmap, p->base + controls[i], &value);
\t\tif (ret)
\t\t\tbreak;
\t\tif (value) {
\t\t\tret = -EBUSY;
\t\t\tbreak;
\t\t}
\t}
\tspin_unlock_irqrestore(&p->lock, flags);
\treturn ret;
}

int qcom_pmic_typec_pdphy_apsd_verify(void *context)
{
\tstruct pmic_typec *tcpm = context;

\tif (!tcpm || !tcpm->pmic_typec_pdphy || tcpm->tcpm_port)
\t\treturn -EBUSY;
\treturn qcom_pmic_typec_pdphy_handoff_quiet(tcpm->pmic_typec_pdphy);
}

int qcom_pmic_typec_pdphy_apsd_release(void *context)
{
\tstruct pmic_typec *tcpm = context;
\tstruct pmic_typec_pdphy *p;
\tint ret;

\tif (!tcpm || !tcpm->pmic_typec_pdphy)
\t\treturn -EINVAL;
\tp = tcpm->pmic_typec_pdphy;
\tif (!p->handoff_powered)
\t\treturn 0; /* never acquired, already released, or consumed by start */
\tif (p->supply_held || p->tcpm_port || p->irqs_started)
\t\treturn -EBUSY;
\tret = regulator_disable(p->vdd_pdphy);
\tif (!ret)
\t\tp->handoff_powered = false;
\treturn ret;
}

int qcom_pmic_typec_pdphy_apsd_begin(void *context)
{
\tstruct pmic_typec *tcpm = context;
\tstruct pmic_typec_pdphy *p;
\tint ret, release;

\tif (!tcpm || !tcpm->pmic_typec_pdphy || tcpm->tcpm_port)
\t\treturn -EBUSY;
\tp = tcpm->pmic_typec_pdphy;
\tif (p->handoff_powered || p->supply_held || p->tcpm_port || p->irqs_started)
\t\treturn -EBUSY;
\tret = regulator_enable(p->vdd_pdphy);
\tif (ret)
\t\treturn ret;
\tp->handoff_powered = true;
\tret = qcom_pmic_typec_pdphy_handoff_quiet(p);
\tif (ret) {
\t\trelease = qcom_pmic_typec_pdphy_apsd_release(tcpm);
\t\tif (release)
\t\t\tdev_err(p->dev, "unverified pre-start PD supply release failed %d\\n", release);
\t}
\treturn ret;
}

static void qcom_pmic_typec_pdphy_apsd_cleanup(void *context)
{
\tstruct pmic_typec *tcpm = context;
\tint ret = qcom_pmic_typec_pdphy_apsd_release(tcpm);

\tif (ret)
\t\tdev_err(tcpm->dev, "pre-start PD PHY devres release failed %d\\n", ret);
}

'''
phy=replace(phy,'static int qcom_pmic_typec_pdphy_start(struct pmic_typec *tcpm,\n',
 extra+'static int qcom_pmic_typec_pdphy_start(struct pmic_typec *tcpm,\n')
phy=replace(phy,'''\tret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);
\tif (ret)
\t\treturn ret;

\tpmic_typec_pdphy->supply_held = true;''', '''\tif (pmic_typec_pdphy->handoff_powered) {
\t\t/* Recheck actual zero controls; transfer the SAME held reference.
\t\t * The outer tcpm_port was just registered, but this PHY has not
\t\t * published its own port or enabled IRQs/protocol callbacks yet.
\t\t */
\t\tret = qcom_pmic_typec_pdphy_handoff_quiet(pmic_typec_pdphy);
\t\tif (ret)
\t\t\treturn ret;
\t\tpmic_typec_pdphy->supply_held = true;
\t\tpmic_typec_pdphy->handoff_powered = false;
\t} else {
\t\tret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);
\t\tif (ret)
\t\t\treturn ret;
\t\tpmic_typec_pdphy->supply_held = true;
\t}''')
phy=replace(phy,'if (tcpm->samurai_fixed_5v)\n\t\treturn ret;',
 'if (tcpm->samurai_fixed_5v || tcpm->samurai_contract_shutdown)\n\t\treturn ret;')
phy=replace(phy,'\ttcpm->pmic_typec_pdphy = pmic_typec_pdphy;\n',
 '''\ttcpm->pmic_typec_pdphy = pmic_typec_pdphy;
\t/* Added after regulator/IRQ allocation: its bound devres runs while
\t * both the original tcpm and PHY context still exist, and only owns
\t * a pre-start reference. Started protocol power uses joined finish.
\t */
\tret = devm_add_action_or_reset(dev, qcom_pmic_typec_pdphy_apsd_cleanup, tcpm);
\tif (ret)
\t\treturn ret;
''')
texts['qcom_pmic_typec_pdphy.c']=phy
rows={};patch=[]
for name,text in texts.items():
    original=inputs[name].read_text()
    (HERE/name).write_text(text)
    path='drivers/usb/typec/tcpm/qcom/'+name
    rows[path]={'file':name,'baseline':str(inputs[name]),'baseline_sha256':sha(inputs[name]),
        'baseline_normalized_sha256':hashlib.sha256(original.encode()).hexdigest(),'sha256':sha(HERE/name)}
    patch+=difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+path,tofile='b/'+path)
for name in ['qcom_pmic_typec_apsd.c','qcom_pmic_typec_apsd.h']:
    original=(OLD/name).read_text();text=(HERE/name).read_text();path='drivers/usb/typec/tcpm/qcom/'+name
    rows[path]={'file':name,'baseline':str(OLD/name),'baseline_sha256':sha(OLD/name),
        'baseline_normalized_sha256':hashlib.sha256(original.encode()).hexdigest(),'sha256':sha(HERE/name)}
    patch+=difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+path,tofile='b/'+path)
(HERE/'measured-start.patch').write_text(''.join(patch))
(HERE/'source.json').write_text(json.dumps({'prepared':True,'phone_accessed':False,
    'full_probe_integration':False,'frozen_parent_delivery_sha256':sha(OLD/'delivery.json'),
    'frozen_parent_sources':{r['file']:r['sha256'] for r in frozen['sources'].values()},
    'sources':rows},indent=2)+'\n')
print(json.dumps({'prepared':True,'files':len(rows),'parent_frozen':True}))
