import os
import sys
import tty
import termios


def write_run_bat(directory, command):
    run_bat_path = os.path.join(directory, 'RUN.BAT')
    run_bat = open(run_bat_path, 'w')
    run_bat.writelines([
        '@ECHO OFF\n',
        command + '\n',
    ])
    run_bat.close()


def getchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def get_executables(directory):
    bat_files = []
    com_files = []
    exe_files = []
    for file in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, file)):
            file_parts = os.path.splitext(file)
            ext = file_parts[1].lower()
            if ext == '.bat':
                bat_files.append(file)
            elif ext == '.com':
                com_files.append(file)
            elif ext == '.exe':
                exe_files.append(file)
    return bat_files + com_files + exe_files


def create_run_bat_in_dir(directory):
    all_files = get_executables(directory)

    for i, choice in enumerate(all_files):
        print(' %s. %s' % (i+1, choice))

    user_choice = int(getchar()) - 1

    chosen_file = all_files[user_choice]
    file_parts = os.path.splitext(chosen_file)
    extension = file_parts[1].lower()
    if extension == '.bat':
        original_bat_file = os.path.join(directory, chosen_file)
        run_bat_path = os.path.join(directory, 'RUN.BAT')
        os.rename(original_bat_file, run_bat_path)
    else:
        write_run_bat(directory, chosen_file)

