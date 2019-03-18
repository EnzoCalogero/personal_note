# -*- coding: utf-8 -*-
import sys
import os
import csv
import json
import uuid
import shutil
import gzip
from collections import Counter
from datetime import datetime

# Stats Counters
sender_counter = Counter()
receiver_counter = Counter()
connections_counter = Counter()  #  Counter for the connection extension for Neo4j
row_number = 0


def write_json(email_, row_number_, file_input_):
    """ Write the email dictionary into a json file.

    :param email_: dictionary of one row
    :param row_number_: the position of the row in the file
    :param file_input_: The path name of the source file

    :return:null
    """
    filename = file_input_.split('/')[-1]
    json_file = './processed/{}-{}.json'.format(filename, row_number_)

    with open(json_file, 'w') as f:
        json.dump(email_, f, indent=4, separators=(',', ': '))
        # Added for POSIX compatibility
        f.write('\n')
    f.close()


def archive_file(input_file_):
    """The function archive the source file

    :param input_file_: The path name of the source file
    :return:null
    """
    filename = input_file_.split('/')[-1]
    archive_path = './archive/'

    current_data = datetime.now()
    current_data = current_data.strftime("%Y%m%d")
    archived_file = '{}{}-processed-{}.gz'.format(archive_path, filename, current_data)

    with open(input_file, 'rb') as f_in, gzip.open(archived_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    print("File Archived as {}".format(archived_file))


def statistics_updater(email_):
    """The function extract from the email dictionary, the sender and receiver(s)
    and update the related counters.
    :param email_:dictionary of one row
    :return:
    """
    global row_number
    row_number += 1

    sender_counter[email_['sender']] += 1

    for receiver in email_['recipients']:
        receiver_counter[receiver] += 1


def network_updater(email_):
    """The function extract from the email dictionary, the sender and receiver(s)
    and update the related counters.
    :param email_:dictionary of one row
    :return:
    """
    for receiver in email_['recipients']:
        connection= "{}-{}".format(email_['sender'],receiver)
    print(connection)
    connections_counter[connection] += 1

def statistics_final(input_file_):
    """ The function consolidate the counters for the received and send emails
     and dump all into the <input file>-stat.cvs file.
    :param input_file_: The path name of the source file
    :return:
    """
    filename = input_file_.split('/')[-1]
    filename = './{}-stats.csv'.format(filename)
    file_stats = open(filename, 'w')
    file_stats.write('User, Received_Emails, Sended_Emails\n')
    list_users = list(set(sender_counter.keys()))
    list_users.sort()
    for user in list_users:
        file_stats.write('"{}",{},{}\n'.format(user, receiver_counter.get(user, 0), sender_counter.get(user, 0)))
    file_stats.close()
    print("File statistics as {}".format(filename))


def check_file():
    """The function test the application input information and the existence of the source file

    :return:
    """
    # Check the command line argument
    if len(sys.argv) != 2:
        print("\n Sorry, not a valid format")
        print("\nPlease, use the format, as in the example below:")
        print("python parse-daily-enron-file.py source/enron-event-history-20180202.csv")
        exit()
    input_file_ = str(sys.argv[1])
    # check  if file exist
    if not os.path.isfile(input_file_):
        print("Sorry, file not found")
        print("File {} do not Exist please check the file path".format(input_file_))
        exit()
    return input_file_


if __name__ == "__main__":

    input_file = check_file()

    row_number = 0
    with open(input_file) as csv_file:
        readCSV = csv.reader(csv_file, delimiter=',')
        for row in readCSV:
            row_number += 1
            email = dict()
            email['timestamp_iso'] = datetime.utcfromtimestamp(int(row[0])/1000).isoformat()
            email['unique_id'] = str(uuid.uuid4())
            email['message identifier'] = row[1]
            email['sender'] = row[2].lower()
            email['recipients'] = row[3].lower().split('|')

            dict_recipients = {'name': 'number_of_recipients', 'value': len(row[3].split('|'))}
            email['attributes'] = [dict_recipients, ]

            # it is always empty but we keep for consistency
            email["topic"] = row[4]

            # it is always mail but we keep for consistency
            email["email"] = row[5]

            write_json(email, row_number, input_file)

            statistics_updater(email)
            network_updater(email)

        csv_file.close()

        archive_file(input_file)

        statistics_final(input_file)
        print(connections_counter)
