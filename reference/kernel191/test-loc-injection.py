from pathlib import Path
import hashlib,json,os,shlex,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel191/host-tests');out.mkdir(exist_ok=True)
source_root=out.parent/'source'
def production(source):
 start=source.index('typedef struct {',source.index('/* Location: Inject UTC time */'))
 end=source.index('static void\nloc_register_event_inject_req_ready (',start)
 data=source.index('#define MAX_BYTES_PER_REQUEST 1024')
 data_end=source.index('/*****************************************************************************/',data)
 return source[start:end]+source[data:data_end]
api=[]
for op,(name,typename) in enumerate([('inject_utc_time','InjectUtcTime'),('inject_position','InjectPosition'),('inject_predicted_orbits_data','InjectPredictedOrbitsData'),('inject_xtra_data','InjectXtraData')]):
 for prefix,suffix in [('QmiMessageLoc','Input'),('QmiMessageLoc','Output'),('QmiIndicationLoc','Output')]:
  t=prefix+typename+suffix;api.append('typedef Output '+t+';')
  if prefix=='QmiMessageLoc':api.append('G_DEFINE_AUTOPTR_CLEANUP_FUNC('+t+',output_unref)')
 for prefix in ['qmi_message_loc_','qmi_indication_loc_']:
  api.extend([f'#define {prefix}{name}_output_ref output_ref',f'#define {prefix}{name}_output_unref output_unref'])
 api.extend([f'#define qmi_client_loc_{name}_finish fake_finish',f'#define qmi_message_loc_{name}_output_get_result response_result',f'#define qmi_indication_loc_{name}_output_get_indication_status indication_status',f'#define qmi_message_loc_{name}_input_new() output_new(0)',f'#define qmi_message_loc_{name}_input_unref output_unref',f'static void qmi_client_loc_{name}(QmiClientLoc *c,Output *i,int t,void *n,GAsyncReadyCallback cb,gpointer d) {{fake_send({op},c,i,t,n,cb,d);}}'])
 if op>=2:
  for field,target in [('total_size','set_total'),('total_parts','set_parts'),('part_number','set_part'),('part_data','set_data')]:api.append(f'#define qmi_message_loc_{name}_input_set_{field} {target}')
  api.append(f'#define qmi_indication_loc_{name}_output_get_part_number indication_part')
api.extend(['typedef Output QmiIndicationLocInjectTimeRequestOutput;','typedef Output QmiIndicationLocInjectPositionRequestOutput;'])
for field,target in [('latitude','get_lat'),('longitude','get_lon'),('utc_timestamp','get_time')]:api.append(f'#define qmi_indication_loc_inject_position_request_output_get_{field} {target}')
for name,fields in [('inject_utc_time',['utc_time','time_uncertainty','time_source']),('inject_position',['latitude','longitude','position_source','horizontal_uncertainty_circular','horizontal_confidence','utc_timestamp']),('inject_predicted_orbits_data',['format_type'])]:
 for field in fields:
  target='set_utc' if field in ['utc_time','utc_timestamp'] else 'set_uncertainty' if field in ['time_uncertainty','horizontal_uncertainty_circular'] else None
  api.append(f'#define qmi_message_loc_{name}_input_set_{field} '+target if target else f'#define qmi_message_loc_{name}_input_set_{field}(p,v,e) ((void)(p),(void)(v),(void)(e),TRUE)')
template=(ref/'loc-injection-harness.c').read_text().replace('/* BUILD_API_MOCKS */','\n'.join(api))
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gio-2.0'],text=True));env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
def build(name,text):
 p=out/(name+'.c');p.write_text(template.replace('/* BUILD_PRODUCTION_CALLBACKS */',production(text)));binary=out/name
 result=subprocess.run(['gcc','-g','-O1','-fno-omit-frame-pointer','-fsanitize=address,undefined','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-value','-Wno-deprecated-declarations',str(p),'-o',str(binary)]+flags,capture_output=True)
 (out/(name+'-compile-private.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,(out/(name+'-compile-private.log'))
 return binary
original=(source_root/'mm-shared-qmi-before.c').read_text();baseline=build('baseline',original)
negative=[]
for mode,events,expected in [(0,'TE',-1),(1,'TE',-1),(2,'IA',1),(3,'IA',1)]:
 result=subprocess.run([str(baseline),str(mode),events,str(expected),'single'],capture_output=True,env=env)
 (out/(f'baseline-{mode}-{events}-private.log')).write_bytes(result.stdout+result.stderr)
 assert result.returncode!=0,(mode,events)
 negative.append(dict(operation=mode,events=events,rejected=True))
patched=(source_root/'mm-shared-qmi.c').read_text();binary=build('patched',patched)
result=subprocess.run([str(binary)],capture_output=True,env=env)
(out/'patched-run-private.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0,(out/'patched-run-private.log')
mutants={
 'remove_ack_reference':patched.replace('g_object_ref (task));','task);'),
 'ignore_part_number':patched.replace('part_number != ctx->n_part','FALSE'),
 'retain_predicted_listener_on_fallback':patched.replace('''if (g_error_matches (error, QMI_PROTOCOL_ERROR, QMI_PROTOCOL_ERROR_NOT_SUPPORTED)) {
            inject_assistance_data_context_cleanup_action (ctx);''','''if (g_error_matches (error, QMI_PROTOCOL_ERROR, QMI_PROTOCOL_ERROR_NOT_SUPPORTED)) {
            /* Broken cleanup for the negative test. */''')}
for name,text in mutants.items():
 assert text!=patched
 mutant=build(name,text);r=subprocess.run([str(mutant)],capture_output=True,env=env)
 (out/(name+'-run-private.log')).write_bytes(r.stdout+r.stderr);assert r.returncode!=0,name
def capability(s):
 a=s.index('typedef struct {',s.index('/* Location: load supported assistance data */'));b=s.index('/* Location: Inject UTC time */',a)
 c=s.index('static void\nloc_location_get_predicted_orbits_data_source_indication_cb (',b);d=s.index('/* Location: inject assistance data */',c)
 return s[a:b]+s[c:d]
assert capability(patched)==capability(original)
report=dict(stage=191,production_callbacks_sha256=hashlib.sha256(production(patched).encode()).hexdigest(),cases=257,address_sanitizer=True,undefined_behavior_sanitizer=True,leak_detection=True,pinned190_runtime_failures=negative,runtime_mutants_rejected=list(mutants),capability190_fix_unchanged=True,stdout=result.stdout.decode().strip())
(ref/'loc-injection-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
