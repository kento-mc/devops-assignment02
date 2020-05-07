#!/usr/bin/env python3
import boto3
import os
import sys
import subprocess
import webbrowser

ec2 = boto3.resource('ec2')
ec2Client =boto3.client('ec2')
asClient = boto3.client('autoscaling')
clientELB = boto3.client('elbv2')

# TODO check for nat gateway. create one if not present.
# TODO check for load balancer. create one if not present.

# Variables to capture user input for auto-scaling capacity
desired = 0
minSize = 0
maxSize = 0

print('')
while True:
    ans = input('Please enter the desired instance capacity: ')
    try:
        desired = int(ans)
        if desired < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must an integer between 0 and 12. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must an integer between 0 and 12. Try again!")

print('')
while True:
    ans = input('Please enter the minimum number of instances: ')
    try:
        minSize = int(ans)
        if minSize < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must an integer between 0 and 12. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must an integer between 0 and 12. Try again!")

print('')
while True:
    ans = input('Please enter the maximum number of instances: ')
    try:
        maxSize = int(ans)
        if maxSize < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must an integer between 0 and 12. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must an integer between 0 and 12. Try again!")

bastionAMI = 'ami-0cc7a8eddaa88d5bf'
dbAMI = 'ami-0e9ef911b46b19098'
webAMI = 'ami-0c794033068baa237'
dbInstance = {}
bastionInstance = {}
instancePairs = []

print('')
print('Checking App ifrastructure...')

instances = ec2Client.describe_instances()

for inst in instances['Reservations']:
    instanceDetail = []
    instanceDetail.append(inst['Instances'][0]['ImageId'])
    instanceDetail.append(inst['Instances'][0]['InstanceId'])
    instancePairs.append(instanceDetail)

dbFound = False 
for inst in instancePairs:
    if dbAMI in inst:
        dbInstance = ec2.Instance(inst[1])
        instanceState = dbInstance.state['Name']
        if instanceState == 'terminated':
            pass
        elif instanceState == 'shutting-down':
            if type(dbInstance) is list:
                dbInstance[0].wait_until_running(
                    Filters=[
                        {
                            'Name': 'instance-state-name',
                            'Values': [
                                'stopped',
                            ]
                        },
                    ],
                )
            else:
                dbInstance[0].wait_until_running(
                    Filters=[
                        {
                            'Name': 'instance-state-name',
                            'Values': [
                                'stopped',
                            ]
                        },
                    ],
                )
            pass
        elif instanceState == 'running' or instanceState == 'pending':
            dbInstance = ec2.Instance(inst[1])
            dbFound = True
            break
        elif instanceState == 'stopped' or instanceState == 'stopping':
            # start existing db
            try:
                ec2Client.start_instances(InstanceIds=[inst[1]])
            except Exception as error:
                print('')
                print('Error starting DB server:')
                print(error)
            dbInstance = ec2.Instance(inst[1])
            print('')
            print('Starting existing DB server...')
            dbFound = True

if dbFound == False:
    print('')
    print('Spinning up new DB server...')
    try:
        # spin up new ec2 instance and configure db server
        dbInstance = ec2.create_instances(
            ImageId=dbAMI,
            InstanceType='t2.nano',
            KeyName='kchadwick_key',
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=['sg-042e4b564377dd6c7'],
            SubnetId='subnet-0afc8b9a77fb34de5',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'A02 DB server'
                        },
                    ]
                },
            ],
            UserData='''#!/bin/bash
                yum update -y
                yum install httpd -y
                systemctl enable httpd
                systemctl start httpd''',

            PrivateIpAddress='10.0.1.197'
        )
        dbFound = True
    except Exception as error:
        print('')
        print('Error spinning up new DB server:')
        print(error)

if type(dbInstance) is list:
    dbInstance[0].wait_until_running(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running',
                ]
            },
        ],
    )
    dbInstance[0].reload()
    print('')
    print('DB server running: ' + dbInstance[0].private_ip_address)
else:
    dbInstance.wait_until_running(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running',
                ]
            },
        ],
    )
    dbInstance.reload()
    print('')
    print('DB server running: ' + dbInstance.private_ip_address)

bastionFound = False
for inst in instancePairs:
    if bastionAMI in inst and inst:
        bastionInstance = ec2.Instance(inst[1])
        instanceState = bastionInstance.state['Name']
        if instanceState == 'terminated' or instanceState == 'shutting-down':
            pass
        elif instanceState == 'running' or instanceState == 'pending':
            bastionInstance = ec2.Instance(inst[1])
            bastionFound = True
            break
        elif instanceState == 'stopped' or instanceState == 'stopping':
            # start existing bastion
            try:
                ec2Client.start_instances(InstanceIds=[inst[1]])
            except Exception as error:
                print('')
                print('Error starting Bastion server:')
                print(error)
            bastionInstance = ec2.Instance(inst[1])
            print('')
            print('Starting existing Bastion server...')
            bastionFound = True

if bastionFound == False:
    print('')
    print('Spinning up new Bastion server...')
    try:
        # spin up new bastion server
        bastionInstance = ec2.create_instances(
            ImageId=bastionAMI,
            InstanceType='t2.nano',
            KeyName='kchadwick_key',
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=['sg-0d5a827e1e5ecf5c0'],
            SubnetId='subnet-0bc534a86f324e9da',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'A02 bastion'
                        },
                    ]
                },
            ],
        )
        bastionFound = True
    except Exception as error:
        print('')
        print('Error spinning up new Bastion server:')
        print(error)

if type(bastionInstance) is list:
    bastionInstance[0].wait_until_running(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running',
                ]
            },
        ],
    )
    bastionInstance[0].reload()
    print('')
    print('Bastion server running: ' + bastionInstance[0].public_ip_address)
else:
    bastionInstance.wait_until_running(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'running',
                ]
            },
        ],
    )
    bastionInstance.reload()
    print('')
    print('Bastion server running: ' + bastionInstance.public_ip_address)

print('')
print('Configuring DB and web servers...')
waiter = ec2Client.get_waiter('instance_status_ok')
waiter.wait() # wait for completion of status checks

# start fresh mongod process on the DB server
try:
    subprocess.Popen(['./restart-mongo.py', bastionInstance.public_ip_address], shell=False, stdout=subprocess.DEVNULL)
except Exception as error:
    print('')
    print('Error restarting mongod process on DB server.')
    print('Please try running the restart-mongo.py script manually before testing the App.')

# TODO run node on each running web server instance
webInstances = []
for inst in instances['Reservations']:
    if webAMI == inst['Instances'][0]['ImageId'] and inst['Instances'][0]['State'] == 'running':
        webInstances.append(inst['Instances'][0]['PublicIpAddress'])

for ip in webInstances:
    subprocess.Popen(['./restart-node.py', ip], shell=False, stdout=subprocess.DEVNULL)

response = asClient.update_auto_scaling_group(
    AutoScalingGroupName='A02-asg',
    LaunchConfigurationName='A02-lc',
    MinSize=minSize,
    MaxSize=maxSize,
    DesiredCapacity=desired
)

instances = ec2Client.describe_instances()
dbDisplay = ''
basDisplay = ''
webInstDisplay = []
for inst in instances['Reservations']:
    if inst['Instances'][0]['State']['Name'] == 'running':
        if inst['Instances'][0]['ImageId'] == dbAMI:
            dbDisplay = inst['Instances'][0]['PrivateIpAddress']
        elif inst['Instances'][0]['ImageId'] == bastionAMI:
            basDisplay = dbDisplay = inst['Instances'][0]['PublicIpAddress']
        else:
            webInstDisplay.append(inst['Instances'][0]['PublicIpAddress'])

print('')
print(' ---------------------------------------')
print('|      App Infrastructure Snapshot      |')
print(' ---------------------------------------')
print('  DB Server:' + '\t' + '\t' + ' ' + dbDisplay)
print('  Bastion Server:' + '\t' + ' ' + basDisplay)
i = 0
for inst in webInstDisplay:
    print('  Web Server Instance:' + '\t' + ' ' + webInstDisplay[i])
    i += 1
    
print('')
response = clientELB.describe_load_balancers(Names=['A02-lb'])
lbDNS = response['LoadBalancers'][0]['DNSName']

webbrowser.open(lbDNS, new=2)
