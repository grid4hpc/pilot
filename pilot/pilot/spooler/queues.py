# -*- encoding: utf-8 -*-

import eventlet

operation = eventlet.queue.LightQueue()
run = eventlet.queue.LightQueue()
pause = eventlet.queue.LightQueue()
abort = eventlet.queue.LightQueue()
task = eventlet.queue.LightQueue()
task_poll = eventlet.queue.LightQueue()
delegations = eventlet.queue.LightQueue()
