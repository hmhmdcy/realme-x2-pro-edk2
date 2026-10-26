from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel374'
s=(OLD/'owner-regression.c').read_text()
s=s.replace('struct camss_a5 {','struct camss_a5_session {struct camss_a5 *a5;unsigned type;};\n#define CAMSS_A5_IPE_RT 2\n#define CAMSS_A5_IPE_NON_RT 3\nstruct camss_a5 {')
s=s.replace(' unsigned interrupts,messages,watchdogs,protocol_errors;',' unsigned interrupts,messages,watchdogs,protocol_errors;\n unsigned session_count;')
s=s.replace('static struct camss_a5 *device_a5,*allocated;','static struct camss_a5 *device_a5,*allocated;\nstatic struct camss_a5_session session_rt,session_non_rt;\nstatic unsigned creates,destroys;')
anchor='static void *devm_kzalloc('
idx=s.index(anchor)
s=s[:idx]+'''static int camss_a5_ipe_create(struct camss_a5 *a,struct camss_a5_session *session,unsigned type){
 assert(a->initialized && test_lock && !session->a5);++creates;
 if((scenario==30 && type==2)||(scenario==31 && type==3))return -EREMOTEIO;
 session->a5=a;session->type=type;++a->session_count;return 0;
}
static int camss_a5_ipe_destroy(struct camss_a5 *a,struct camss_a5_session *session){
 assert(session->a5==a && test_lock);++destroys;
 if((scenario==32 && session->type==3)||(scenario==33 && session->type==2))return -EREMOTEIO;
 session->a5=NULL;--a->session_count;return 0;
}
'''+s[idx:]
s=s.replace(' a->pc_done=a->initialized;', ' session_rt.a5=session_non_rt.a5=NULL;a->session_count=0;\n a->pc_done=a->initialized;')
s=s.replace('if(scenario>=20){','if(scenario>=20 && scenario<=23){')
s=s.replace('scenario==6?-EPROTO:0;', 'scenario==6?-EPROTO:scenario>=30?-EREMOTEIO:0;')
s=s.replace(' assert(test_error==error);',' assert(test_error==error);\n if(!error)assert(creates==2 && destroys==2 && !a.session_count);\n if(scenario==30)assert(creates==1 && !destroys);\n if(scenario==31)assert(creates==2 && !destroys);\n if(scenario==32)assert(creates==2 && destroys==1);\n if(scenario==33)assert(creates==2 && destroys==2);')
(HERE/'owner-regression.c').write_text(s)
s=(OLD/'check-owner.py').read_text().replace('stage=374','stage=376').replace('list(range(15))+[20,21,22,23]','list(range(15))+[20,21,22,23,30,31,32,33]')
s=s.replace('actual_platform_binding_and_hardware_handshake_not_proven=True','actual_platform_binding_and_hardware_handshake_not_proven=True,session_create_destroy_failure_cleanup_paths_checked=True')
(HERE/'check-owner.py').write_text(s)
print('Prepared actual owner run/probe/cleanup models including each new session-stage failure.')
