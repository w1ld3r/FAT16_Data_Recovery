import struct
import argparse
import sys
import os
from pathlib import Path

MAGIC_NUMBER1 = b"\x4b\x17\x4c\x17\x4d\x17\xff\xff"
MAGIC_NUMBER2 = b"\x69\x32\x69\x32\x00\x00\x39\x6b\x69\x32"
EXTRACT_DIRECTORY = "extract"

def parse_arguments():
    desc = """Extract files from FAT16 file system"""
    parser = argparse.ArgumentParser(prog='fat16_extract', description=desc)
    parser.add_argument('-f', '--file', 
        metavar='File',
        help='FAT16 file system',
        type=argparse.FileType('rb'),
        required=True
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)
    else:
        return get_args(parser.parse_args())

def get_args(args):
    try:
        if args.file:
            return args.file
    except:
        sys.exit('Input not reconize !\n')

def get_root_directory_offset(data):
    offset = 0
    last_offset = 0
    while True:
        offset = data.find(MAGIC_NUMBER1, offset)
        if offset == -1:
            break
        offset += len(MAGIC_NUMBER1)
        last_offset = offset

    offset = last_offset - (last_offset % 16) + 16

    while data[offset] == 0x0:
        offset += 16

    return offset

def get_c2_offset(data, offset):
    while data[offset] != 0x0:
        offset += 16
    while data[offset] == 0x0:
        offset += 16
    return offset

def get_cluster_size(data, root_dir_offset, c2_offset):
    offset = root_dir_offset
    while offset < len(data):
        if data[offset:offset+10] == MAGIC_NUMBER2:
            file1_cluster_offset, = struct.unpack('<B', data[offset+len(MAGIC_NUMBER2):offset+len(MAGIC_NUMBER2)+1])
            file1_size, = struct.unpack('<I', data[offset+len(MAGIC_NUMBER2)+2:offset+len(MAGIC_NUMBER2)+6])
            offset += 16

            while data[offset:offset+10] != MAGIC_NUMBER2:
                offset += 16

            file2_cluster_offset, = struct.unpack('<B', data[offset+len(MAGIC_NUMBER2):offset+len(MAGIC_NUMBER2)+1])

            f_cluster_size = (file1_size + (file1_size % 512)) / (file2_cluster_offset - file1_cluster_offset)
            cluster_size = 512 - (f_cluster_size % 512) + f_cluster_size
            return int(cluster_size)
        else:
            offset += 16
    return 0
    

def get_files(data, root_dir_offset, c2_offset, cluster_size):

    offset = root_dir_offset
    i = 0

    print("┌" + "─" * 45 + "┐")
    print("│\033[1m{:<15}{:>15}{:>15}\033[0m│".format("Filename", "Offset", "Size"))
    print("├" + "─" * 45 + "┤")

    while True:
        offset = data.find(MAGIC_NUMBER2, offset)

        if offset == -1:
            break

        if data[offset-16] == 0xe5:
            file_name = "_" + data[offset-15:offset-8].decode().lower().replace(" ", "")
        else:
            file_name = data[offset-16:offset-8].decode().lower().replace(" ", "")

        file_extension = data[offset-8:offset-5].decode().lower()
        f_name = file_name + "." + file_extension

        offset += len(MAGIC_NUMBER2)

        f_offset, = struct.unpack('<H', data[offset:offset+2])
        f_size, = struct.unpack('<I', data[offset+2:offset+6])

        f_b_offset = c2_offset + (f_offset - 2) * cluster_size
        print("│{:<15}{:>15}{:>15}│".format(f_name, hex(f_b_offset), f_size))

        Path(EXTRACT_DIRECTORY).mkdir(exist_ok=True)
        with open(EXTRACT_DIRECTORY + "/" + f_name, "wb") as wfile:
            wfile.write(data[f_b_offset:f_b_offset + f_size])

        i += 1

    print("└" + "─" * 45 + "┘")
    print("%d files extracted in %s/%s/" % (i, os.getcwd(), EXTRACT_DIRECTORY))

if __name__ == "__main__":
    data = parse_arguments().read()
    root_dir_offset = get_root_directory_offset(data)
    c2_offset = get_c2_offset(data, root_dir_offset)
    if root_dir_offset != c2_offset:
        cluster_size = get_cluster_size(data, root_dir_offset, c2_offset)
        if cluster_size % 512 == 0 and cluster_size >= 512:
            get_files(data, root_dir_offset, c2_offset, cluster_size)