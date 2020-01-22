import re
from pathlib import Path
import hashlib
import json
import smtplib
import ast
import os.path
from email.message import EmailMessage

STATE_START = 0
STATE_ROOT = 5
STATE_FOLDER = 10
STATE_FILES = 15
PATTERN_HOST = r'\[\s*host'
PATTERN_ROOT = r'\[\s*root_folder'
PATTERN_FOLDER = r'\[\s*folder'
FILE_CONF = 'gea.config'
HASH_FILE = 'hash'


def append_delimiter(directory):
    """

    :param directory:
    :type directory: str
    :return:
    :rtype: str
    """
    if directory in ['.', './']:
        return ''
    else:
        directory = directory if re.search(r'/$', directory) else directory + '/'
        return directory


def return_key(line):
    """

    :param line:
    :type line: str
    :return:
    :rtype: str
    """
    aux = line.replace('=', ' ').replace('[', ' ').replace(']', ' ').split()
    if len(aux) == 2:
        output_string = aux[1]
        return output_string
    else:
        print("Error, key not found")
        return False


def read_configuration(file_name):
    """

    :param file_name:
    :type file_name: str
    :return:
    :rtype: list
    """
    root_folder = ''
    folder = ''
    # output_list = []
    # try:
    f = open(file_name, 'r')
    # except IOError:
    #     print('Error')
    #     return False
    state = STATE_START
    for line in f:
        line = line.strip()
        if not line:
            continue
        if re.search(r'^#', line):
            continue
        if state == STATE_START:
            if re.search(PATTERN_HOST, line):
                host = return_key(line)
                if host:
                    state = STATE_ROOT
                else:
                    raise ValueError('host definition not found')

        elif state == STATE_ROOT:
            if re.search(PATTERN_ROOT, line):
                root_folder = return_key(line)
                if root_folder:
                    root_folder = append_delimiter(root_folder)
                    state = STATE_FOLDER
                else:
                    raise ValueError('root folder definition not found')

        elif state == STATE_FOLDER:
            if re.search(PATTERN_FOLDER, line):
                folder = return_key(line)
                if folder:
                    folder = append_delimiter(folder)
                    state = STATE_FILES
                else:
                    raise ValueError('folder not defined')

        elif state == STATE_FILES:
            if re.search(PATTERN_HOST, line) or re.search(PATTERN_ROOT, line):
                raise ValueError('duplicate host or root folder definition')
            if re.search(PATTERN_FOLDER, line):
                folder = return_key(line)
                if folder:
                    folder = append_delimiter(folder)
                    state = STATE_FILES
                else:
                    raise ValueError('folder not defined')
            else:
                file_list.append(root_folder + folder + line.strip())
    return file_list


def expand(full_file_name):
    """

    :param full_file_name:
    :type full_file_name: str
    :return:
    :rtype: list
    """
    val = full_file_name.rfind('/')
    path = full_file_name[0:val]
    pattern = full_file_name[val + 1:]
    posix_path = Path(path).glob(pattern)

    path_comparator = Path(full_file_name)
    if path_comparator.exists() and re.search(''):
        print('Exist ', pattern)
    else:
        print('Not exists ', pattern)

    return posix_path


def build_expand_list(file_name_list):
    """

    :param file_name_list:
    :type file_name_list: list
    :return:
    :rtype: list
    """
    output_list = []
    for file_name in file_name_list:
        for expanded_file_name in expand(file_name):
            output_list.append(str(expanded_file_name))
    return output_list


def print_list(input_list):
    """

    :param input_list:
    :type input_list: list
    :return:
    :rtype:
    """
    for element in input_list:
        print(element)


def calculate_md5(file_name):
    """

    :param file_name:
    :type file_name: str
    :return:
    :rtype: str
    """
    f = open(file_name)
    buffer = f.read()
    hash_result = hashlib.md5(buffer.encode())
    f.close()
    return hash_result.hexdigest()


def dictionary_hash(files_list):
    """

    :param files_list:
    :type files_list: list
    :return:
    :rtype: dict
    """
    hash_dict = {}
    for file_name in files_list:
        hash_result = calculate_md5(file_name)
        hash_dict[file_name] = hash_result
    return hash_dict


def hash_file_exist(file_hash):
    """

    :param file_hash:
    :type file_hash: str
    :return:
    :rtype: str
    """
    with open(file_hash, 'r') as f:
        string_content = f.read()
        return string_content


def compare_hash(reference_file_string_content, configuration_dictionary):
    """

    :param reference_file_string_content:
    :type reference_file_string_content: str
    :param configuration_dictionary:
    :type configuration_dictionary: dict
    :return:
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

    :param add_files:
    :type add_files: list
    :param mod_files:
    :type mod_files: list
    :param rm_files:
    :type rm_files: list
    :return:
    :rtype:
    """
    aux_rm = ''
    aux_mod = ''
    aux_add = ""
    msg = EmailMessage()
    msg['Subject'] = f'Changes detected in {FILE_CONF}'
    msg['From'] = 'brojas@gemini.edu'
    msg['To'] = 'brojas@gemini.edu'

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
    msg.set_content(aux_mod + aux_rm + aux_add)
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()


def write_file(dictionary):
    """

    :param dictionary:
    :type dictionary: dict
    :return:
    :rtype:
    """
    with open('hash', 'w') as file:
        file.write(json.dumps(dictionary))


if __name__ == '__main__':
    file_list = []
    expanded_file_list = []
    dict_hash = {}
    reference_content = ''
    added_files = []
    removed_files = []
    modified_files = []
    try:
        file_list = read_configuration(FILE_CONF)
    except FileNotFoundError as e:
        print(e)
        exit(0)
    except ValueError as e:
        print(e)
        exit(0)
    try:
        expanded_file_list = build_expand_list(file_list)
        print(expanded_file_list)
    except ValueError as e:
        print(e)
        exit(0)
    # print_list(expanded_file_list)
    dict_hash = dictionary_hash(expanded_file_list)
    if os.path.exists(HASH_FILE):
        reference_content = hash_file_exist(HASH_FILE)
        modified_files, removed_files, added_files = compare_hash(reference_content, dict_hash)
        if modified_files or removed_files or added_files:
            print('Email send')
            # send_email(modified_files, removed_files, added_files)
    # write_file(dict_hash)
