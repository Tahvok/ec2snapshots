#!/usr/bin/env python2
from __future__ import print_function
import boto3
import argparse
# Import Session from boto3
from boto3.session import Session

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-p", "--profile", type=str,
                    help="specify profile to use", default='default')
parser.add_argument("-r", "--region", type=str,
                    help="specify region to use", default='us-east-1')
parser.add_argument("-c", "--check", action="store_true", 
                    help="run in test mode", default=False)
parser.add_argument("-w", "--word", type=str, 
                    help="specify the word to search for", default='daily')
args = parser.parse_args()

# Create a new Session with given profile
session = Session(profile_name=args.profile)

# Create ec2 object with given region
ec2 = session.client('ec2', region_name=args.region)

# Get all volumes from ec2
volumes = ec2.describe_volumes()

# Loop through all volumes
for volume in volumes['Volumes']:
    
    # Check if Tags exist
    if 'Tags' in volume:

        # Set volume name to volume id
        volume_name = volume['VolumeId']

        # Loop all tags
        for tag in volume['Tags']:

            # Assign correct volume name if we found one
            if 'Name' in tag['Key']:
                volume_name = tag['Value']

            # Do backups flag
            do_backup = False

            # Lowercase the Value
            value = tag['Value'].lower()

            # Check if Value contains the backup word
            if args.word in value:
                    # set to True as the word was found
                    do_backup = True
                    break

        # Only print the message if --check is set
        if do_backup and args.check:
            print("Check " + volume_name + ": '" + 
                    args.word + "' was found in tag, will create backup."
                )

        # Create the snapshot otherwise
        elif do_backup:
            # Create snapshot
            result = ec2.create_snapshot(
                    VolumeId=volume['VolumeId'],
                    Description='Scheduled Snapshot [' +
                                volume['VolumeId'] +
                                '] - ec2backup'
                )

            # Create tags
            ec2.create_tags(
                    Resources=[
                        result['SnapshotId'],
                        ],
                    Tags=[
                        {
                            'Key': 'Name',
                            'Value': 'ec2backup - ' + volume_name
                        },
                        
                    ]
                    )

        # Print the message if --check is set and no 'word' found
        elif args.check:
            print("Check " + volume_name + ": '" + 
                    args.word + "' was NOT found in the tags, will NOT create backup."
                )

    # If no tags were found and --check is set
    elif args.check:
        print("Check " + volume_name + 
                ": no tags were found. Will NOT create backup."
        )

