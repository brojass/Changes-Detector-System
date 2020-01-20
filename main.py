import re
from pathlib import Path
import hashlib
import json
import smtplib
import ast
from email.message import EmailMessage

STATE_START = 0
STATE_ROOT = 5
STATE_FOLDER = 10
STATE_FILES = 15
PATTERN_HOST = r'\[\s*host'
PATTERN_ROOT = r'\[\s*root_folder'
PATTERN_FOLDER = r'\[\s*folder'
HASH_FILE = 'hash'


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
    return posix_path


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
    return sorted(output_list)


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
    :rtype:
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


def compare_hash(file_string_content, dictionary):
    """

    :param file_string_content:
    :type file_string_content: str
    :param dictionary:
    :type dictionary: dict
    :return:
    :rtype:
    """
    dict2 = ast.literal_eval(file_string_content)
    diffkeys = [k for k in dictionary if dictionary[k] != dict2[k]]
    for k in diffkeys:
        print(k, ':', dictionary[k], '->', dict2[k])


def write_file(file_exist, file_content, dictionary):
    """

    :param file_content:
    :type file_content: str
    :param file_exist:
    :type file_exist: bool
    :param dictionary:
    :type dictionary: dict
    :return:
    :rtype:
    """
    if file_exist:
        print('File ' + HASH_FILE + ' already exists')
        compare_hash(file_content, dictionary)

    else:
        with open('hash', 'w') as file:
            file.write(json.dumps(dictionary))


def hash_file_exist(list_expanded):
    """

    :param list_expanded:
    :type list_expanded: list
    :return:
    :rtype: bool
    """
    with open(HASH_FILE, 'r') as f:
        string_content = f.read()
        if list_expanded[0] in string_content:
            return True, string_content
        else:
            string_content = ''
            return False, string_content


def send_email(file):
    """

    :param file:
    :type file:
    :return:
    :rtype:
    """
    with open(file) as fp:
        msg = EmailMessage()
        msg.set_content(fp.read())
    msg['Subject'] = f'Changes detected in {file}'
    msg['From'] = 'brojas@gemini.edu'
    msg['To'] = 'brojas@gemini.edu'

    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()


if __name__ == '__main__':
    file_list = []
    expanded_file_list = []
    dict_hash = {}
    file_existence = False
    str_content = ''
    try:
        file_list = read_configuration('gea.config')
    except FileNotFoundError as e:
        print(e)
        exit(0)
    except ValueError as e:
        print(e)
        exit(0)
    expanded_file_list = build_expand_list(file_list)
    print_list(expanded_file_list)
    dict_hash = dictionary_hash(expanded_file_list)
    try:
        file_existence, str_content = hash_file_exist(expanded_file_list)
    except FileNotFoundError as e:
        print(e)
        exit(0)
    write_file(file_existence, str_content, dict_hash)
    # send_email(HASH_FILE)
