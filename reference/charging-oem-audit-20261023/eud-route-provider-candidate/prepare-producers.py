"""Pair every existing functional EUD entry before any hardware operation."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
origins={'eud.c':REF/'charging-session-20261023/eud-runtime-window-candidate-r2/eud.c',
    'qcom_eud.c':HERE.parent/'eud-sdp500/drivers--usb--misc--qcom_eud.c',
    'eud_earlycon.c':HERE.parent/'apsd-integration/current-r7/snapshots/drivers--tty--serial--eud_earlycon.c'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
files={};patch=''
for name,path in origins.items():
    old=path.read_text();new=replace(old,'#include <linux/module.h>' if name!='eud_earlycon.c' else '#include <linux/kernel.h>',
        ('#include <linux/module.h>' if name!='eud_earlycon.c' else '#include <linux/kernel.h>')+'\n#include <linux/usb/samurai-eud-route.h>')
    if name=='eud.c':
        mark='''        struct resource *res;
        int ret;

        if (eud || eud_window_orphan)'''
        new=replace(new,mark,'''        struct resource *res;
        struct samurai_eud_producer *producer;
        int ret;

        if (eud || eud_window_orphan)''')
        mark='''        port = &up->port;
        port->membase = devm_platform_get_and_ioremap_resource'''
        prefix='''        ret = samurai_eud_producer_claim(pdev, &producer);
        if (ret)
                return ret;
        if (producer) {
                ret = devm_add_action_or_reset(&pdev->dev, samurai_eud_producer_release, producer);
                if (ret)
                        return ret;
        }

'''
        new=replace(new,mark,prefix+mark)
        target='drivers/tty/serial/eud.c'
    elif name=='qcom_eud.c':
        new=replace(new,'\tstruct resource *res;\n\tint ret;', '\tstruct resource *res;\n\tstruct samurai_eud_producer *producer;\n\tint ret;')
        mark='\tchip->dev = &pdev->dev;'
        prefix='''	ret = samurai_eud_producer_claim(pdev, &producer);
	if (ret)
		return ret;
	if (producer) {
		ret = devm_add_action_or_reset(&pdev->dev, samurai_eud_producer_release, producer);
		if (ret)
			return ret;
	}

'''
        new=replace(new,mark,prefix+mark);target='drivers/usb/misc/qcom_eud.c'
    else:
        # This legacy poll is never called; the existing transmitter already
        # uses only the measured timed pacing. Keep every live body intact.
        code=re.sub(r'/\*.*?\*/|//[^\n]*','',old,flags=re.S)
        assert len(re.findall(r'\beud_wait_tx\b',code))==1
        start=new.index('static void eud_wait_tx(');end=new.index('\nstatic void eud_write(',start)
        new=new[:start]+new[end+1:]
        new=replace(new,'\tvoid __iomem *csr;','\tvoid __iomem *csr;\n\tint ret;')
        mark='''	if (!device->port.membase)
		return -ENODEV;
'''
        new=replace(new,mark,mark+'''
	ret = samurai_eud_earlycon_claim(device->port.mapbase);
	if (ret)
		return ret;
''');target='drivers/tty/serial/eud_earlycon.c'
    output=HERE/name
    if output.exists():assert output.read_text()==new,name
    else:output.write_text(new)
    files[name]=dict(original=str(path),original_sha256=sha(path.read_bytes()),sha256=sha(new.encode()),target=target)
    patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+target,tofile='b/'+target))
(HERE/'producer-entry.patch').write_text(patch)
(HERE/'source-result.json').write_text(json.dumps(dict(prepared=True,files=files,phone_accessed=False,APSD_gate_enabled=False),indent=2)+'\n')
print(json.dumps(dict(prepared=True,paired_producers=3,phone_accessed=False)))
