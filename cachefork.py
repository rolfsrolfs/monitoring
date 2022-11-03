#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 
# If your script get timeout because it uses long time to run, maybe more time than your system (ex monitoring) allows, 
# this cachefork script will fork a process that updates local cache that holds the output from your script while it shows the last
# updated cache and exit-code.
# 
# requires python > 3.2 because of subprocess.Popen( ... start_new_session=True)
# 
# usage:
#   /full/path/to/cachefork.py /full/path/to/<your_script>.[sh/py/pl/ext] [your script parameters]
# 
#
# 
# WORKFLOW:
#   if cache is old and needs refresh:
#       fork a process that updates cache + continue below
#   if really old cache:
#       exit(100)  - while we wait for newer updated cache, exit 100
#   if cache is good (not old):
#       fil_stdout to stdout
#       fil_stderr to stderr
#       exit with exitcode that the parameter script gave.

import os
import sys
import subprocess
import time
import hashlib
import random
import re

debug = False
# debug = True
argremove = 1

py3 = "python3"

cachemaxperiod = 600  # in seconds: 600 = 10 min
cacheperiod = 30  # seconds cache minimum this period (No forking before this runs)
cache_dir = "/tmp/cachefork"

if len(sys.argv) > 1 and sys.argv[1] == '0':
    argremove += 1

argsleft = sys.argv[argremove:]
if (len(sys.argv) < 2) or ( len(sys.argv) >= 2 and sys.argv[1] == '-h'):
    if len(sys.argv) > 1 and sys.argv[1] == '-h':
        argremove += 1
    sys.stderr.write(f'using character 0 for background fork process\n')
    sys.stderr.write(f'Usage: {sys.argv[0]} [-h|-s] <command to cache (execute with args)>\n')
    sys.exit(98)

dry_run = False
argsleft = sys.argv[argremove:]
if len(argsleft) >= 1 and (argsleft[0] in ['--dryrun', '--dry-run', '--status', '-s']):
    argremove += 1
    print(f"Status for files... DRY-RUN, no forking.. no executing script... (-s|--status|--dryrun)")
    debug = True
    dry_run = True

if not os.path.isdir(cache_dir):
     os.makedirs(cache_dir)

now = int(time.time())

last_complete = 0
last_start = 0
command = sys.argv[argremove:]

str_command = " ".join(command).encode()
basecmd = str(os.path.basename(str_command)[0:30].decode()).replace(' ', "_")
cmdprefix = "".join(re.findall(re.compile(r"[a-zA-Z0-9:_,.-]", re.IGNORECASE), basecmd))

hasher = hashlib.md5()
hasher.update(str_command)
basefile = cmdprefix + "-" + hasher.hexdigest()
f = cache_dir + os.sep + basefile

mother_pidfile = f + '-runcached.pid'
child_pidfile = f + '-child.pid'
child_child_pidfile = f + '-child-child.pid'

fil_stdout = f + '.stdout'
fil_stderr = f + '.stderr'

exitcodefile = f + '.exitcode'
commandfile = f + '.cmd'


if debug:
	print("DEBUG enabled, extra output")
	print("Files used with these parameters:")
	print(f"  pid-files: mother {mother_pidfile} 1st child {child_pidfile} 2nd child: {child_child_pidfile}")
	print(f"  output files: stdout: {fil_stdout} stderr: {fil_stderr} exitcodefile: {exitcodefile}")
	print(f"  commandfile: {commandfile}")

def getdiff_file(file):
    stamp = 0
    if os.path.isfile(file) and os.access(file, os.R_OK):
        try:
            stamp = int(os.path.getmtime(file))
        except Exception as e:
            if debug:
                print(f"got exception {e}")
            stamp = 0
    return now - stamp


# command with 0 and script and arguments runs, sends output to file
def runit(cmd, exitcodefile, cmdfile):
    print(f"Running {cmd} into {fil_stdout}.tmp.{now}")
    f_stdout = open(f"{fil_stdout}.tmp.{now}", 'w')
    if fil_stdout != fil_stderr:
        f_stderr = open(f"{fil_stderr}.tmp.{now}", 'w')
    else:
        f_stderr = f_stdout
    print(f"cmd: {cmd}")
    p = subprocess.Popen(" ".join(cmd), stdout=f_stdout, stderr=f_stderr, shell=True)
    p.communicate()
    with open(child_child_pidfile, 'w') as f:
        f.write(str(p.pid))
    f_stdout.close()
    os.rename(f"{fil_stdout}.tmp.{now}", f"{fil_stdout}")
    if fil_stdout != fil_stderr:
        f_stderr.close()
        os.rename(f"{fil_stderr}.tmp.{now}", f"{fil_stderr}")

    exitcode = p.returncode
    with open(cmdfile, 'w') as f:
        f.write(str(cmd))
    with open(exitcodefile, 'w') as f:
        f.write(str(exitcode))

# If i am the fork: just run the command. 0 at sys.argv[1] defines this
if len(sys.argv) > 1 and sys.argv[1] == '0':
    runit(command, exitcodefile, commandfile)

# last_complete is defined by the timestamp on exitcodefila if it exists.
# exitcodefile is created at the end after the script completed running
# last_start is defined by the timestamp on the child_pidfile when tit starts
diff_complete = getdiff_file(exitcodefile)
diff_start = getdiff_file(child_pidfile)

# If main process:
if len(sys.argv) > 1 and sys.argv[1] != '0':
    # print(f"{diff_complete=} {diff_start=} ")
    if debug:
	    print(f"diff_complete={diff_complete} diff_start={diff_start} ")

    if diff_complete > cacheperiod and diff_start > cacheperiod:
        if debug:
            print("forking subprocess..")
            print([py3, os.path.realpath(__file__), '0', " ".join(command)])
        # start_new_session forks the process. requires python > 3.2
        if not dry_run:
            p = subprocess.Popen([py3, os.path.realpath(__file__), '0', " ".join(command)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with open(child_pidfile, 'w') as f:
                f.write(str(p.pid))
            if debug:
                # print(f"{p.pid=} {p.returncode=} {p.stderr=} {p.stdout=}")
                print(f"p.pid={p.pid} p.returncode={p.returncode} p.stderr={p.stderr} p.stdout={p.stdout}")
            # os.getsid(p.pid)

# if cache is good (not really old), read the cache files and exit with the original script exitcode.
if diff_complete <= cachemaxperiod:
    with open(fil_stdout, 'r') as f:
        sys.stdout.write(f.read())
    with open(fil_stderr, 'r') as f2:
        sys.stderr.write(f2.read())
    if os.path.isfile(exitcodefile):
        with open(exitcodefile, 'r') as fe:
            try:
                sys.exit(int(fe.read()))
            except Exception as e:
                # sys.stderr.write(f"Exception on reading and converting {exitcodefile=} to int() {e}")
                sys.stderr.write(f"Exception on reading and converting exitcodefile={exitcodefile} to int() {e}")
                sys.exit(99)
    else:
        # no exitcodefile
        sys.exit(102)


# if nothing else...
print("WARNING - waiting for cache refresh or something is wrong.")
sys.exit(100)
