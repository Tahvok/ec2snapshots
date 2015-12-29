#!/usr/bin/env python2
"""Script for creating snapshots of EC2 volumes.

This script is making use of configured `.aws/config` and `.aws/credentials`.
Ensure to configure those correctly with IAM.
"""

from __future__ import print_function
import argparse
import datetime
import pytz
# Import Session from boto3
from boto3.session import Session

__author__ = "Albert Mikaelyan"
__licence__ = "MIT"
__version__ = "1.0"


class Volumes(object):
    """Amazon EC2 backup volumes

    Attributes:
        check (bool): If the object is in check mode.
        ec2 (boto3.client('ec2)): EC2 client.
        backup_word (str): Backup word in tags.
        backup_volumes (dict): Backup volumes, using word, from EC2.

    """

    def __init__(self, ec2, backup_word, check):
        """__init__ backup volumes.

        Args:
            ec2: Ec2 client.
            backup_word: The word in volumes' tags that indicates the backup.
            check: Pass True to only check what will be done.
        """
        self.check = check

        self.ec2 = ec2

        self.backup_word = backup_word

        self.backup_volumes = self.get_backup_volumes()

    def get_backup_volumes(self):
        """Get backup volumes from EC2.

        Returns: Dictionary of backup volumes.

        """
        if hasattr(self, 'backup_volumes'):
            return self.backup_volumes

        else:
            return self.ec2.describe_volumes(
                Filters=[
                    {
                        'Name': 'tag-value',
                        'Values': [
                            '*' + self.backup_word + '*',
                        ]
                    },
                ],
            )

    def run_backup(self):
        """Run backup

        Will create ec2 snapshots of the object volumes, and create a tag to
        each of them.
        """

        # Print if --check is set
        if self.check:
            print('Volume Ids that snapshots will be created for:')

        for volume in self.backup_volumes['Volumes']:

            volume_id = volume['VolumeId']
            volume_name = volume_id

            for tag in volume['Tags']:
                if tag['Key'] is 'Name':
                    volume_name = tag['Value']

            # If check is not set, will create snapshots
            if not self.check:
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

            # Else print if --check is set
            else:
                print(volume_id)


class Snapshots(object):
    """Amazon EC2 backup snapshots.

    Attributes:
        check (bool): If the object is in check mode.
        ec2 (boto3.client('ec2)): EC2 client.
        backup_word (str): Backup word in tags.
        backup_volumes (dict): Backup volumes, using word, from EC2.
        backup_snapshots (dict): Backup snapshots, using word and
            backup_volumes, from EC2.
    """

    def __init__(self, ec2, backup_volumes, backup_word, check):
        """__init__ backup snapshots

        Args:
            ec2: Ec2 client.
            backup_volumes: Backup volumes the snapshots created for.
            backup_word: The word in snapshots' tags that indicates backup.
            check: Pass True to only check what will be done.
        """
        self.check = check

        self.ec2 = ec2

        self.backup_word = backup_word

        self.backup_volumes = backup_volumes

        self.backup_snapshots = self.get_snapshots()

    def get_snapshots(self):
        """Get backup snapshots from EC2

        Returns: Dictionary of backup snapshots.
        """
        # If object is already initialized, just return the attribute.
        if hasattr(self, 'backup_snapshots'):
            return self.backup_snapshots

        # Else get the volumes from EC2.
        else:
            # Iterate over backup volumes, and get their IDs.
            volume_ids = []
            for volume in self.backup_volumes['Volumes']:
                volume_ids.append(volume['VolumeId'])

            # Return snapshots from EC2, using volume_ids and backup_word.
            return self.ec2.describe_snapshots(
                Filters=[
                    {
                        'Name': 'volume-id',
                        'Values': volume_ids,
                    },
                    {
                        'Name': 'tag-value',
                        'Values': [
                            '*' + self.backup_word + '*',
                        ]
                    }
                ]
            )

    def delete_snapshots(self, days, backup_snapshots=None):
        """Delete old snapshots.

        Args:
            days: Max number of days that snapshots will live.
            backup_snapshots: Dictionary of snapshots.
                If not specified, will use the snapshots from self.
        """

        # Check if backup_snapshots is specified.
        if backup_snapshots is None:
            backup_snapshots = self.backup_snapshots

        # Get our date.
        my_date = datetime.datetime.utcnow()
        my_date = my_date.replace(tzinfo=pytz.utc)

        # Iterate over backup_snapshots.
        for snapshot in backup_snapshots['Snapshots']:

            # Get the difference between our date and snapshot StartTime date.
            snapshot_age = my_date - snapshot['StartTime']

            # If snapshots are older than our specified days.
            if days < snapshot_age.days:
                # Print if --check is set.
                if self.check:
                    print(
                            'Snapshot [{}] of volume [{}]: '
                            'Will be removed. '
                            'Reason: The snapshot is {} days old, '
                            'which is more than the specified {} days.'
                            .format(snapshot['SnapshotId'],
                                    snapshot['VolumeId'],
                                    snapshot_age.days, days)
                    )

                # Else delete the snapshot.
                else:
                    self.ec2.delete_snapshot(
                        SnapshotId=snapshot['SnapshotId'])

            # Else if snapshots are not older than our specified days.
            # Just print if --check is set.
            elif self.check:
                print(
                        'Snapshot [{}] of volume [{}]: '
                        'Will NOT be deleted. '
                        'Reason: The snapshot is {} days old,'
                        'and is less than the specified {} days.'
                        .format(snapshot['SnapshotId'],
                                snapshot['VolumeId'],
                                snapshot_age.days, days)
                )


if '__main__' == __name__:
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check", action="store_true",
                        help="run in test mode", default=False)
    parser.add_argument("-p", "--profile", type=str,
                        help="specify profile to use", default='default')
    parser.add_argument("-r", "--region", type=str,
                        help="specify region to use", default='us-east-1')
    parser.add_argument("-w", "--word", type=str,
                        help="specify the word to search for", default='daily')
    parser.add_argument("-d", "--days", type=int,
                        help="specify days to preserve the snapshots",
                        default=None)
    args = parser.parse_args()

    # Create a new Session with given profile
    session = Session(profile_name=args.profile)

    # Create ec2 object with given region
    EC2 = session.client('ec2', region_name=args.region)

    # Initiate volumes to backup.
    my_volumes = Volumes(EC2, args.word, args.check)

    # Run backup of my volumes.
    my_volumes.run_backup()

    # Only if days are specified will delete old snapshots.
    if args.days is not None:
        # Initiate snapshots to delete.
        my_snapshots = Snapshots(EC2, my_volumes.get_backup_volumes(),
                                 args.word, args.check)

        # Delete my snapshots
        my_snapshots.delete_snapshots(args.days)
