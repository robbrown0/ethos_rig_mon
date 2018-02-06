#!/usr/bin/env python
# import required modules
import subprocess
import os
import re
import sys
import argparse
import httplib, urllib
import time
import datetime
import time
import subprocess
import socket

# set a few variables
hashalert = 10  # Set the hashalert variable to the rate in MH/s that you want the flag the GPU as not hashing, and in trun rebooted the rig.  10 MH/s is the default.
hashavgalert = 65 # Set the hashaverage variable to the rate in MH/s that you want the rig to reboot at.  Depends on the rigs total MH/s.
hashalert = format(float(hashalert), '.2f')
hash = None
hashdec = ''
miner_id = ''
varCardList = ''
x = " "
varNotifyCnt = 0
statusmessage = "HASHING AS EXPECTED"
errorstatusmessage = "LOW HASHRATE DETECTED"

"""
# 
# If you find this script beneficial, feel free to donate:  ETH 0xE8cBA305dBAAD26d6C505BC47Ee4fA96616bD52C
#
# The idea of this script was adapted from a published version by Jayd Lawrence at https://gist.github.com/jaydlawrence/5a70cbf868f90bbc4cd7b0913810f310.  While I still use the same implementation of the
# pushover service, I'm not determining hash using the udpate command, I'm parsing the miner log output, and I'm looking at each card as opposed to only the average hash rate.  I've added more easy to read
# log files, as well as log file maintenance.  I also ping an external IP to make sure the miner is on the internet, so it doesn't enter a reboot loop.
#
# Place this file at /home/ethos/ethos_rig_mon.py  (I use WinSCP)
#
# The entries at the bottom of this comment block go into the crontab for the ethos user.
#
# The script usese the Pushover notfication service to notify you of reboots or when a card or the rig are not hashing as expected.
# Replace <app_token> with your app token, eg. curl -s -F "token=as9dv8jaw4e9fasdjgoa2w3t98jawl4" ... in the two lines below that go into the ethos user's crontab.
# replace <user_token> with your user token eg. ... -F "user=rtsfgjsrtjsrtj457ujtfgtwsvka" ...
#
# By placing the below section in the crontab it starts the script and notifies you when EthOS is back up
#
# From a terminal window:  crontab -e
# Press CTRL+V for next page and paste the following two lines.  Please note modify the user and application tokens on BOTH lines.  Exit the crontab, and the script will run every two minutes.
# If the hashalert threshold is crossed a file is written.  The script will run every 2 minutes, and if the hash rate is at or below the hashalert and hashavg alert variables AND the file exists, the rig will be rebooted.
#
# I'm including two lines from my crontab to make sure you understand formatting.  I have modified both of my ID, but you should get the idea.
#@reboot curl -s -F "token=aardkds1zdjxxxt8rn6qqfc1816s6k" -F "user=uqvkvnrbxxxhtt4iap35bzs3n3jy1y " -F "title=RIG - "$(hostname)" - IS NOW ONLINE" -F "message=RIG - "$(hostname)" rebooted and is now online." https://api.pushover.net/1/messages.json
#*/2 * * * *   /usr/bin/python /home/ethos/ethos_rig_mon.py -u uqvkvnrb3mshtxxxap35bzs3n3jy1y -a aardkds1zdjz5xxxrn6qqfc1816s6k >> /home/ethos/ethos_rig_mon.log

@reboot curl -s -F "token=aardkds1zdjxxxx8rn6qqfc1816s6k" -F "user=uqvkvnrbxxxxtt4iap35bzs3n3jy1y " -F "title=RIG - "$(hostname)" - IS NOW ONLINE" -F "message=RIG - "$(hostname)" rebooted and is now online." https://api.pushover.net/1/messages.json
*/2 * * * *   /usr/bin/python /home/ethos/ethos_rig_mon.py -u uqvkvnrbxxxxtt4iap35bzs3n3jy1y -a aardkds1zdjxxxx8rn6qqfc1816s6k >> /home/ethos/ethos_rig_mon.log

 """
# get rig hostname
miner_id = socket.gethostname()

# if the output file does not exist call the script with with log name to generate the output
if not os.path.exists("/home/ethos/ethos_rig_mon.log"):
    os.system("python ethos_rig_mon.py -u uqvkvnrbxxxxtt4iap35bzs3n3jy1y -a aardkds1zdjxxxx8rn6qqfc1816s6k >> /home/ethos/ethos_rig_mon.log") 
    exit()

# if the file has 362 lines (1 run every 2 minutes for 12 hours plus the header, if a previous output is found it is deleted, the output file is renamed to previous_ethos_rig_mon.log, and the script is executed again.
num_lines = sum(1 for line in open('/home/ethos/ethos_rig_mon.log'))
if num_lines >= 362:
    os.remove("/home/ethos/previous_ethos_rig_mon.log") if os.path.exists("/home/ethos/previous_ethos_rig_mon.log") else None
    os.rename("/home/ethos/ethos_rig_mon.log","/home/ethos/previous_ethos_rig_mon.log")
    os.system("python ethos_rig_mon.py -u uqvkvnrbxxxxtt4iap35bzs3n3jy1y -a aardkds1zdjxxxx8rn6qqfc1816s6k >> /home/ethos/ethos_rig_mon.log") 
    exit()

# write header in output file if the file is empty
if os.path.getsize("/home/ethos/ethos_rig_mon.log") <= 0:
    # File is empty, writing header
    print "TIMESTAMP     | HOSTNAME | STATUS  |    HASHRATE    | HASH STATUS"
    print "-----------------------------------------------------------------------------------"

# setup the function to send to the pushover notification service
def pushover_message(title, message, app_token, user_token):
    conn = httplib.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
      urllib.urlencode({
        "token": app_token,                       # Insert app token here
        "user": user_token,                       # Insert user token here
        "title": title,                			  # Title of the message
        "message": message     				      # Content of the message
      }), { "Content-type": "application/x-www-form-urlencoded" })
    return conn.getresponse()
# parse the passed arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    '-f',
    '--checkfilepath',
    dest='check_file_path', 
    help="path to store temporary file at if reboot criteria is met, but we need to wait until next time this script runs, check if that file exists, criteria are till met and then reboot",	
    default="/tmp/ethos_rig_mon.txt"
)
parser.add_argument('-a', '--pushover_app_token', dest='pushover_app_token',  help="app token for pushover service for push notifications on reboot")
parser.add_argument('-u', '--pushover_user_token', dest='pushover_user_token',  help="user token for pushover service for push notifications on reboot")
args = parser.parse_args()

# get current time to use when writing output entries
current_time = datetime.datetime.now()

# ping external host to ensure internet connectivity.  Otherwise, the rig would go into an unnecessary reboot loop during an Internet outage (ISP failure, device / router failure).  
# Pinging Google Public DNS Server.  They should be around for a little while.  :)
with open(os.devnull, 'w') as DEVNULL:
    try:
        subprocess.check_call(
            ['ping', '-c', '1', '8.8.8.8'],
            stdout=DEVNULL,  # suppress output
            stderr=DEVNULL
        )
        is_up = True
    except subprocess.CalledProcessError:
        is_up = False

# based on ping results, it either writes an offline log entry and exits, of if the reslut was online, the script continues.
if is_up <> True:
    print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | OFFLINE |                | NO INTERNET CONNECTIVITY"
    exit()

# parse miner hash file to determine last report hash for each card
from subprocess import Popen, PIPE
varCardNum = 0
varHashTot = 0
varHashAvg = 0
varCardHash = 0
varCardLog = ""
f = '/var/run/ethos/miner_hashes.file' #miner hash file location
# Get the last line from the file
p = Popen(['tail','-1',f], stderr=PIPE, stdout=PIPE)
res,err = p.communicate()
if err:
    print (err.decode())
else:
    # Use split to get the part of the line that you require
    varPerCardHash = res.split(" ")
    for varCardHash in (varPerCardHash):
        hash = format(float(varCardHash), '.2f')
        spaces = x*(7-len(hash))
        varHashTot = float(varCardHash) + float(varHashTot)
        varCardNum = varCardNum + 1
        varCardLog = str(varCardNum)
        if not hash or hash < hashalert:
            print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hash),"MH/s  |",errorstatusmessage," - GPU ",varCardNum
            # check if file exists, meaning that the hash rate wasn't as expected during the last script run
            if os.path.exists("/tmp/ethos_rig_mon_gpu_"+varCardLog+".txt"):
                os.remove("/tmp/ethos_rig_mon_gpu_"+varCardLog+".txt")
                varNotifyCnt = varNotifyCnt + 1
                if varNotifyCnt == 1:
                    # send push notification
                    pushover_message(
                        'RIG - {} - RESTARTING'.format(miner_id),
                        'RIG - {} - GPU {} reached a hash rate of {}'.format(miner_id,varCardLog,hash),
                        args.pushover_app_token,
                        args.pushover_user_token
                    )
                # reboot the system
                print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hash),"MH/s  | REBOOTING RIG - GPU CHECK"
                os.system("/opt/ethos/bin/r")
            else:
                print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hash),"MH/s  | CREATED CHECK FILE"
                # create a file so that next time we know we have been at 0 hash rate for one cycle.  If the problem is not cleared on the next cycle, the rig will be rebooted.
                os.system('touch {}'.format("/tmp/ethos_rig_mon_gpu_"+varCardLog+".txt"))
        else:
            # if the check file exists, remove it because the low hash issue has cleared
            if os.path.exists("/tmp/ethos_rig_mon_gpu_"+varCardLog+".txt"):
                os.remove("/tmp/ethos_rig_mon_gpu_"+varCardLog+".txt")
                print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hash),"MH/s  | REMOVED CHECK FILE - GPU ",varCardNum
# set more variables
varHashAvg = (varHashTot/varCardNum)*varCardNum
hashdec = format(float(varHashAvg), '.2f')
spaces = x*(7-len(hashdec))

# Check RIG average hash, if is non-existent of less than 115 by default - defined in the hashavgalert variable, a temp file is written, and if on the second run, the file still exists, the rig is rebooted.
if not float(hashdec) or float(hashdec) < float(hashavgalert):
    print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hashdec),"MH/s  |",errorstatusmessage
    # check if file exists, meaning that the hash rate wasn't as expected during the last script run
    if os.path.isfile(args.check_file_path):
        os.remove(args.check_file_path)
        # send push notification if the tokens have been set using the pushover notification service
        if args.pushover_user_token and args.pushover_app_token:
            pushover_message(
                'RIG - {} RESTARTING'.format(miner_id),
                'RIG - {} reached a hash rate of {}'.format(miner_id,hashdec),
                args.pushover_app_token,
                args.pushover_user_token
            )
        # reboot the system
        print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hashdec),"MH/s  | REBOOTING RIG"
        os.system("/opt/ethos/bin/r")
    else:
        print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hashdec),"MH/s  | CREATED CHECK FILE"
        # create a file so that next time we know we have been at 0 hash rate for one cycle.  If the problem is not cleared on the next cycle, the rig will be rebooted.
        os.system('touch {}'.format(args.check_file_path))
else:
    print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hashdec),"MH/s  |",statusmessage
    # if the checkfile exists, remove it because the conditions are no longer met
    if os.path.isfile(args.check_file_path):
        os.remove(args.check_file_path)
        print("{:%Y%m%d_%H%M}".format(current_time)),"|  {}".format(miner_id)," | ONLINE  |",spaces,"{}".format(hashdec),"MH/s  | REMOVED CHECK FILE"
