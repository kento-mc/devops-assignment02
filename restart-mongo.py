#!/usr/bin/env python3
import subprocess
import sys

bastionIP = sys.argv[1]
sshToDB = 'ssh -o StrictHostKeyChecking=no -A ec2-user@' + bastionIP + ' ssh -o StrictHostKeyChecking=no -A ec2-user@10.0.1.197'
killMongo = " \"sudo pkill mongod\""
startMongo = " \"sudo mongod -dbpath db --bind_ip_all\""
subprocess.run(sshToDB + killMongo, shell=True)
subprocess.run(sshToDB + startMongo, shell=True)
