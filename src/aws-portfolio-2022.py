# Import boto3, os, json, logging, and botocore.exceptions modules
import os
from time import sleep
import boto3
import json
import datetime
import logging
import typing
from botocore.exceptions import ClientError

profiles = boto3.session.Session().available_profiles


# TODO: Add option for different profiles
if len(profiles) > 0:
    session = boto3.session.Session(profile_name=profiles[0])
else:
    print("Please enter your profile credentials by running aws configure ")
    quit()

# TODO: Add option for different region
boto_client = boto3.client('ec2')
ec2_resource = boto3.resource('ec2', region_name='us-east-1')


def getInstanceIds(instanceName: typing.Optional[str] = None):
    '''
        Get a specific instance id if given a name or all instance ids in the users account

        Arguments: \n

        instanceName: Optional[String]

        Returns: \n
        List -- Instance ids \n
        or \n
        String -- Instance id \n
    '''

    instances = []
    for instance in ec2_resource.instances.all():
        instances.append(instance.id)
        if instanceName is not None:
            tags = ec2_resource.Instance(instance.id).tags
            if tags[0]["Value"] == instanceName:
                return instance.id

    if instanceName is None:
        return instances
    else:
        print("Id for that name not found")


def verifyInstanceName(instanceName: str):
    '''
        Checks to check if the instance name is valid

        Arguments: \n
        checkName -- String

        Returns: \n
        Bool -- True if name is already taken, otherwise returns False
    '''

    # TODO: Add more name verification checks
    instances = list(ec2_resource.instances.all())
    if instances:
        for instance in instances:
            tags = ec2_resource.Instance(instance.id).tags
            if tags[0]["Value"] == instanceName:
                return True  # Name already exists
            else:
                return False  # Name does not exist
    else:
        return False  # No current instances found name is not taken


def findOrCreateKeyPair(instanceName: str):
    '''Create a new KeyPair for your instance and returns the name of the key pair'''
    try:
        key_pairs = boto_client.describe_key_pairs()
        for key in key_pairs['KeyPairs']:
            if key['KeyName'] == f'{instanceName}KeyPair':
                print("Key already exists")
                return f'{instanceName}KeyPair'
        key_pair = ec2_resource.create_key_pair(
            KeyName=f'{instanceName}KeyPair')
        file = open(f'{instanceName}KeyPair.pem', 'w')
        file.write(key_pair.key_material)
        # TODO: Check for a key pair file in the directory
        # TODO: Add date to key pair name

        return f'{instanceName}KeyPair'
    except ClientError as e:
        print(e)


def createSecurityGroup(instanceName: str):
    '''Create a security group with ssh access, returns the id of the security group'''

    # Try to create a security group with ssh access
    try:
        security_group = boto_client.create_security_group(
            Description=f'Security Group for {instanceName}',
            GroupName=f'{instanceName}SecurityGroup')

        security_group_id = security_group['GroupId']

        data = boto_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 22,
                            'ToPort': 22, "IpRanges": [{'CidrIp': '0.0.0.0/0'}]}]
        )

        return security_group_id
    except ClientError as e:
        print(e)


def startEC2Instance(instanceName=None):
    '''Start a new instance with the specified name'''
    # If name is not passed in function call as user for instance name
    if instanceName is None:
        instanceName = input(
            "Please enter the name for your instance: ").lower()

    # Loop to keep asking for instance name if it is invalid
    while True:
        # Check if the name already exists
        if verifyInstanceName(instanceName) is False:
            # If the instance name is valid

            # Create a key_pair
            keyPairName = findOrCreateKeyPair(instanceName)

            # Create security group
            security_group_id = createSecurityGroup(instanceName)

            # Create the instance
            # TODO: Add variable to ask for users choice in InstanceType
            instances = ec2_resource.create_instances(
                ImageId='ami-0022f774911c1d690',
                MinCount=1,
                MaxCount=1,
                InstanceType='t2.micro',
                KeyName=keyPairName,
                TagSpecifications=[
                    {'ResourceType': 'instance',
                     # TODO Append datetime to the instance name, optionally if user requests it.
                     'Tags': [{'Key': 'Name', 'Value': f'{instanceName}'}]
                     }],
                SecurityGroupIds=[security_group_id]
            )
            checkUntilRunning(instanceName)
            break
        else:
            instanceName = input(
                'Name was already taken, please enter a new name: ').lower()


def checkInstanceStatus(instanceName: typing.Optional[str] = None, instanceId: typing.Optional[str] = None) -> str | None:
    '''
        Checks the state of a given instance name or id and returns it

        Arguments: \n
        instanceName: Optional[str]
        instanceId: Optional[str]

        Returns: \n
        str -- State of the instance
    '''
    if instanceName is not None:
        instanceId = getInstanceIds(instanceName)
    if instanceId is not None:
        state = ec2_resource.Instance(instanceId).state
        return state["Name"]
    else:
        print('instance name or id not given')


def checkUntilRunning(instanceName: str, timeout: typing.Optional[int] = 10):
    '''
        Checks the state of the instance until it is running, best used after you start a new instance.

        Arguments: \n
        instanceName: str
        timeout: Optional

        Returns: \n
        Bool -- True if the instance is running, False if it doesn't run after a timeout.
    '''
    # TODO: Add all status match cases?
    # 0 : pending
    # 16 : running
    # 32 : shutting-down
    # 48 : terminated
    # 64 : stopping
    # 80 : stopped
    sleep(1)
    instanceId = getInstanceIds(instanceName)
    instance = ec2_resource.Instance(instanceId)
    publicIP = instance.public_ip_address.replace('.', '-')

    for i in range(0, timeout):
        status = checkInstanceStatus(instanceId=instanceId)
        match status:
            case "running":
                print(
                    f'EC2 Instance is running, you can connect to it with this command: \nssh -i "{instanceName}KeyPair.pem" ec2-user@ec2-{publicIP}.compute-1.amazonaws.com')
                return True
            case _:
                print(
                    f'EC2 Instance is not running, the current state is {status}...')
                sleep(10)
    return False


if __name__ == '__main__':
    print("Main program")
    startEC2Instance()

    # TODO: Properly format all docstrings
    # TODO: Add more user variables: Region, InstanceSize, AMI, ???
    # TODO: Remove unused imports
    # TODO: Add type annotation to every function
    # TODO: Add multipledispatch?
    # TODO: Film loom video
