"""Recover a shared camera pool through normal suspend/renegotiation on peer loss."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';p=W/'pipewire-1.6.9/src/pipewire/impl-port.c'
s=(P/'broadcast-core-r1-source-private.c').read_text();assert 'broadcast_owner' not in s
needle='''		pw_impl_port_set_param(port, SPA_PARAM_Format, 0, NULL);
	}
	return res;
}

static int check_properties'''
assert s.count(needle)==1
s=s.replace(needle,'''\t\tpw_impl_port_set_param(port, SPA_PARAM_Format, 0, NULL);
	} else if (port->direction == PW_DIRECTION_OUTPUT && port->node &&
			SPA_CONTAINER_OF(port, struct impl, this)->reliable_broadcast) {
		/* Busy metadata is shared across processes. A lost consumer may
		 * leave a reference behind. Suspend and renegotiate the pool rather
		 * than guessing which other consumers still own its memory. */
		struct pw_impl_node *node = port->node;
		pw_log_info("%p: rebuild camera pool after consumer removal", port);
		int suspended = pw_impl_node_set_state(node, PW_NODE_STATE_SUSPENDED);
		if (suspended < 0)
			return suspended;
		pw_context_recalc_graph(node->context, "camera consumer removed");
	}
	return res;
}

static int check_properties''')
p.write_text(s)
orig=(SDK/'work/pipewire262/pipewire-1.6.9/src/pipewire/impl-port.c').read_text()
(R/'core-broadcast-reconfigure-candidate.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
(P/'reconfigure-core-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2000:]
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-reconfigure-candidate.so')
report=dict(compiled=True,core_sha256=hashlib.sha256((P/'libpipewire-reconfigure-candidate.so').read_bytes()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-broadcast-candidate.so').read_bytes()).hexdigest(),busy_counters_never_reset=True,no_system_deployment=True)
(R/'reconfigure-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
