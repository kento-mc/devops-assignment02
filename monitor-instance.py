#!/usr/bin/env python3
import boto3
import os
import sys
import subprocess
import socket

public_ip = ''

if len(sys.argv) == 1:
    print('')
    print('Please enter the public IP address of the instance you would like to monitor.')
    while True:
        ans = input('==> ')
        try:
            socket.inet_aton(ans)
            public_ip = ans
            break
        except Exception as error:
            print('')
            print('Invalid entry. Please enter a valid IP address.')
else:
    public_ip = sys.argv[1]

sshCmd = "ssh -o StrictHostKeyChecking=no -A ec2-user@" + public_ip
command = sshCmd + " \'iostat\'"
output = subprocess.getoutput(command)
print(output)


