"""Use existing board modes and their original mode-selected DS4 modules."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for attempt in ['r3','r4']:
 s=json.loads((HERE/('capture-runtime-'+attempt+'-validation.json')).read_text());assert s['state']['terminal'] and not s['worker_live'] and not s['client_live']
text=(HERE/'ds4-capture.c').read_text();assert '"s5k3m5 "' in text
needle=' bool full_only=getenv("DS4_CAPTURE_FULL_ONLY")!=NULL;';assert text.count(needle)==1
text=text.replace(needle,needle+'''
 const char *model=getenv("DS4_SENSOR_MODEL");if(!model)model="s5k3m5";
 const struct {const char *name;unsigned width,height;} modes[]={
  {"s5kgw1",4608,3456},{"s5k3m5",2104,1560},{"imx471",2304,1728},{"imx319",1632,1224}};
 unsigned mode=0;while(mode<4&&strcmp(model,modes[mode].name))mode++;if(mode==4)return 2;
 unsigned sensor_width=modes[mode].width,sensor_height=modes[mode].height;
 printf("CAMERA model=%s requested=%ux%u\\n",model,sensor_width,sensor_height);
''')
text=text.replace('if(!strncmp(e.name,"s5k3m5 ",7))sen=e;','if(!strncmp(e.name,model,strlen(model))&&e.name[strlen(model)]==\' \')sen=e;')
text=text.replace('input.format.width=2104;input.format.height=1560;','input.format.width=sensor_width;input.format.height=sensor_height;').replace('input.format.width!=2104||input.format.height!=1560','input.format.width!=sensor_width||input.format.height!=sensor_height')
(HERE/'ds4-capture.c').write_text(text)
text=(HERE/'capture-worker-body.py').read_text();a=" for label,pattern in [('full-only',2),('pattern',2),('scene',0)]:";assert a in text
text=text.replace(a," for model,kind,pattern in [('s5kgw1','full-only',2)]+[(m,k,p) for m in ['s5kgw1','s5k3m5','imx471','imx319'] for k,p in [('pattern',2),('scene',0)]]:\n  label=model+'-'+kind")
text=text.replace("root/'params-private.bin',case/'params-private.bin'","root/('params-'+model+'-private.bin'),case/'params-private.bin'")
text=text.replace("env=os.environ.copy()","env=os.environ.copy();env['DS4_SENSOR_MODEL']=model")
text=text.replace("if label=='full-only'","if kind=='full-only'").replace("if label!='full-only'","if kind!='full-only'")
(HERE/'multicamera-worker-body.py').write_text(text)
text=(HERE/'prepare-capture.py').read_text().replace("HERE/'capture-worker-body.py'","HERE/'multicamera-worker-body.py'")
needle="proof={'modules':{}}";assert needle in text
text=text.replace(needle,"for model in ['s5kgw1','s5k3m5','imx471','imx319']:files['params-'+model+'-private.bin']=P/('params-'+model+'-private.bin')\n"+needle)
(HERE/'prepare-multicamera-capture.py').write_text(text)
print(json.dumps(dict(generic_probe_source_sha256=hashlib.sha256((HERE/'ds4-capture.c').read_bytes()).hexdigest(),models=4,passed=True)))
