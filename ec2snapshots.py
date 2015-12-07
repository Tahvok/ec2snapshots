#!/usr/bin/env python2
from __future__ import print_function
import argparse
import datetime
import pytz
# Import Session from boto3
from boto3.session import Session


class Volumes(object):
    """Amazon ec2 volumes

    """

    def __init__(self, ec2, backup_word, check):
        self.check = check

        self.ec2 = ec2

        self.backup_word = backup_word

        self.backup_volumes = self.get_backup_volumes()

    def get_backup_volumes(self):
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

        print('Volume Ids that snapshots will be created for:')

        for volume in self.backup_volumes['Volumes']:

            volume_id = volume['VolumeId']

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
                                'Value': 'ec2backup - ' + volume_id
                            },

                        ]
                )

            else:
                print(volume_id)


class Snapshots(object):
    def __init__(self, ec2, backup_volumes, backup_word, check):
        self.check = check

        self.backup_volumes = backup_volumes

        self.ec2 = ec2

        self.backup_word = backup_word

        self.backup_snapshots = self.get_snapshots()

    def get_snapshots(self):
        if hasattr(self, 'backup_snapshots'):
            return self.backup_snapshots

        else:
            volume_ids = []

            for volume in self.backup_volumes['Volumes']:
                volume_ids.append(volume['VolumeId'])

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
        if backup_snapshots is None:
            backup_snapshots = self.backup_snapshots

        my_date = datetime.datetime.utcnow()
        my_date = my_date.replace(tzinfo=pytz.utc)

        for snapshot in backup_snapshots['Snapshots']:
            snapshot_age = my_date - snapshot['StartTime']

            if days < snapshot_age.days:
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

                else:
                    self.ec2.delete_snapshot(
                        SnapshotId=snapshot['SnapshotId'])
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

    my_volumes = Volumes(EC2, args.word, args.check)

    my_volumes.run_backup()


#    my_snapshots.get_snapshots()

    if args.days is not None:
        my_snapshots = Snapshots(EC2, my_volumes.get_backup_volumes(),
                                 args.word, args.check)

        my_snapshots.delete_snapshots(args.days)
