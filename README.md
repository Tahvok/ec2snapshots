# ec2snapshots
Creates ec2 snapshots of volumes using keyword in tags, and deletes old snapshots

# Requirements
* Python 2 symlinked to /usr/bin/python2 (should work with python 3 as well, but not tested)
* boto3
* pytz

# Argument defaults
    check = False
    profile = 'default'
    region = 'us-east-1'
    word = 'daily'
    days = None

# Install
    git clone https://github.com/Tahvok/ec2snapshots.git

You need [boto3](https://github.com/boto/boto3) and [pytz](http://pytz.sourceforge.net) modules.
You can install them with:

    pip install -r requirements.txt

Configure boto3 according to: (https://boto3.readthedocs.org/en/latest/guide/quickstart.html#configuration)

# Usage
Create a snapshots using defaults above:

    ./ec2snapshots

Show help:

    ./ec2snapshots -h

Use the profile `second` and region `eu-west-1`:

    ./ec2snapshots --profile second -r eu-west-1

Create snapshots to volumes with tag value `monthly` in sa-east-1, and delete snapshots older than 31 days:

    ./ec2snapshots --region sa-east-1 -word monthly -d 31

You can always specify a `--check` to see what will be done. The script will not create snapshots or delete snapshots if this is specified:

    ./ec2snapshots -d 10 --check

# Help/Contributing
Feel free to contact me on github, submit issues, or pull requests.
