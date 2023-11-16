"""
Convert python code to clickable batch functions.
"""

import os
from src.cmd_farewell_handler import cmd_farewells
from src.directory_functions import job_name_to_global_path

def python_to_batch(python_path: str, job_name=None, search_in_main_folder=None):
    """ Convert a python file to an batch file. """

    assert 'PYTHON_PATH' in globals()
    PYTHON_PATH = globals('PYTHON_PATH')
    assert 'FUNCTIONS_DIR_HOME' in globals()
    FUNCTIONS_DIR_HOME = globals('FUNCTIONS_DIR_HOME')
    assert os.path.isfile(python_path), f"file {python_path} does not exist."

    if job_name is not None:
        batch_file_global_path = job_name_to_global_path(job_name, search_in_main_folder)
        assert os.path.exists(batch_file_global_path),\
        f"path {batch_file_global_path} does not exist."
        python_command = f'"{PYTHON_PATH}" "{python_path}" "{job_name}"'
    else:
        batch_file_global_path = os.path.join(FUNCTIONS_DIR_HOME, '../batch_files')
        assert os.path.exists(batch_file_global_path),\
                f"path {batch_file_global_path} does not exist."
        python_command = f'"{PYTHON_PATH}" "{python_path}"'


    function_name = os.path.splitext(os.path.basename(python_path))[0]

    with open(os.path.join(batch_file_global_path, f'{function_name}.bat'), 'w+') as bat_file:
        bat_file.write(rf"""@echo off

{python_command}

{cmd_farewells}""")
