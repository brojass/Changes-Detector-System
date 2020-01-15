import re

STATE_START = 0
STATE_ROOT = 5
STATE_FOLDER = 10
STATE_FILES = 15
PATTERN_HOST = r'\[\s*host'
PATTERN_ROOT = r'\[\s*root_folder'
PATTERN_FOLDER = r'\[\s*folder'


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
        print(output_string)
        return output_string
    else:
        print("Error, key not found")
        return False


def red_configuration(file_name):
    """

    :param file_name:
    :type file_name: str
    :return:
    :rtype:
    """
    host = ''
    root_folder = ''
    folder = ''
    output_list = []
    try:
        f = open(file_name, 'r')
    except IOError:
        print('Error')
        return False
    state = STATE_START
    for line in f:
        line = line.strip()
        if not line:
            continue
        if re.search(r'^#', line):
            continue
        print(line)
        if state == STATE_START:
            if re.search(PATTERN_HOST, line):
                host = return_key(line)
                if host:
                    state = STATE_ROOT
                else:
                    print('Error, host not found')
                    return False

        elif state == STATE_ROOT:
            if re.search(PATTERN_ROOT, line):
                root_folder = return_key(line)
                if root_folder:
                    root_folder = append_delimiter(root_folder)
                    state = STATE_FOLDER
                else:
                    print('Error, folder not found')
                    return False

        elif state == STATE_FOLDER:
            if re.search(PATTERN_FOLDER, line):
                folder = return_key(line)
                if folder:
                    folder = append_delimiter(folder)
                    state = STATE_FILES
                else:
                    print('Error, folder not found')
                    return False

        elif state == STATE_FILES:
            if re.search(PATTERN_HOST, line) or re.search(PATTERN_ROOT, line):
                print('Error, pattern already defined')
                return False
            if re.search(PATTERN_FOLDER, line):
                folder = return_key(line)
                if folder:
                    folder = append_delimiter(folder)
                    state = STATE_FILES
                else:
                    print('Error, folder not found')
                    return False
            else:
                output_list.append(root_folder + folder + line.strip())
                print(line.strip())
    print(output_list)
    return True


if __name__ == '__main__':
    red_configuration('gea.config')
