"""Offline audit of the retained k459/r2 trace and paired k452 CSV."""
from pathlib import Path
import collections
import csv
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mount.mounted_build()
SOURCE=BUILD.parent/'source354'
P=Path('/mnt/e/edk2-samurai-out')
OUT=P/'kernel459';RUN=OUT/'runtime-collected-r2';TRACE=RUN/'k459-host-review'
CSV=P/'kernel452/runtime-collected-r2/trace-window/captures/full-27901-e1-17268856052455.csv'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')

def sources():
    original=load(HERE.parent/'kernel363/boot-candidate-build-validation.json')['commit']
    locations=subprocess.check_output(['git','-C',str(SOURCE),'grep','-n','v4l2_buffer_set_timestamp',original,'--','include']).decode()
    (OUT/'timestamp-helper-location-private.txt').write_text(locations)
    helper_paths={line.split(':',2)[1] for line in locations.splitlines()}
    rows=[]
    for relative in ['drivers/media/v4l2-core/v4l2-ioctl.c','drivers/media/common/videobuf2/videobuf2-core.c',
                     'include/trace/events/vb2.h','include/trace/events/v4l2.h',*sorted(helper_paths)]:
        cached=P/'kernel457/source'/relative
        raw=subprocess.check_output(['git','-C',str(SOURCE),'show',original+':'+relative])
        dest=OUT/'runtime-source363'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        rows.append(dict(path=relative,original_sha256=sha(dest),cached457_sha256=sha(cached) if cached.exists() else None,
                         equal=raw==cached.read_bytes() if cached.exists() else None))
        if relative.endswith('v4l2-ioctl.c'):
            lines=raw.decode().splitlines()
            anchors=[i for i,line in enumerate(lines) if 'trace_v4l2_' in line]
            write('runtime-v4l2-source-snippets-private.json',[dict(line=i+1,lines=lines[max(0,i-25):i+8]) for i in anchors])
    write('runtime-source-audit-private.json',dict(original363=original,files=rows))
    print(json.dumps(dict(source_comparison=rows)))

def audit():
    frozen_names=['README.md','trace-instance.py','check-helper.py','helper-validation.json','render-validation.json',
                  'inspect-capacity.py','capacity-source-validation.json']
    frozen_before={name:sha(HERE/name) for name in frozen_names}
    state=load(TRACE/'state.json');attempt=state['capture_attempts'][0]
    raw=TRACE/'trace-private-1.txt';assert sha(raw)==attempt['trace']['sha256']
    assert raw.stat().st_size==attempt['trace']['bytes'] and attempt['complete'] and attempt['trace']['eof']
    events=[];lost=[]
    pattern=re.compile(r'\s*(?P<comm>.+)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+\S+\s+(?P<time>\d+\.\d+):\s+(?P<event>\w+):\s*(?P<payload>.*)')
    text=raw.read_text();header=re.search(r'entries-in-buffer/entries-written: (\d+)/(\d+)',text)
    for line in text.splitlines():
        if not line or line.startswith('#'):continue
        match=pattern.fullmatch(line)
        if not match:
            if 'LOST' in line:lost.append(line);continue
            raise ValueError('Unparsed trace line: '+line[:150])
        values=match.groupdict();item=dict(event=values['event'],cpu=int(values['cpu']),pid=int(values['pid']),
            mono_ns=int(Decimal(values['time'])*1_000_000_000),comm=values['comm'].strip(),payload=values['payload'])
        if item['event'].startswith('vb2_'):
            fields=dict(re.findall(r'(owner|queued|owned_by_drv|index|type|bytesused|timestamp) = ([0-9a-f]+)',item['payload']))
            assert set(fields)==set(['owner','queued','owned_by_drv','index','type','bytesused','timestamp'])
            item.update({k:(v if k=='owner' else int(v)) for k,v in fields.items()})
        events.append(item)
    counts=collections.Counter(e['event'] for e in events)
    assert len(events)==int(header[1])
    stats=[]
    for cpu in state['possible_cpus']:
        path=TRACE/f'stats-private-1-cpu{cpu}.txt'
        assert sha(path)==attempt['stats'][str(cpu)]['sha256'] and path.stat().st_size==attempt['stats'][str(cpu)]['bytes']
        data=dict(re.findall(r'^([^:]+): ([0-9.]+)$',path.read_text(),re.M))
        row=dict(cpu=cpu,**{key:(int(Decimal(value)*1_000_000_000) if key.endswith(' ts') else int(value)) for key,value in data.items()})
        parsed=[e for e in events if e['cpu']==cpu]
        assert row['entries']==len(parsed)
        if parsed:assert row['oldest event ts']==min(e['mono_ns'] for e in parsed)
        stats.append(row)
    assert sum(s['entries']+s['overrun'] for s in stats)==int(header[2])
    assert all(s['commit overrun']==s['dropped events']==s['read events']==0 for s in stats)
    spec=importlib.util.spec_from_file_location('paired452reader',HERE.parent/'kernel452/check-diagnostic.py')
    paired=importlib.util.module_from_spec(spec);spec.loader.exec_module(paired)
    csv_summary,records=paired.parse_trace(CSV.read_text())
    csv_dq=[r for r in records if r['type']==7 and r['status']==0 and r['flags']&8]
    vb_dq=[e for e in events if e['event']=='vb2_dqbuf']
    # V4L2 timeval conversion truncates to microseconds; compare payload clocks
    # with each other, not a payload timestamp against a callback clock.
    by_timestamp=collections.defaultdict(list)
    for event in vb_dq:
        if event['timestamp']:by_timestamp[event['timestamp']//1000*1000].append(event)
    matches=[]
    for row in csv_dq:
        candidates=by_timestamp[row['hardware_ns']]
        matches.append(dict(csv=row,candidates=candidates))
    owner_counts=collections.Counter(e['owner'] for row in matches for e in row['candidates'])
    write('runtime-exploration-private.json',dict(counts=counts,stats=stats,loss_markers=lost,
       csv=csv_summary,csv_full_dq=len(csv_dq),unique_timestamp_matches=sum(len(x['candidates'])==1 for x in matches),
       unmatched=sum(not x['candidates'] for x in matches),ambiguous=sum(len(x['candidates'])>1 for x in matches),owner_counts=owner_counts,
       candidate_examples=matches[:5]))
    # A FULL dequeue syscall must precede its imageReady/FullDq callback.
    # Require strict ordering despite text timestamps' microsecond precision.
    anchored=[]
    for match in matches:
        earlier=[e for e in match['candidates'] if e['mono_ns']+1000<=match['csv']['mono_ns']]
        assert len(earlier)==1,('Non-unique causal FULL DQ anchor',match['csv']['number'],len(earlier))
        anchored.append(dict(csv=match['csv'],kernel=earlier[0]))
    owners={pair['kernel']['owner'] for pair in anchored};assert len(owners)==1
    owner=owners.pop()
    common_start=max(records[0]['mono_ns'],max(s['oldest event ts']+1000 for s in stats if s['overrun']))
    common_end=records[-1]['mono_ns']
    assert all(common_start<=r['mono_ns']<=common_end for r in csv_dq)
    stop=next(r['mono_ns'] for r in records if r['type']==21)
    q_begin={};q_pairs=[]
    full_q=[e for e in events if e['event']=='vb2_qbuf' and e['owner']==owner]
    full_queue=[e for e in events if e['event']=='vb2_buf_queue' and e['owner']==owner]
    for row in records:
        if row['type']==5:q_begin[(row['request'],row['buffer'])]=row
        if row['type']!=6 or row['status']!=0:continue
        begin=q_begin.pop((row['request'],row['buffer']))
        candidates=[e for e in full_q if begin['mono_ns']<=e['mono_ns'] and e['mono_ns']+1000<=row['mono_ns']]
        assert len(candidates)==1,('QBUF bracket',row['number'],len(candidates))
        q=candidates[0]
        queue=[e for e in full_queue if e['index']==q['index'] and q['mono_ns']<=e['mono_ns'] and e['mono_ns']+1000<=row['mono_ns']]
        assert len(queue)==1
        q_pairs.append(dict(begin=begin,result=row,qbuf=q,buf_queue=queue[0]))
    buffer_indices=collections.defaultdict(set)
    for pair in q_pairs:buffer_indices[pair['begin']['buffer']].add(pair['qbuf']['index'])
    assert all(len(indices)==1 for indices in buffer_indices.values())
    buffer_indices={buffer:next(iter(indices)) for buffer,indices in buffer_indices.items()}
    assert len(set(buffer_indices.values()))==len(buffer_indices)
    full_done=[e for e in events if e['event']=='vb2_buf_done' and e['owner']==owner]
    chains=[]
    for pair in anchored:
        row,dq=pair['csv'],pair['kernel']
        assert buffer_indices[row['buffer']]==dq['index']
        done=[e for e in full_done if e['index']==dq['index'] and e['timestamp']==dq['timestamp'] and e['mono_ns']<=dq['mono_ns']]
        assert len(done)==1
        assert common_start<=done[0]['mono_ns'] and dq['mono_ns']+1000<=row['mono_ns']<=common_end
        chains.append(dict(csv=row,done=done[0],dq=dq,
                           done_to_dq_ns=dq['mono_ns']-done[0]['mono_ns'],dq_to_callback_ns=row['mono_ns']-dq['mono_ns']))
    assert all(b['csv']['sof']==a['csv']['sof']+1 for a,b in zip(chains,chains[1:]))
    def latency(values):
        values=sorted(values);n=len(values)
        return dict(count=n,min_us=values[0]/1000,median_us=(values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2)/1000,
                    p95_us=values[(95*n+99)//100-1]/1000,max_us=values[-1]/1000)
    full_tail=[e for e in events if e['event'].startswith('vb2_') and e['owner']==owner and common_start<=e['mono_ns']<=common_end]
    ranges={}
    for kind in ['vb2_qbuf','vb2_buf_queue','vb2_buf_done','vb2_dqbuf']:
        selected=[e for e in full_tail if e['event']==kind and e['mono_ns']<stop]
        ranges[kind]={key:dict(min=min(e[key] for e in selected),max=max(e[key] for e in selected),
                              zero_snapshots=sum(e[key]==0 for e in selected)) for key in ['queued','owned_by_drv']}
        ranges[kind]['events']=len(selected)
    assert re.findall(r'\[(\w+)\]',state['configuration']['trace_clock'])==['mono']
    assert state['phase']=='cleaned' and state['errors']==[] and attempt['online_cpus_unchanged']
    assert state['unrelated_before']==attempt['unrelated_after']==state['unrelated_at_cleanup']
    assert state['unrelated_selected_controls_unchanged'] and attempt['unrelated_selected_controls_unchanged']
    controller=load(OUT/'controller-live-2-private.json');collected=load(RUN/'result.json')
    assert all(controller.get(key)==collected.get(key) for key in collected)
    assert controller['terminal'] and controller['trace_cleaned'] and not controller['worker_alive_at_controller_end']
    assert controller['trace_instances']==['display','radio'] and controller['errors']==[]
    export=controller['camera_state']['diagnostic_cases']['trace-window']['trace_export']
    assert sha(CSV)==export['sha256'] and CSV.stat().st_size==export['bytes']
    assert state['boot_id']==load(RUN/'baseline-start-private.json')['boot_id'].strip()
    selection=load(TRACE/'selection-private.json');probe=load(TRACE/'probe-private.json')
    assert sha(TRACE/'probe-private.json')==selection['probe_sha256']
    assert probe['video_nodes'][selection['full_video_node']]['dev'].split(':')[1]==str(selection['full_minor'])
    assert selection['clock']=='mono' and selection['full_minor']==0
    assert probe['video_nodes']['video0']['name']=='msm_vfe0_video0'
    assert probe['video_nodes']['video3']==dict(name='msm_vfe0_video3',dev='81:3')
    for name,digest in load(RUN/'manifest.json').items():
        target=RUN/name if (RUN/name).exists() else (HERE/name if (HERE/name).exists() else OUT/name)
        assert sha(target)==digest,(name,'collected controller input fingerprint')
    kernel=P/'kernel457/source';user=P/'kernel457/userspace452/src/libcamera'
    vfe=(kernel/'drivers/media/platform/qcom/camss/camss-vfe.c').read_text()
    header_vfe=(kernel/'drivers/media/platform/qcom/camss/camss-vfe.h').read_text()
    pipeline=(user/'pipeline/camss-vfe/camss_vfe.cpp').read_text()
    ioctl=(OUT/'runtime-source363/drivers/media/v4l2-core/v4l2-ioctl.c').read_text()
    stamp='\n'.join(path.read_text() for path in (OUT/'runtime-source363/include').rglob('*.h') if 'v4l2_buffer_set_timestamp' in path.read_text())
    userspace=(user/'v4l2_videodevice.cpp').read_text()
    source_checks=dict(
      ioctl_trace_success_branch='if (err == 0) {\n\t\tif (cmd == VIDIOC_DQBUF)' in ioctl,
      debug_gate_is_in_separate_function=ioctl.index('V4L2_DEV_DEBUG_STREAMING')<ioctl.index('static int check_array_args')<ioctl.index('trace_v4l2_dqbuf'),
      pix_line3_rdi_line0='VFE_LINE_PIX = 3' in header_vfe and 'VFE_LINE_RDI0 = 0' in header_vfe,
      register_name_uses_line='MSM_VFE_NAME, vfe->id, "video", i' in vfe,
      pix_links_registered_node='&sd->entity, MSM_VFE_PAD_SRC' in vfe and '&video_out->vdev.entity, 0' in vfe,
      image_from_adjacent_nv12='device.formats().count(V4L2PixelFormat(V4L2_PIX_FMT_NV12))' in pipeline and 'endpoint.image = other' in pipeline,
      full_qbuf_call_bracket='EventType::FullQbufBegin,request,ife' in pipeline and 'int ret = d->image_->queueBuffer(ife)' in pipeline,
      full_dq_at_image_callback='void CamssVfeData::imageReady(FrameBuffer *buffer)\n{\n traceFull(camss_diag::EventType::FullDq' in pipeline,
      kernel_timeval_truncates='v4l2_buffer_set_timestamp' in stamp and ('/ 1000' in stamp or 'NSEC_PER_USEC' in stamp),
      userspace_timeval_reconstruction='+ buf.timestamp.tv_usec * 1000ULL' in userspace,
      m2m_copy_timestamp_documented='V4L2_BUF_FLAG_TIMESTAMP_COPY' in userspace)
    assert all(source_checks.values()),source_checks
    inspection=load(HERE.parent/'kernel457/source-inspection.json')
    actual_manifest=load(P/'kernel452/runtime-collected-r2/manifest.json')
    assert all(actual_manifest[name+'.ko']==value for name,value in inspection['modules441'].items())
    private=dict(common_start_ns=common_start,common_end_ns=common_end,stop_begin_ns=stop,
       owner=owner,buffer_indices=buffer_indices,qbuf_pairs=q_pairs,full_done_dq_callback_chains=chains,
       full_tail_event_counts=collections.Counter(e['event'] for e in full_tail),ranges_before_stop=ranges,
       latencies=dict(done_to_dq=latency([c['done_to_dq_ns'] for c in chains]),
                      dq_to_callback=latency([c['dq_to_callback_ns'] for c in chains])),source_checks=source_checks,
       kernel_timestamp_and_callback_clocks_never_subtracted=True)
    write('runtime-pairing-private.json',private)
    sources_result=load(OUT/'runtime-source-audit-private.json')
    assert all(row['equal'] for row in sources_result['files'] if row['cached457_sha256'])
    assert frozen_before=={name:sha(HERE/name) for name in frozen_names}
    public=dict(stage=459,passed=True,scope='offline audit of captured r2 trace and common complete tail',
       no_phone_sdk_build_or_source_changes=True,frozen_seven_files_unchanged=True,
       inputs=dict(trace_sha256=sha(raw),state_sha256=sha(TRACE/'state.json'),csv_sha256=sha(CSV),
                   controller_live2_sha256=sha(OUT/'controller-live-2-private.json'),
                   stats_sha256={str(cpu):sha(TRACE/f'stats-private-1-cpu{cpu}.txt') for cpu in state['possible_cpus']}),
       kernel_trace=dict(retained=len(events),written=int(header[2]),overwritten=sum(s['overrun'] for s in stats),
          whole_session_lossless=False,event_counts={**dict(counts),**{name:counts[name] for name in ['v4l2_qbuf','v4l2_dqbuf']}},
          per_cpu=[{key:s[key] for key in ['cpu','entries','overrun','commit overrun','dropped events','read events']} for s in stats],
          online_cpus_unchanged=True,clock='mono',text_resolution_ns=1000,non_consuming_export_complete=True),
       userspace_csv=dict(total=csv_summary['total'],retained=csv_summary['retained'],overwritten=csv_summary['overwritten'],
          clock_errors=csv_summary['clock_errors'],q_underflows=csv_summary['q_underflows'],complete_footer=True),
       filter_diagnosis=dict(actual_v4l2_events_retained=0,configured_minor=0,configured_target='VFE0 RDI0',
          full_node_from_matching_source_and_actual_inventory='video3, minor3',source363_and_cached457_v4l2_equal=True,
          ioctl_trace_calls_have_no_debug_gate=True,full_minor_trace_emission_not_tested=True,
          future_selection_requires_current_topology_and_open_fd=True),
       common_complete_tail=dict(seconds=(common_end-common_start)/1e9,covers_all_possible_cpu_overrun_boundaries=True,
          csv_full_success_dq=len(csv_dq),single_causal_owner=True,timestamp_only_ambiguous=sum(len(x['candidates'])>1 for x in matches),
          done_dq_callback_chains=len(chains),full_qbuf_call_brackets=len(q_pairs),buffer_index_mapping_count=len(buffer_indices),
          full_tail_event_counts=dict(private['full_tail_event_counts']),before_stop_ranges=ranges,
          approximate_trace_to_trace_and_trace_to_callback_latencies=private['latencies'],
          payload_and_callback_timestamps_never_subtracted=True,not_hardware_fifo_counts=True,
          no_root_cause_or_long_term_drop_fix_claim=True),
       lifecycle=dict(instance_cleaned=True,controller_worker_exited=True,remaining_instances_display_radio=True,
          global_display_radio_selected_controls_unchanged=True,
          later_usb_replug_and_whole_phone_health_outside_this_audit=True),
       source363=sources_result,source_checks=source_checks,private_pairing_sha256=sha(OUT/'runtime-pairing-private.json'),
       checker_sha256=sha(__file__))
    (HERE/'runtime-trace-validation.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(events=len(events),counts=counts,common_seconds=(common_end-common_start)/1e9,
       full_chains=len(chains),qbuf_brackets=len(q_pairs),pool_indices=len(buffer_indices),ranges=ranges,latencies=private['latencies'])),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--sources']:sources()
    elif sys.argv[1:]==['--audit']:audit()
    elif sys.argv[1:]==['--all']:sources();audit()
    else:raise SystemExit('Use --sources, --audit or --all; cached evidence only, no device calls')
