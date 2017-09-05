from __future__ import absolute_import
import subprocess

try:
    from core.os.mac._appkit import *
except ImportError:
    pass
    

def get_running_processes():
    pids = []
    program_list = subprocess.Popen('ps -d', shell=True, stdout=subprocess.PIPE).communicate()[0]
    for line in program_list.splitlines():
        pids.append(line.decode())
    output = {line.rsplit()[-1]: line.rsplit()[0] for line in pids}
    return output
