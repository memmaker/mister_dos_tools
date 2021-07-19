import hashlib
import re
import struct
import sys
import os
from pathlib import Path
import csv
from create_run_bat import create_run_bat_in_dir, write_run_bat_verbatim

filesIDX = 'FILES.IDX'
titlesIDX = 'TITLES.IDX'
sort_key = lambda record: record['title']


def removeByIndex(index):
    files = readFileIndex(filesIDX)
    titles = readTitleIndex(titlesIDX)

    del files[index]
    del titles[index]

    generateFileIndex(filesIDX, files)
    generateTitleIndex(titlesIDX, titles)


def insertTitle(insert_index, filename, title):
    files = readFileIndex(filesIDX)
    titles = readTitleIndex(titlesIDX)

    files.insert(insert_index, filename)
    titles.insert(insert_index, title)

    generateFileIndex(filesIDX, files)
    generateTitleIndex(titlesIDX, titles)

    readFileIndex(filesIDX)
    readTitleIndex(titlesIDX)


def generateFileIndex(filesIDX, DOSnames):
    print("  Generating files index...")
    f = open(filesIDX, 'wb')
    f.write(struct.pack('<H', len(DOSnames)))
    for idx, fname in enumerate(DOSnames):
        f.write(struct.pack('<H', idx))
        f.write(str.encode(fname[0:12].ljust(12, "\x00")))
    f.close()


def read_all_indices(directory):
    filesIDX_path = os.path.join(directory, filesIDX)
    titlesIDX_path = os.path.join(directory, titlesIDX)
    files = readFileIndex(filesIDX_path)
    titles = readTitleIndex(titlesIDX_path)
    data_list = []
    for i, filename in enumerate(files):
        title = titles[i]
        data_list.append({
            'title': title,
            'file': filename
        })
    return data_list


def get_non_conflicting_filename(filename, set_of_known_filenames):
    index = 2
    filename_list = list(filename)
    length = len(filename)
    if length < 11:
        filename_list.insert(length - 4, '_')
        filename_list.insert(length - 4, '_')
        length += 2
    elif length < 12:
        filename_list.insert(length - 4, '_')
        length += 1
    while True:
        filename_list[length - 5] = str(index)
        filename_string = ''.join(filename_list)
        if filename_string not in set_of_known_filenames:
            return filename_string
        index += 1


def check_duplicates(full_list, rename_dir):
    # assumes list is sorted
    last_filename = ''
    set_of_filenames = set()
    for i, record in enumerate(full_list):
        if last_filename == record['file']:
            print('Found duplicate filename "%s" for game %s' % (record['file'], record['title']))
            new_filename = get_non_conflicting_filename(last_filename, set_of_filenames)
            print('...renaming to %s' % new_filename)
            full_list[i]['file'] = new_filename
            change_filename(last_filename, new_filename, rename_dir)
        else:
            last_filename = record['file']
            set_of_filenames.add(record['file'])
    return full_list


def change_filename(last_filename, new_filename, rename_dir):
    old_path = os.path.join(rename_dir, 'FILES', last_filename)
    new_path = os.path.join(rename_dir, 'FILES', new_filename)
    os.rename(old_path, new_path)

    old_short_name = os.path.splitext(last_filename)[0]
    new_short_name = os.path.splitext(new_filename)[0]

    old_root_dir = os.path.join(rename_dir, 'GAMES', old_short_name)
    old_games_path = os.path.join(old_root_dir, old_short_name)

    new_root_dir = os.path.join(rename_dir, 'GAMES', new_short_name)
    new_games_path = os.path.join(new_root_dir, new_short_name)

    ensure_dir_exists(new_root_dir)

    os.rename(old_games_path, new_games_path)

    write_start_bat(new_root_dir, new_short_name)
    os.remove(os.path.join(old_root_dir, '1_Start.bat'))
    os.rmdir(old_root_dir)


def merge_indices_sorted(list_one, list_two, rename_dir):
    full_list = list_one + list_two
    full_list.sort(key=sort_key)
    full_list = check_duplicates(full_list, rename_dir)
    return full_list


def write_index_list(data_list, target_directory):
    titles = []
    files = []
    for entry in data_list:
        titles.append(entry['title'])
        files.append(entry['file'])

    filesIDX_path = os.path.join(target_directory, filesIDX)
    titlesIDX_path = os.path.join(target_directory, titlesIDX)

    generateTitleIndex(titlesIDX_path, titles)
    generateFileIndex(filesIDX_path, files)


def readFileIndex(filesIDX):
    filenames = []
    f = open(filesIDX, 'rb')
    count = struct.unpack('<H', f.read(2))[0]
    print('COUNT: %s' % (count,))

    for counter in range(count):
        index = struct.unpack('<H', f.read(2))[0]
        name_bytes = f.read(12)
        name = name_bytes.decode().strip("\x00")
        # print('Found: %s - %s' % (index, name))
        # print('Decoded name %s with length %s' % (name, name_bytes))
        filenames.append(name)
    f.close()
    return filenames


def readTitleIndex(titlesIDX):
    titles = []
    f = open(titlesIDX, 'rb')
    count = struct.unpack('<H', f.read(2))[0]
    for i in range(count):
        offset = struct.unpack('<L', f.read(4))[0]
        # print('Found offset: ' + str(offset))
    for i in range(count):
        index = struct.unpack('<H', f.read(2))[0]
        hash_bytes = f.read(16)
        title_len = struct.unpack('B', f.read(1))[0]
        title_bytes = f.read(title_len)
        title = title_bytes.decode(encoding='latin_1').strip()
        # print('Found: %s - %s' % (index, title))
        titles.append(title)

    f.close()
    return titles


def generateTitleIndex(titlesIDX, titles):
    print("  Generating titles index...")
    f = open(titlesIDX, 'wb')
    f.write(struct.pack('<H', len(titles)))
    # build list of offsets
    toffsets = []
    curofs = 2 + (len(titles) * 4)  # real starting offset is past the offset structure itself
    for tlen in titles:
        toffsets.append(curofs)
        curofs = curofs + (2 + 16 + 1 + len(tlen))
    # dump offsets to index file
    for tmpofs in toffsets:
        f.write(struct.pack('<L', tmpofs))
    for idx, name in enumerate(titles):
        clean_name = name.replace('\xa0', u' ')
        encoded_name = clean_name.encode(encoding='latin_1')
        # write titleID
        f.write(struct.pack('<H', idx))
        # write titleHash
        thash = hashlib.md5(encoded_name).digest()
        f.write(thash)
        # write titleLen
        name_length = len(clean_name)
        # print('Encoding length %s for %s' % (name_length, name))
        f.write(struct.pack('B', name_length))
        # write title itself
        f.write(encoded_name)
    f.close()


def generateShortName(long_name):
    cleaned_name = re.sub(r'[^a-zA-Z0-9]', '', long_name).upper()
    if len(cleaned_name) > 8:
        cleaned_name = cleaned_name[0:8]
    return cleaned_name


def directoryToIndex(src_dir, target_dir, do_move=False, do_create_zips=True):
    record_data = indexDirectory(src_dir)
    record_data.sort(key=sort_key)

    title_list = []
    file_list = []

    file_idx = os.path.join(target_dir, 'FILES.IDX')
    title_idx = os.path.join(target_dir, 'TITLES.IDX')

    files_sub_dir = os.path.join(target_dir, 'FILES')
    games_sub_dir = os.path.join(target_dir, 'GAMES')

    if do_create_zips:
        ensure_dir_exists(files_sub_dir)

    if do_move:
        ensure_dir_exists(games_sub_dir)

    for record in record_data:
        title_list.append(record['title'])
        file_list.append(record['zip_name'])

        if do_create_zips:
            file_path = os.path.join(files_sub_dir, record['zip_name'])
            Path(file_path).touch(exist_ok=True)

        if do_move:
            game_dir = os.path.join(games_sub_dir, record['short_name'])
            game_sub_dir = os.path.join(game_dir, record['short_name'])
            ensure_dir_exists(game_dir)
            os.rename(record['full_path'], game_sub_dir)
            write_start_bat(game_dir, record['short_name'])
    print('\n*********************************\n')
    generateFileIndex(file_idx, file_list)
    generateTitleIndex(title_idx, title_list)


def write_start_bat(game_dir, short_name):
    start_bat = os.path.join(game_dir, '1_Start.bat')
    file = open(start_bat, 'w', newline='\r\n', encoding="latin-1")

    list_of_commands = [
        '@ECHO OFF',
        'cd %s' % short_name,
        'call run.bat'
    ]

    commands_with_le = map(lambda c: c + '\n', filter(lambda c: c.strip('\r\n\t '), list_of_commands))

    file.writelines(commands_with_le)

    file.close()


def ensure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)


def save_title(title, title_path):
    with open(title_path, "w") as text_file:
        text_file.write(title)


def recreate_batch_files(src_dir):
    for short_name in os.listdir(src_dir):
        root_dir = os.path.join(src_dir, short_name)
        if not os.path.isfile(root_dir) and not os.path.islink(root_dir):
            start_path = os.path.join(root_dir, '1_Start.bat')
            if os.path.exists(start_path) and os.path.isfile(start_path):
                full_path = os.path.join(root_dir, short_name)  # go deeper one level
                write_start_bat(root_dir, short_name)
                run_path = os.path.join(full_path, 'RUN.BAT')
                with open(run_path, "r", encoding='latin-1', newline='\r\n') as run_file:
                    run_commands = list(filter(lambda line: line, map(lambda line: line.strip('\r\n\t '), run_file.readlines())))
                    write_run_bat_verbatim(full_path, run_commands)


def indexDirectory(src_dir):
    record_data = []
    for f in os.listdir(src_dir):
        full_path = os.path.join(src_dir, f)
        if not os.path.isfile(full_path) and not os.path.islink(full_path):
            print('\n*********************************\n\nFound directory %s' % (f,))
            start_path = os.path.join(full_path, '1_Start.bat')

            if os.path.exists(start_path) and os.path.isfile(start_path):
                full_path = os.path.join(full_path, f) # go deeper one level

            run_path = os.path.join(full_path, 'RUN.BAT')
            if not os.path.exists(run_path) or not os.path.isfile(run_path):
                print('WARNING: No run.bat for %s' % (f,))
                create_run_bat_in_dir(full_path)
            title_path = os.path.join(full_path, 'title.txt')
            if not os.path.exists(title_path) or not os.path.isfile(title_path):
                print('WARNING: No title.txt for %s' % (f,))
                title = input('Please input title (ENTER = Folder Name): ')
                if not title:
                    title = f
                save_title(title, title_path)
            else:
                title = Path(title_path).read_text().strip()
            print(' ...found title "%s"' % title)

            short_name = f

            if len(short_name) > 8:
                print('WARNING: Directory name is too long for DOS.')
                short_name = get_user_short_name(generateShortName(f))
            record_data.append({
                'title': title,
                'full_path': full_path,
                'run_bat_path': run_path,
                'short_name': short_name,
                'zip_name': short_name + '.ZIP'
            })
    return record_data


def lfn_to_title_files(src_dir):
    for f in os.listdir(src_dir):
        if not os.path.isfile(f) and not os.path.islink(f) and len(f) > 8:
            print('\n********************************************\n\nFound lfn directory %s' % (f,))
            full_path = os.path.join(src_dir, f)
            title_path = os.path.join(src_dir, f, 'title.txt')
            if not os.path.exists(title_path) or not os.path.isfile(title_path):
                print('WARNING: No title.txt for %s. Using folder name.' % (f,))
                title = f
                save_title(title, title_path)

            short_name = generateShortName(f)
            user_short_name = get_user_short_name(short_name)
            if user_short_name:
                short_name = user_short_name
            short_dir = os.path.join(src_dir, short_name)
            print('Renaming %s > %s' % (full_path, short_dir))
            os.rename(full_path, short_dir)


def get_user_short_name(short_name):
    current_name = short_name
    while True:
        user_short_name = input('Please input short name (ENTER = Use %s): ' % (current_name,))
        if not user_short_name:
            return current_name
        if len(user_short_name) <= 8:
            return user_short_name.upper()
        else:
            current_name = user_short_name[0:8].upper()


def write_csv(file, data):
    with open(file, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for record in data:
            row_data = [record['title'], record['file']]
            print(row_data)
            writer.writerow(row_data)


def read_csv(file):
    index_data = []
    with open(file) as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            index_data.append({
                'title': row[0],
                'file': row[1]
            })
    return index_data


def display_data(list_of_records):
    for i, record in enumerate(list_of_records):
        print('%s. [%s] %s' % (i, record['file'], record['title']))


if len(sys.argv) > 1:
    command = str(sys.argv[1])
    print('Command: ' + command)
    if command == 'add':
        at_index = int(sys.argv[2])
        game_filename = str(sys.argv[3])
        game_title = str(sys.argv[4])
        insertTitle(at_index, game_filename, game_title)
    elif command == 'show':
        source_directory = os.path.abspath(sys.argv[2])
        data_list = read_all_indices(source_directory)
        display_data(data_list)
    elif command == 'remove':
        at_index = int(sys.argv[2])
        removeByIndex(at_index)
    elif command == 'index':
        source_directory = os.path.abspath(sys.argv[2])
        target_directory = os.path.abspath(sys.argv[3])
        directoryToIndex(source_directory, target_directory)
    elif command == 'index_and_move':
        source_directory = os.path.abspath(sys.argv[2])
        target_directory = os.path.abspath(sys.argv[3])
        directoryToIndex(source_directory, target_directory, do_move=True)
    elif command == 'merge':
        source_directory_one = os.path.abspath(sys.argv[2])
        source_directory_two = os.path.abspath(sys.argv[3])
        target_directory = os.path.abspath(sys.argv[4])

        data_one = read_all_indices(source_directory_one)
        data_two = read_all_indices(source_directory_two)
        data_list = merge_indices_sorted(data_one, data_two, source_directory_one)

        write_index_list(data_list, target_directory)
    elif command == 'title_convert':
        source_directory = os.path.abspath(sys.argv[2])
        lfn_to_title_files(source_directory)
    elif command == 'index_to_csv':
        source_directory = os.path.abspath(sys.argv[2])
        csv_path = os.path.join(source_directory, '_index.csv')
        data_list = read_all_indices(source_directory)
        write_csv(csv_path, data_list)
    elif command == 'csv_to_index':
        source_directory = os.path.abspath(sys.argv[2])
        csv_path = os.path.join(source_directory, '_index.csv')
        data_list = read_csv(csv_path)
        data_list.sort(key=sort_key)
        write_index_list(data_list, source_directory)
    elif command == 'rebat':
        source_directory = os.path.abspath(sys.argv[2])
        recreate_batch_files(source_directory)
