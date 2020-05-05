#!/usr/bin/env python3
import boto3
import os
import sys
import subprocess
import socket

client = boto3.client('ec2')
clientELB = boto3.client('elbv2')

# declare variables to store instance ip address, or array of ip addresses
public_ip = ''
instIps = []

# Command for ssh into instances
sshCmd = "ssh -o StrictHostKeyChecking=no -A ec2-user@"

if len(sys.argv) == 1:
    menu = True
    while menu:
        print('')
        print('Would you like to monitor a single instance, or all instances behind a load balancer?')
        print('---------------------')
        print('  1) single instance')
        print('  2) all instances')
        print('------')
        ans = input('==> ')
        if ans == '1':
            excThrown = False
            while True:
                print('')
                print('Please enter the public IP address of the instance, or enter 0 to go back.')
                print('------')
                ans = input('==> ')
                if excThrown == True and ans == '0':
                    break
                try:
                    socket.inet_aton(ans) # validate ip address format
                    public_ip = ans
                    menu = False
                    break
                except Exception as error:
                    excThrown = True
                    print('')
                    print('Invalid entry.')
        elif ans == '2':
            print('')
            print('Please enter the name of the load balancer.')
            while True:
                print('------')
                ans = input('==> ')
                if ans == '0':
                    break
                try:
                    elbArn = clientELB.describe_load_balancers(Names=[ans])['LoadBalancers'][0]['LoadBalancerArn']
                    tgtArn = clientELB.describe_target_groups(LoadBalancerArn=elbArn)['TargetGroups'][0]['TargetGroupArn']
                    targets = clientELB.describe_target_health(TargetGroupArn=tgtArn)['TargetHealthDescriptions']
                    for target in targets:
                        instId = target['Target']['Id']
                        instance = client.describe_instances(InstanceIds=[instId])
                        instIps.append(instance['Reservations'][0]['Instances'][0]['PublicIpAddress'])
                    menu = False
                    break
                except Exception as error:
                    print('')
                    print('Could not retrieve load balancer.')
                    print('Please enter name again, or enter 0 to go back.')         
            print('')
            print('This load balancer currently has ' + str(len(instIps)) + ' instances running.')
            print('')
            print('Loading instance data...')
        else:
            print('')
            print('Invalid entry.')
else:
    try:
        socket.inet_aton(sys.argv[1]) # validate ip address format
        public_ip = sys.argv[1]
    except Exception as error:
        print('')
        print('Passed argument must be a valid IP address. Please try again.')

if len(instIps) == 0:
    instIps.append(public_ip)

for ip in instIps:
    # Enable custom metrics for the instance
    runMem = " ./mem.sh"
    runMemCmd = sshCmd + ip + runMem
    try:
        subprocess.run(runMemCmd, shell=True, stderr=subprocess.DEVNULL)
    except Exception as error:
        print('')
        print('Connection error. Please try again.')

# Save commands for retrieving individual metrics to variables
used_memory=" free -m | awk 'NR==2{printf \"%.2f\t\", $3*100/$2 }'"
tcp_conn=" netstat -an | wc -l"
tcp_conn_port_80=" netstat -an | grep 80 | wc -l"
tcp_conn_port_443=" netstat -an | grep 443 | wc -l"
users=" uptime | awk '{ print $4 }'"
io_wait=" iostat | awk 'NR==4 {print $5}'"

print('')
print(' -------------------------------------')
print('|  App Instance Performance Snapshot  |')
print(' -------------------------------------')
print('')

instCount = 1

for ip in instIps:
    
    # Construct ssh commands
    usedMemCmd = sshCmd + ip + used_memory
    usedMemOutput = subprocess.getoutput(usedMemCmd)
    tcpConnCmd = sshCmd + ip + tcp_conn
    tcpConnOutput = subprocess.getoutput(tcpConnCmd)
    tcpConn80Cmd = sshCmd + ip + tcp_conn_port_80
    tcpConn80Output = subprocess.getoutput(tcpConn80Cmd)
    tcpConn443Cmd = sshCmd + ip + tcp_conn_port_443
    tcpConn443Output = subprocess.getoutput(tcpConn443Cmd)
    usersCmd = sshCmd + ip + users
    usersOutput = subprocess.getoutput(usersCmd)
    ioWaitCmd = sshCmd + ip + io_wait
    ioWaitOutput = subprocess.getoutput(ioWaitCmd)

    print(' Instance ' + str(instCount) +'/' + str(len(instIps)) + '   -   IP: ' + ip)
    print(' -------------------------------------')
    print('   Memory Usage:' + '\t' + usedMemOutput.strip() + '%')
    print('   TCP Connections:' + '\t' + tcpConnOutput.strip())
    print('   HTTP Connections:' + '\t' + tcpConn80Output.strip())
    print('   HTTPS Connections:' + '\t' + tcpConn443Output.strip())
    print('   Current Users:' + '\t' + usersOutput.strip())
    print('   IO Wait time:' + '\t' + ioWaitOutput.strip() + '%')
    print(' -------------------------------------')
    print('')

    instCount += 1

print('Good bye!')
print('')
