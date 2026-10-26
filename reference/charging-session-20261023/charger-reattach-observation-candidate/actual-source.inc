	source = c->sample.online ? 1 : !ret && c->sample.valid ? 0 : -1;
	sm_reattach_source(&c->reattach, now, source);
