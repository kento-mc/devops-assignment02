#!/usr/bin/env python3
import subprocess
import sys

ip = sys.argv[1]
sshToServer = 'ssh -o StrictHostKeyChecking=no -A ec2-user@' + ip
cdRun = " \"cd donation-web-10; node index.js\""
#startMongo = " \"sudo mongod -dbpath db --bind_ip_all\""
#subprocess.run(sshToServer + killMongo, shell=True)
subprocess.run(sshToServer + cdRun, shell=True)

