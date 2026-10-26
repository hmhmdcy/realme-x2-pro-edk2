"""Extract actual driver functions and run only the IRQ delta cases."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/cy122/charging-management-20261023/usb-input-irq-object-r1/tests')
OUTPUT.mkdir(parents=True,exist_ok=True)
binary=OUTPUT/'test-events'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=HERE/'samurai-usb-input.c'
raw=source.read_bytes();text=raw.decode()
assert 'normal_shutdown_uses_existing_stop' in json.loads((HERE/'source-result.json').read_bytes())
assert sha(source)==json.loads((HERE/'source-result.json').read_bytes())['candidate_source_sha256']
def function(name):
    anchor=text.index(name+'(')
    start=text.rfind('\n',0,anchor)+1
    begin=text.index('{',anchor);depth=1;i=begin+1
    while depth:
        depth += (text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]+'\n'
extracted='\n'.join(function(n) for n in ['samurai_usb_event','samurai_usb_request_events','samurai_usb_stop','samurai_usb_shutdown'])
(HERE/'actual-events-and-stop.inc').write_text(extracted)
baseline=(HERE/'baseline-samurai-usb-input.c').read_text()
stop=function('samurai_usb_stop')
assert stop.strip() in baseline
assert text.index('input->paused = true;',text.index('static int samurai_usb_probe')) < text.index('samurai_usb_request_events(pdev, input)') < text.index('input->psy = devm_power_supply_register') < text.index('devm_add_action_or_reset(dev, samurai_usb_stop, input)') < text.index('input->paused = false;',text.index('static int samurai_usb_probe'))
command=['gcc','-std=c11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'test-events.c'),'-o',str(binary)]
built=subprocess.run(command,capture_output=True,text=True)
assert built.returncode==0,built.stdout+built.stderr
run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
assert run.returncode==0,run.stdout+run.stderr
actual=json.loads(run.stdout)
result={'passed':True,'actual_function_result':actual,'asan_ubsan':True,'compiler_command':command,
        'source_sha256':sha(source),'test_source_sha256':sha(HERE/'test-events.c'),
        'actual_extracted_functions_sha256':sha(HERE/'actual-events-and-stop.inc'),
        'runner_sha256':sha(Path(__file__)),
        'static_probe_order_verified':True,'legacy_stop_function_unchanged':True,
        'scope':'actual event/request/stop/shutdown bodies with fake IRQ/platform/work boundary; not full probe or hardware concurrency proof',
        'old_float_decode_tests_rerun':False,'phone_SSH_USB_SDK_Git_used':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':actual['actual_function_cases'],'receipt_sha256':sha(HERE/'test-result.json')}))
