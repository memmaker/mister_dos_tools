import time
import sys
import ctypes, os

## NOTE: This is windows only, since it uses diskpart via shell.

def is_admin_user():
    is_admin = False
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin


def get_size(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def dirToVHD(directory_path, vhd_dest_filename, label_name='DOS'):
    directory_path = os.path.abspath(directory_path)
    min_size = get_size(directory_path)
    print('Bytes needed: %s' % (min_size,))
    min_size_mb = int(((min_size * 1.1) / 1024) / 1024 + 50)
    print('MegaBytes needed: %s' % (min_size_mb,))
    createVHD(int(min_size_mb), vhd_dest_filename, label_name)
    print('Disk created waiting for write operation')
    time.sleep(2)
    # copy dir to w:
    stream = os.popen('xcopy %s %s /s /e' % (directory_path, 'w:'))
    output = stream.read()
    print(output)


def executeDiskpartCommands(list_of_commands):
    script_file = 'diskp00.txt'
    file = open(script_file, 'w')
    file.writelines(list_of_commands)
    file.close()

    stream = os.popen('diskpart /s %s' % (script_file,))
    output = stream.read()
    os.remove(script_file)
    return output


def createVHD(size_in_mb, dest_filename, label_name='DOS'):
    dest_filename = os.path.abspath(dest_filename)
    diskpart_commands = [
        'CREATE VDISK FILE="%s" MAXIMUM=%s\n' % (dest_filename, size_in_mb),
        'ATTACH VDISK\n',
        'CREATE PARTITION PRIMARY SIZE=10\n',
        'FORMAT FS=FAT LABEL="STUB" QUICK\n'
        'CREATE PARTITION PRIMARY\n',
        'FORMAT FS=FAT32 LABEL="%s" QUICK\n' % (label_name,),
        'ASSIGN LETTER=W\n',
        'EXIT\n'
    ]
    output = executeDiskpartCommands(diskpart_commands)
    print(output)


def detachVHD(vhd_filename):
    vhd_filename = os.path.abspath(vhd_filename)
    diskpart_commands = [
        'SELECT VDISK FILE="%s"\n' % (vhd_filename,),
        'DETACH VDISK\n',
        'EXIT\n'
    ]
    output = executeDiskpartCommands(diskpart_commands)
    print(output)


def attachVHD(vhd_filename):
    vhd_filename = os.path.abspath(vhd_filename)
    diskpart_commands = [
        'SELECT VDISK FILE="%s"\n' % (vhd_filename,),
        'ATTACH VDISK\n',
        'EXIT\n'
    ]
    output = executeDiskpartCommands(diskpart_commands)
    print(output)


# createVHD(1000, 'test.vhd', 'mylabel')
# attachVHD('test.vhd')
if not is_admin_user():
    print('MUST BE RUN AS ADMIN')
    sys.exit(1)

if len(sys.argv) == 4:
    command = sys.argv[1]
    if command == 's':
        size_in_mb = int(sys.argv[2])
        vhd_file = os.path.abspath(sys.argv[3])
        print('Size (MB): %s, VHD: %s' % (size_in_mb, vhd_file))
        createVHD(size_in_mb, vhd_file)
        detachVHD(vhd_file)
        sys.exit(0)
    elif command == 'd':
        directory = sys.argv[2]
        vhd_file = sys.argv[3]
        print('Dir: %s, VHD: %s' % (directory, vhd_file))
        dirToVHD(directory, vhd_file)
        detachVHD(vhd_file)
        sys.exit(0)

print('Usage:\n vhd s [SIZE IN MB] [VHD FILE]\n vhd d [DIRECTORY] [VHD FILE]')
