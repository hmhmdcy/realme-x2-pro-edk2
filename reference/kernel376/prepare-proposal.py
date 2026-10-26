from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'firmware-session-validation.json').read_text())['passed']
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c'];before={n:(P/(n+'.before')).read_text() for n in names};after=dict(before)
s=after[names[0]].replace('/* SM8150 A5 firmware transport. No image sessions or IPE commands yet. */','/* SM8150 A5 firmware transport and IPE session lifecycle. */')
anchor='#define EVENT_NOTIFY 0x20008U';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n#define IPE_CREATE 0x1010008U\n#define IPE_CREATE_ACK 0x1020008U\n#define IPE_ASYNC_DIRECT 0x101000aU\n#define IPE_ASYNC_DIRECT_ACK 0x102000aU\n#define IPE_DESTROY 8U')
s=s.replace('if (bytes < 8)\n\t\tgoto malformed;', 'if (bytes < 8 || get_unaligned_le32(a5->message) != bytes)\n\t\tgoto malformed;')
anchor='\tcase PING_ACK:';assert s.count(anchor)==1
cases='''\tcase IPE_CREATE_ACK:
\t\tif (bytes != 32)
\t\t\tgoto malformed;
\t\tif (get_unaligned_le64(a5->message + 16) != a5->session_cookie ||
\t\t    get_unaligned_le64(a5->message + 24) != a5->session_cookie2)
\t\t\treturn;
\t\terror = get_unaligned_le32(a5->message + 8);
\t\ta5->session_reply_handle = get_unaligned_le32(a5->message + 12);
\t\tif (!error && !a5->session_reply_handle)
\t\t\tgoto malformed;
\t\ta5->session_reply = true;
\t\tbreak;
\tcase IPE_ASYNC_DIRECT_ACK:
\t\t/* Actual A5 firmware emits 32-byte header plus 16-byte payload,
\t\t * not sizeof(the downstream packed 12-byte payload declaration).
\t\t */
\t\tif (bytes != 48)
\t\t\tgoto malformed;
\t\tif (get_unaligned_le64(a5->message + 12) != a5->session_cookie ||
\t\t    get_unaligned_le64(a5->message + 20) != a5->session_cookie2)
\t\t\treturn;
\t\tif (get_unaligned_le32(a5->message + 8) != a5->session_opcode)
\t\t\tgoto malformed;
\t\terror = get_unaligned_le32(a5->message + 28);
\t\tif (!error)
\t\t\terror = get_unaligned_le32(a5->message + 32);
\t\ta5->session_reply = true;
\t\tbreak;
'''
s=s.replace(anchor,cases+anchor)
anchor='\tWRITE_ONCE(a5->command_error, error ? -EREMOTEIO : 0);\n\tcomplete(&a5->response);'
assert s.count(anchor)==1
s=s.replace(anchor,'\t/* A successful packet must not erase a concurrent watchdog/protocol\n\t * failure latched by the hard IRQ or an earlier packet in this batch.\n\t */\n\tif (error)\n\t\tcommand_failure(a5, -EREMOTEIO);\n\telse\n\t\tcomplete(&a5->response);')
a=s.index('static int send_command(');b=s.index('bool camss_a5_backing_owned(',a)
old=s[a:b]
generic=old.replace('static int send_command(struct camss_a5 *a5, u32 type, u32 response)', 'static int send_packet(struct camss_a5 *a5, const void *packet, u32 bytes,\n\t\t\t u32 response)')
generic=generic.replace('\t__le32 packet[4];\n\tu32 bytes = type == SYS_PING ? 16 : 8;\n','').replace('\tif (!a5->cpu_enabled', '\ta5->command_queued = false;\n\tif (!a5->cpu_enabled')
generic=generic.replace('\tpacket[0] = cpu_to_le32(bytes);\n\tpacket[1] = cpu_to_le32(type);\n\tput_unaligned_le64(a5->ping_cookie, packet + 2);\n','')
generic=generic.replace('\twritel(1, a5->resources.sierra + A5_HOST_INTERRUPT);','\ta5->command_queued = true;\n\twritel(1, a5->resources.sierra + A5_HOST_INTERRUPT);')
generic=generic.replace('\tWRITE_ONCE(a5->expected, 0);\n\treturn ret;', '\tWRITE_ONCE(a5->expected, 0);\n\t/* Join an IRQ thread already parsing a response before inspecting its\n\t * fields or reusing the pending token/handle state.\n\t */\n\tsynchronize_irq(a5->irq);\n\tif (!ret)\n\t\tret = READ_ONCE(a5->command_error);\n\treturn ret;')
wrapper='''static int send_command(struct camss_a5 *a5, u32 type, u32 response)
{
\t__le32 packet[4];
\tu32 bytes = type == SYS_PING ? 16 : 8;

\tpacket[0] = cpu_to_le32(bytes);
\tpacket[1] = cpu_to_le32(type);
\tput_unaligned_le64(a5->ping_cookie, packet + 2);
\treturn send_packet(a5, packet, bytes, response);
}

'''
s=s[:a]+generic+wrapper+(HERE/'session-methods.c').read_text()+'\n'+s[b:]
anchor='\t\tif (a5->initialized && a5->irq_enabled) {';assert s.count(anchor)==1
s=s.replace(anchor,'\t\tif (a5->initialized && a5->irq_enabled &&\n\t\t    !a5->session_uncertain && !a5->session_count) {')
anchor='\tcapture_shared_state(a5);\n\treturn 0;\n}\n\nstatic int stop_locked';assert s.count(anchor)==1;s=s.replace(anchor,'\tinvalidate_sessions(a5);\n'+anchor)
anchor='''static int stop_locked(struct camss_a5 *a5)
{
\tint ret;

\tret = quiesce_locked(a5);''';assert s.count(anchor)==1
s=s.replace(anchor,'''static int stop_locked(struct camss_a5 *a5)
{
\tstruct camss_a5_session *session, *next;
\tint ret;

\tif (a5->initialized && !a5->session_uncertain) {
\t\tlist_for_each_entry_safe(session, next, &a5->sessions, node) {
\t\t\tret = ipe_destroy_locked(a5, session);
\t\t\tif (ret)
\t\t\t\tbreak;
\t\t}
\t}
\tret = quiesce_locked(a5);''')
anchor='\ta5->boot_expired = false;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\ta5->session_creates = a5->session_destroys = a5->session_peak = 0;')
anchor='\tmutex_init(&a5->lock);';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\tINIT_LIST_HEAD(&a5->sessions);')
after[names[0]]=s
s=after[names[1]].replace('#include <linux/hrtimer.h>','#include <linux/hrtimer.h>\n#include <linux/list.h>')
anchor='struct camss_a5 {';assert s.count(anchor)==1
s=s.replace(anchor,'''struct camss_a5;

enum camss_a5_ipe_type {
\tCAMSS_A5_IPE_RT = 2,
\tCAMSS_A5_IPE_NON_RT = 3,
};

/* Zero-initialize before first use. Keep this object alive until destroy or
 * successful stop; do not mutate its fields or use one object with two owners.
 * Stop destroys live known sessions, or invalidates them after forced reset.
 * No image buffers or frame commands are submitted by this interface yet.
 */
struct camss_a5_session {
\tstruct list_head node;
\tstruct camss_a5 *a5;
\tu32 handle, type;
};

'''+anchor)
anchor='\tu64 ping_cookie;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\tstruct list_head sessions;\n\tu64 session_sequence, session_cookie, session_cookie2;\n\tu32 session_opcode, session_reply_handle;\n\tu32 session_count, session_creates, session_destroys, session_peak;\n\tbool command_queued, session_reply, session_uncertain;')
anchor='int camss_a5_stop(struct camss_a5 *a5);';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\nint camss_a5_ipe_create(struct camss_a5 *a5, struct camss_a5_session *session,\n\t\t\t u32 handle_type);\nint camss_a5_ipe_destroy(struct camss_a5 *a5, struct camss_a5_session *session);')
after[names[1]]=s
s=after[names[2]].replace('/* Temporary bootstrap diagnostic. No image sessions or sensor changes. */','/* Temporary A5/IPE session diagnostic. No image frames or sensor changes. */')
anchor='static struct camss_a5 *device_a5;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\nstatic struct camss_a5_session session_rt, session_non_rt;')
anchor='\\"image_sessions\\":0}';assert s.count(anchor)==1;s=s.replace(anchor,'\\"image_sessions\\":%u,\\"session_creates\\":%u,\\"session_destroys\\":%u,\\"session_peak\\":%u,\\"session_uncertain\\":%s,\\"image_frames\\":0}')
anchor='\t\t  a5->queue_state[3], a5->queue_state[4], a5->queue_state[5]);';assert s.count(anchor)==1;s=s.replace(anchor,'\t\t  a5->queue_state[3], a5->queue_state[4], a5->queue_state[5],\n\t\t  a5->session_count, a5->session_creates, a5->session_destroys, a5->session_peak,\n\t\t  a5->session_uncertain ? "true" : "false");')
anchor='\tret = camss_a5_ping(a5, 0x353536706d636173ULL);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
\tif (ret)
\t\tgoto done;
\tphase = "create-ipe-rt";
\tret = camss_a5_ipe_create(a5, &session_rt, CAMSS_A5_IPE_RT);
\tif (ret)
\t\tgoto done;
\tphase = "create-ipe-non-rt";
\tret = camss_a5_ipe_create(a5, &session_non_rt, CAMSS_A5_IPE_NON_RT);
\tif (ret)
\t\tgoto done;
\tphase = "destroy-ipe-non-rt";
\tret = camss_a5_ipe_destroy(a5, &session_non_rt);
\tif (ret)
\t\tgoto done;
\tphase = "destroy-ipe-rt";
\tret = camss_a5_ipe_destroy(a5, &session_rt);''')
after[names[2]]=s;(HERE/names[2]).write_text(s)
patch=''
for name in names:
 (P/(name+'.proposed')).write_text(after[name]);patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'ipe-session.patch').write_text(patch)
parent=json.loads((HERE/'source-before.json').read_text())['parent'];(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=376,parent=parent,changed=names,installed=False),indent=2)+'\n')
print('Prepared IPE RT/non-RT session lifecycle, strict original A5 response layouts and token matching.')
