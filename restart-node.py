#!/usr/bin/env python3
import subprocess
import sys

ip = sys.argv[1]
sshToServer = 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -A ec2-user@' + ip
cdRun = " \"cd donation-web-10; node index.js\""
subprocess.run(sshToServer + cdRun, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

