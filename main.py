import sys
import re
from pathlib import Path
import hashlib
import json
import smtplib
import ast
import os.path
from email.message import EmailMessage
from argparse import Namespace, ArgumentParser

PATTERN_HOST = r'\[\s*host'
PATTERN_ROOT = r'\[\s*root_folder'
PATTERN_FOLDER = r'\[\s*folder'
PATTERN_EMAIL = r'\[\s*email'

FILE_CONF_LIST = ['gea.config', 'rtconfig.config']
REFERENCE_FILE = 'hash'
EMAILS_TO_SEND = ['brojas@gemini.edu']


class ConfigurationError(Exception):
    """
    Raised when a syntax error is found in a configuration file.
    """
    pass


def append_delimiter(directory):
    """
    Add '/' to the end of the directory name if it's not already there.
    Return an empty string when the directory is '.' or './'
    :param directory: The name or direction path from the pattern
    :type directory: str
    :return: The path with '/' at the final of each one
    :rtype: str
    """
    if directory in ['.', './']:
        return ''
    else:
        directory = directory if re.search(r'/$', directory) else directory + '/'
        return directory


def return_value(line):
    """
    Separate a line of the form '[key=value]' into 'key' and 'value'.
    Raise an exception if the line cannot be split into key and value.
    The key may be 'host', 'root_folder' or 'folder', but this function does not check for it.
    :param line: Line of text that contain '[host/root_folder/folder=xxx]' format.
    :type line: str
    :return: The name or direction path from the pattern
    :rtype: str
    """
    aux = line.replace('=', ' ').replace('[', ' ').replace(']', ' ').split()
    if len(aux) == 2:
        output_string = aux[1]
        return output_string
    else:
        return ''


def read_configuration_file_list(conf_list):
    """
    This function iterates over a list who has the configuration files for later appended
    into only one file list.
    :param conf_list: The configurations files list.
    :type conf_list: list
    :return: A list with files found inside the configurations files.
    :rtype:list
    """
    final_list = []
    for config in conf_list:
        final_list.append(config)
        for config_files_list in read_configuration(config):
            final_list.append(config_files_list)
    return final_list


def read_configuration(file_name):
    """
    This function read the file configuration and have an state machine that separate
    the host and root folder from the folders who has the files to analyze, and as result
    have all files found inside the configuration file.
    :param file_name: The name of the path file who has the configuration.
    :type file_name: str
    :return: A list with files found inside the configuration file.
    :rtype: list
    :raises: ConfigurationError
    """
    host_name = ''
    root_folder = ''
    folder = ''
    found_file_list = []

    f = open(file_name, 'r')

    for line in f:

        # Skip blank lines and comments
        line = line.strip()
        if not line:
            continue
        if re.search(r'^#', line):
            continue

        if re.search(PATTERN_HOST, line):  # [host=host_name]
            value = return_value(line)
            if value:
                if not host_name:
                    host_name = value
                else:
                    raise ConfigurationError('duplicate host definition')
            else:
                raise ConfigurationError('host name missing')

        elif re.search(PATTERN_ROOT, line):  # [root_folder=directory]
            root_folder = return_value(line)
            if root_folder:
                root_folder = append_delimiter(root_folder)
            else:
                raise ConfigurationError('root folder missing')

        elif re.search(PATTERN_FOLDER, line):  # [folder=directory]
            folder = return_value(line)
            if folder:
                folder = append_delimiter(folder)
            else:
                raise ConfigurationError('folder missing')

        else:  # file name
            new_file_name = line.strip()
            if root_folder and folder:
                found_file_list.append(root_folder + folder + new_file_name)
            else:
                raise ConfigurationError('root_folder or folder not defined for ' + new_file_name)

    f.close()
    return found_file_list


def expand(full_file_name):
    """
    Function that find and transform all files which are in '*.xxx' format to path format.
    :param full_file_name: file that were found inside the configuration file.
    :type full_file_name: str
    :return: file in path format.
    :rtype: list
    """
    val = full_file_name.rfind('/')
    path = full_file_name[0:val]
    pattern = full_file_name[val + 1:]
    posix_path = Path(path).glob(pattern)
    return posix_path


def build_expanded_list(file_name_list):
    """
    This function iterates over the list who has the files that were found in first instance, for later find the files
    that are in '*.xxx' format.
    :param file_name_list: list with files that were found inside the configuration file, but not the total of them.
    :type file_name_list: list
    :return: list with total files inside the configuration file.
    :rtype: list
    """
    output_list = []
    for file_name in file_name_list:
        for expanded_file_name in expand(file_name):
            output_list.append(str(expanded_file_name))
    return output_list


def print_list(input_list):
    """
    Function that iterates over a list and print each element.
    :param input_list: list which wanna print.
    :type input_list: list
    """
    for element in input_list:
        print(element)


def calculate_md5(file_name):
    """
    This function calculate md5 of each given file.
    :param file_name: file as element that iterates on 'for' statement in def dictionary_hash.
    :type file_name: str
    :return: md5 hash of given file.
    :rtype: str
    """
    f = open(file_name)
    buffer = f.read()
    hash_result = hashlib.md5(buffer.encode())
    f.close()
    return hash_result.hexdigest()


def calculate_hashes(files_list):
    """
    Function that iterates over list with the total files, for later calculate md5 of each file
    to assign them into a dictionary.
    :param files_list: list with total files inside the configuration file.
    :type files_list: list
    :return: dictionary with md5 hash like value and as key, the files given.
    :rtype: dict
    """
    hash_dict = {}
    for file_name in files_list:
        hash_result = calculate_md5(file_name)
        hash_dict[file_name] = hash_result
    return hash_dict


def read_reference_file(file_hash):
    """
    Function that read the content of REFERENCE_FILE.
    :param file_hash: name or direction of REFERENCE_FILE.
    :type file_hash: str
    :return: content of REFERENCE_FILE.
    :rtype: str
    """
    with open(file_hash, 'r') as f:
        string_content = f.read()
        return string_content


def compare_hashes(reference_file_string_content, configuration_dictionary):
    """
    This function compare the files between REFERENCE_FILE and configuration file. With the purpose
    of known which files was modified, removed or added.
    :param reference_file_string_content: content of REFERENCE_FILE.
    :type reference_file_string_content: str
    :param configuration_dictionary: dictionary with md5 hash like value and files as key.
    :type configuration_dictionary: dict
    :return: three list of modified files, removed files and added files.
    :rtype: tuple
    """
    removed_list = []
    new_list = []
    diff_list = []
    reference_dictionary = ast.literal_eval(reference_file_string_content)

    for key in reference_dictionary:
        if key in configuration_dictionary:
            if configuration_dictionary[key] != reference_dictionary[key]:
                print('File modified: ' + key)
                diff_list.append(key)
        else:
            print('File removed: ' + key)
            removed_list.append(key)

    added_list = [x for x in configuration_dictionary if x not in reference_dictionary]
    for file_added in added_list:
        print('File added: ' + file_added)
        new_list.append(file_added)
    return diff_list, removed_list, new_list


def send_email(mod_files, rm_files, add_files):
    """
    Function that send the email of the changes that were detected to a specifics persons.
    :param add_files: list that contain added files.
    :type add_files: list
    :param mod_files: list that contain modified files.
    :type mod_files: list
    :param rm_files: list that contain removed files.
    :type rm_files: list
    """
    aux_rm = ''
    aux_mod = ''
    aux_add = ""
    email_to_send_list = EMAILS_TO_SEND

    if rm_files:
        for rm in rm_files:
            aux_rm = aux_rm + rm + '\n'
        aux_rm = 'Files that were deleted: \n' + aux_rm
    if mod_files:
        for md in mod_files:
            aux_mod = aux_mod + md + '\n'
        aux_mod = 'Files that were modified: \n' + aux_mod
    if add_files:
        for ad in add_files:
            aux_add = aux_add + ad + '\n'
        aux_add = 'Files that were added: \n' + aux_add

    for email in email_to_send_list:
        print('Email send to ' + email)
        msg = EmailMessage()
        msg['Subject'] = f'Changes detected in configurations files'
        msg['From'] = 'brojas@gemini.edu'
        msg['To'] = email
        msg.set_content(aux_mod + aux_rm + aux_add)
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()


def write_reference_file(dictionary):
    """
    Function that write or overwrite the REFERENCE_FILE
    :param dictionary: dictionary with md5 hash like value and files as key.
    :type dictionary: dict
    """
    with open(REFERENCE_FILE, 'w') as file:
        file.write(json.dumps(dictionary))


def get_arguments(argv):
    """
    Process command line arguments
    :param argv: command line arguments from sys.argv
    :type argv: list
    :return: command line arguments
    :rtype: Namespace
    """
    parser = ArgumentParser()

    parser.add_argument(action='store',
                        nargs='*',
                        dest='file_list',
                        default=[],
                        help='list of configuration files')

    return parser.parse_args(argv[1:])


if __name__ == '__main__':

    # Get file list from the command line. Terminate if no files are specified.
    args = get_arguments(['program', 'gea.config'])  # test
    # args = get_arguments(sys.argv)
    if not args.file_list:
        print('no configuration files specified')
        exit(0)

    # Read configuration file(s)
    file_list = []
    try:
        file_list = read_configuration_file_list(args.file_list)
    except FileNotFoundError as e:
        print(e)
        exit(0)
    except ValueError as e:
        print(e)
        exit(0)

    # Expand any wildcards used in the configuration files
    # The expanded file list is normally longer than the file
    # list read from the configuration file
    expanded_file_list = []
    try:
        expanded_file_list = build_expanded_list(file_list)
    except ValueError as e:
        print(e)
        exit(0)

    print_list(file_list)

    # Calculate the hashes for all files specified in the configuration files
    file_hashes = calculate_hashes(expanded_file_list)

    # Compare the file hashes against the hashes in the reference file.
    # Send an email when new, removed, or modified files are detected.
    if os.path.exists(REFERENCE_FILE):
        reference_hashes = read_reference_file(REFERENCE_FILE)
        modified_files, removed_files, added_files = compare_hashes(reference_hashes, file_hashes)
        if modified_files or removed_files or added_files:
            send_email(modified_files, removed_files, added_files)

    # Update the reference file
    write_reference_file(file_hashes)
