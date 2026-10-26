"""One owned natural discharge/recharge observation, then timer hold proof."""
from pathlib import Path
import importlib.util,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('current_timer_live_IO',HERE/'timer-io.py');protocol=load('current_recharge_protocol',HERE/'recharge-exercise.py')
class IO(base.IO):
    def cancelled(self):return (HERE/'cancel-requested').exists()
def main():
    io=IO(runtime_limit=5720)
    try:
        io.setup();result=protocol.observe_recharge(io,base.e.exercise,5400);io.save('result-private.json',result)
    except BaseException as error:
        io.save('failure-private.json',dict(error=repr(error),commands=io.commands));raise
    finally:io.close()
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
