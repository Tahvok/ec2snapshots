#!/usr/bin/env python2
from __future__ import print_function
import argparse
# Import Session from boto3
from boto3.session import Session


class Volumes(object):

    def __init__(self, ec2, check):
        self.check = check

        self.ec2 = ec2

        self.volumes = ec2.describe_volumes()

    def get_volumes(self):
        return self.volumes

    def __get_backup_volumes(self, backup_word, volumes=None):
        if volumes is None:
            volumes = self.volumes

        backup_volumes = {}

        # Loop through all volumes
        for volume in volumes['Volumes']:

            # Set volume name to volume id
            volume_name = volume['VolumeId']

            volume_id = volume['VolumeId']

            # Check if Tags exist
            if 'Tags' in volume:

                # Do backups flag
                do_backup = False

                # Loop all tags
                for tag in volume['Tags']:

                    # Assign correct volume name if we found one
                    if 'Name' in tag['Key']:
                        volume_name = tag['Value']

                    # Lowercase the Value
                    value = tag['Value'].lower()

                    # Check if Value contains the backup word
                    if backup_word in value:
                        # set to True as the word was found
                        do_backup = True
                        backup_volumes[volume_id] = volume_name

                        # Print message if --check is set
                        if self.check:
                            print(
                                    "Check " + volume_name + ": '" +
                                    backup_word +
                                    "' was found in tag, will create backup."
                            )
                        break

                # Print the message if --check is set and no 'word' found
                if self.check and not do_backup:
                    print(
                            'Check ' + volume_name + ': \'' +
                            backup_word +
                            '\' was NOT found in the tags, ' +
                            'will NOT create backup.'
                    )

            # If no tags were found and --check is set
            elif self.check:
                print(
                        'Check ' + volume_name +
                        ': no tags were found. Will NOT create backup.'
                )

        return backup_volumes

    def run_backup(self, backup_word, backup_volumes=None):
        if backup_volumes is None:
            backup_volumes = self.__get_backup_volumes(backup_word)

        if not self.check:
            for volume_id, volume_name in backup_volumes.iteritems():
                # Create snapshot
                result = self.ec2.create_snapshot(
                        VolumeId=volume_id,
                        Description='Scheduled Snapshot [' +
                                    volume_id +
                                    '] - ec2backup'
                )

                # Create tags
                self.ec2.create_tags(
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


class Snapshots(object):
    def __init__(self, ec2, check):
        self.volumes = Volumes(ec2, check)

    def print_volumes(self):
        return self.volumes.get_volumes()


# def delete_old_backup(ec2):
    # snapshots = ec2.describe_snapshots()

    # print(snapshots)
#     volumes = Ec2Volumes(ec2)

#     print(volumes.backup_volumes)


if '__main__' == __name__:
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
    EC2 = session.client('ec2', region_name=args.region)

    my_volumes = Volumes(EC2, args.check)

    my_volumes.run_backup(args.word)
