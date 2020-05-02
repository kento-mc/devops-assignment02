#!/usr/bin/env python3
import boto3
import os
import sys
import subprocess

ec2 = boto3.resource('ec2')
asClient = boto3.client('autoscaling')

# TODO check for nat gateway. create one if not present.
# TODO check for load balancer. create one if not present.


# Retreive most recent EC2 Amazon Linux 2 AMI for bastion server
amiCmd = "aws ec2 describe-images --owners amazon --filters 'Name=name,Values=amzn2-ami-hvm-2.0.????????.?-x86_64-gp2' 'Name=state,Values=available' --query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' --output text"

bastionAMI = subprocess.getoutput(amiCmd)
dbAMI = 'ami-0e9ef911b46b19098'

# spin up new ec2 instance and configure db server
bastionInstance = ec2.create_instances(
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
)

# spin up new ec2 instance and configure bastion server
# TODO set private ip explicitely
dbInstance = ec2.create_instances(
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

print('')
print('New DB server and bastion spinning up...')
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

dbInstance[0].reload()
bastionInstance[0].reload()
print('')
print('New DB instance running: ' + dbInstance[0].instance_id)
print('New bastion instance running: ' + bastionInstance[0].instance_id)

# Capture user input for auto-scaling capacity
desired = 0
minSize = 0
maxSize = 0

print('')
while True:
    ans = input('Please enter the desired instance capacity: ')
    try:
        desired = int(ans)
        if desired < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must be a positive integer. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must be a positive integer. Try again!")    

print('')
while True:
    ans = input('Please enter the minimum number of instances: ')
    try:
        minSize = int(ans)
        if minSize < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must be a positive integer. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must be a positive integer. Try again!")    

print('')
while True:
    ans = input('Please enter the maximum number of instances: ')
    try:
        maxSize = int(ans)
        if maxSize < 0:  # if not a positive int print message and ask for input again
            print("Sorry, input must be a positive integer. Try again!")
            continue
        break
    except ValueError:
        print("Sorry, input must be a positive integer. Try again!")    

response = asClient.update_auto_scaling_group(
    AutoScalingGroupName='A02-asg',
    LaunchConfigurationName='A02-lc02',
    MinSize=minSize,
    MaxSize=maxSize,
    DesiredCapacity=desired
)

print('')
print('')

