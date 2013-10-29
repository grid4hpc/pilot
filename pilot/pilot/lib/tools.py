# -*- encoding: utf-8 -*-

from eventlet.green import threading


def communicate_with_timeout(proc, stdin=None, timeout=None):
    """Call proc.communicate() and return after given timeout even if
    process is still not finished.

    @param proc: subprocess.Popen instance
    @param timeout: if None, communicate_with_timeout is equal to proc.communicate()

    @returns tuple(stdout, stderr)
    """
    result = [None, None]
    def waiter():
        result[0], result[1] = proc.communicate(stdin)
    waiting_thread = threading.Thread(target=waiter)
    waiting_thread.setDaemon(True)
    waiting_thread.start()
    waiting_thread.join(timeout)
    return tuple(result)
