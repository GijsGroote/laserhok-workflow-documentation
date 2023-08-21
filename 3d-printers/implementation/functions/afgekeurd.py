#! /usr/bin/env python3

import sys
import glob

from mail_functions import send_response_mail
from directory_functions import (
    job_name_to_global_path,
    copy_print_job)

from cmd_farewell_handler import remove_directory_cmd_farewell

if __name__ == '__main__':
    """ move print job from current folder to AFGEKEURD folder and popup a email response """

    job_name = sys.argv[1]
    job_global_path = job_name_to_global_path(job_name)

    # send response mail
    afgekeurd_reason = input("Why is the print job rejected?")
    eml_file_paths = [eml_file for eml_file in glob.glob(job_global_path + "/*.eml")]

    if len(eml_file_paths) > 1:
        print(f'Warning! more than one: {len(eml_file_paths)} .eml files detected')
        input('press enter to send response mail...')

    if len(eml_file_paths) > 0:
        send_response_mail(eml_file_paths[0], afgekeurd_reason)

    else:
        print(f'folder: {job_global_path} does not contain any .eml files, no response mail can be send')

    copy_print_job(job_name, "AFGEKEURD")
    remove_directory_cmd_farewell()

