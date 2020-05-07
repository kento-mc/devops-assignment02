#!/usr/bin/env python3
import boto3
import sys
import subprocess
import socket

client = boto3.client('ec2')
clientELB = boto3.client('elbv2')

# declare variable to store list of instance ip addresses
instIps = []

# Command for ssh into instances
sshCmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -A ec2-user@"

if len(sys.argv) == 1:
    menu = True
    while menu:
        print('')
        print('Would you like to monitor a single instance, or all instances behind a load balancer?')
        print('---------------------')
        print('  1) single instance')
        print('  2) all instances')
        print('---------------------')
        print('  0) exit')
        print('------')
        ans = input('==> ')
        if ans == '0':
            print('')
            print('Good bye!')
            print('')
            sys.exit()
        if ans == '1':
            while True:
                print('')
                print('Please enter the public IP address of the instance (or 0 to go back).')
                print('------')
                ans = input('==> ')
                if ans == '0':
                    break
                try:
                    socket.inet_aton(ans) # validate ip address format
                    try:
                        output = subprocess.getoutput(sshCmd  + ans + ' ls')
                        failure = 'Failed to connect to this IP address.'
                        if 'No route to host' in output:
                            print('')       
                            print(failure)
                            break
                        else:
                            instIps.append(ans)
                            print('')
                            print('Loading instance data...')
                    except Exception as error:
                        print('')       
                        print(failure)  
                        break           
                    menu = False
                    break
                except Exception as error:
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
            instPlural = 'instances'
            if len(instIps) == 1:
                instPlural = 'instance'
            print('This load balancer currently has ' + str(len(instIps)) + ' ' + instPlural + ' running.')
            print('')
            print('Loading instance data...')
        else:
            print('')
            print('Invalid entry.')
else:
    try:
        socket.inet_aton(sys.argv[1]) # validate ip address format
        output = subprocess.getoutput(sshCmd  + sys.argv[1] + ' ls')
        failure = 'Failed to connect to this IP address. Please try again'
        if 'No route to host' in output:
            print('')       
            print(failure)
            print('')
            sys.exit()
        else:
            instIps.append(sys.argv[1])
            print('')
            print('Loading instance data...')
    except Exception as error:
        print('')       
        print('Passed argument must be a valid IP address. Please try again.')    
        print('')     
        sys.exit()   

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
print(' ---------------------------------------')
print('|   App Instance Performance Snapshot   |')
print(' ---------------------------------------')
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

    print('  Instance ' + str(instCount) +'/' + str(len(instIps)) + '   |   IP: ' + ip)
    print(' ---------------------------------------')
    print('    Memory Usage:' + '\t' + '     ' + usedMemOutput.strip() + '%')
    print('    TCP Connections:' + '\t' + '     ' + tcpConnOutput.strip())
    print('    HTTP Connections:' + '\t' + '     ' + tcpConn80Output.strip())
    print('    HTTPS Connections:' + '\t' + '     ' + tcpConn443Output.strip())
    print('    Current Users:' + '\t' + '     ' + usersOutput.strip())
    print('    IO Wait time:' + '\t' + '     ' + ioWaitOutput.strip() + '%')
    print(' ---------------------------------------')
    print('')

    instCount += 1

print('Good bye!')
print('')
