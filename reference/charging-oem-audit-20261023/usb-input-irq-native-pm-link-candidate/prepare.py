"""Only merge the frozen PM-link helper into the actual 7cb IRQ provider source."""
from pathlib import Path
import hashlib, json, difflib, re, importlib.util

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
IRQ=HERE.parent/'usb-input-irq-candidate'
PM=HERE.parent/'usb-input-native-pm-link-candidate'
BOARD=REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def function(text,name):
    match=re.search(r'(?m)^static [^;{}\n]+\b'+re.escape(name)+r'\s*\(',text)
    assert match,name
    start=match.start();brace=text.index('{',match.end());level=1;end=brace+1
    while level:
        level+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]+'\n'

def main():
    prior=json.loads((BOARD/'ko-result.json').read_bytes())
    assert prior['passed'] and prior['module_sha256']=='7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'
    raw=(IRQ/'samurai-usb-input.c').read_bytes()
    assert sha(raw)==prior['source_sha256']=='0fdafb8b3924e431efd67a888cbb88b8f5fe6de22dc400b009bf64cba34b7be5'
    decoder=(PM/'samurai-usb-input-decode.h').read_bytes()
    assert sha(decoder)==prior['decoder_sha256']=='a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'
    helper=(PM/'native-pm-link.c.inc').read_bytes()
    assert sha(helper)=='1b60c5d9ccbb6a5b08176801a4d4513cf9d94bbbaa73de2c2351c38de5eaf1f5'
    old=raw.decode();text=old.replace('#include <linux/of.h>\n','#include <linux/of.h>\n#include <linux/of_platform.h>\n',1)
    text=text.replace('struct samurai_usb_input {\n','struct samurai_usb_input {\n\tstruct device *native_consumer;\n\tstruct device *native_supplier;\n',1)
    anchor='static int samurai_usb_probe(struct platform_device *pdev)\n'
    assert text.count(anchor)==1;text=text.replace(anchor,helper.decode()+'\n'+anchor,1)
    anchor='\tinput->paused = true;\n\tret = samurai_usb_request_events(pdev, input);'
    assert text.count(anchor)==1
    text=text.replace(anchor,'''\tinput->paused = true;
\t/* Order system PM before publishing the supply or requesting its IRQs. */
\tret = samurai_usb_link_native_consumer(dev, input);
\tif (ret)
\t\treturn ret;
\tret = samurai_usb_request_events(pdev, input);''',1)
    names=re.findall(r'(?m)^static [^;{}\n]+\b(samurai_usb_[a-z_]+)\s*\(',old)
    unchanged=[n for n in names if n!='samurai_usb_probe']
    for n in unchanged:assert function(old,n)==function(text,n),n
    for n in ['samurai_usb_unlink_native_consumer','samurai_usb_link_native_consumer']:
        assert function(text,n)==function(helper.decode(),n),n
    (HERE/'samurai-usb-input.c').write_text(text,encoding='utf-8',newline='\n')
    (HERE/'samurai-usb-input-decode.h').write_bytes(decoder)
    (HERE/'native-pm-link.c.inc').write_bytes(helper)
    (HERE/'native-pm-link.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='current-IRQ-0fd/samurai-usb-input.c',tofile='IRQ-native-PM-link/samurai-usb-input.c')),encoding='utf-8',newline='\n')
    groups={'actual-link-irq-probe.inc':['samurai_usb_unlink_native_consumer','samurai_usb_link_native_consumer','samurai_usb_event','samurai_usb_request_events','samurai_usb_probe'],
            'actual-pm-and-setter.inc':['samurai_usb_set_property','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume']}
    for name, funcs in groups.items():(HERE/name).write_text('\n'.join(function(text,n) for n in funcs),encoding='utf-8',newline='\n')
    (HERE/'actual-dwc-vbus-work.inc').write_bytes((PM/'actual-dwc-vbus-work.inc').read_bytes())
    # Reuse only the small frozen parser function; do not run its main or dtc.
    parser=BOARD/'inspect-dtb.py';assert sha(parser.read_bytes())=='5280e01c3c662408d6dc60b65317208e76ed765dc86f64f1ac8698146ff9e5fd'
    spec=importlib.util.spec_from_file_location('cached_dtb_reader',parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    dtb=Path('E:/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01/samurai-usb-input-irq-native-private.dtb')
    dtb_raw=dtb.read_bytes();assert sha(dtb_raw)=='13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
    nodes=m.decode(dtb_raw)['nodes'];node='/soc@0/usb@a6f8800/usb@a600000';p=nodes[node]
    assert b'snps,dwc3' in p['compatible'].split(b'\0') and p['usb-psy-name']==b'samurai-usb-input\0'
    assert all(nodes[n].get('status',b'okay\0') in (b'okay\0',b'ok\0') for n in ['/soc@0','/soc@0/usb@a6f8800',node])
    out=dict(passed=True,baseline_C_sha256=sha(raw),baseline_ko_sha256=prior['module_sha256'],source_sha256=sha((HERE/'samurai-usb-input.c').read_bytes()),
             decoder_sha256=sha(decoder),helper_sha256=sha(helper),helper_file_bytes_exact=True,helper_function_bodies_exact=True,
             old_functions_byte_identical=unchanged,only_old_function_changed='samurai_usb_probe',
             extracts={n:sha((HERE/n).read_bytes()) for n in [*groups,'actual-dwc-vbus-work.inc']},
             actual_legacy_DTB=dict(path=str(dtb),sha256=sha(dtb_raw),node=node,available=True,compatible='snps,dwc3',usb_psy_name='samurai-usb-input'),
             no_new_DTB_built=True,kernel_build_or_storage_accessed=False,device_accessed=False,
             reused_receipts={str(p):sha(p.read_bytes()) for p in [PM/'test-result.json',PM/'delivery.json',IRQ/'test-result.json',BOARD/'ko-result.json']})
    (HERE/'source-result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out))

if __name__=='__main__':main()
