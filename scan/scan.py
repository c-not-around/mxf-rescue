# -*- coding: utf-8 -*-


import sys, os
import traceback


# hdd constants
HDD_SECTOR_SIZE    = 512
# record keys
FILE_HEADER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x02, 0x04, 0x00]
FILE_FOOTER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x04, 0x04, 0x00]
FRAME_HEADER_START = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x04, 0x01, 0x01, 0x00]
FRAME_DATA_START   = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x06, 0x0E, 0x06, 0x0D, 0x03, 0x19, 0x01, 0x45, 0x00]
FRAME_FOOTER_START = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x16, 0x04, 0x03, 0x00]
# recod sizes
FILE_HEADER_SIZE   = 11264
FILE_FOOTER_SIZE   = 10800
FRAME_HEADER_SIZE  = 512
FRAME_DATA_SIZE    = 7452672
FRAME_FOOTER_SIZE  = 36352
FRAME_SIZE         = FRAME_HEADER_SIZE + FRAME_DATA_SIZE + FRAME_FOOTER_SIZE
# offsets of duration in file header
DURATION_OFFSETS   = [0x0BC8, 0x0C27, 0x0CEF, 0x0D6F, 0x15F2, 0x0E37, 0x0EB7, 0x0F7F, 0x0FFF, 0x10C7, 0x1147, 0x120F,
                      0x128F, 0x1357, 0x13D7, 0x1593, 0x16BA, 0x173A, 0x1802, 0x1882, 0x194A, 0x19CA, 0x1A92, 0x1B12,
                      0x1BDA, 0x1C5A, 0x1D22, 0x1DA2]
# offsets of timestamps in file header, file footer
TIMESTAMPS_OFFSETS = [0x0C1B, 0x15E6]

# load file header, file footer
fh = open("header.mxf", "rb")
fh.seek(0)
file_header = fh.read(FILE_HEADER_SIZE)
fh.close()
fh = open("footer.mxf", "rb")
fh.seek(0)
file_footer = fh.read(FILE_FOOTER_SIZE)
fh.close()

# key compare
def key_cmp(key, pattern):
    for i in range(16):
        if key[i] != pattern[i]:
            return False
    return True
# convert from bcd
def from_bcd(x):
    return 10 * (x >> 4) + (x & 0x0F)
# convert to timestamp
def to_timestamp(h, m, s, f):
    return f + 25 * (s + 60 * (m + 60 * h))
# insert value to buffer
def set_value(fs, base, offsets, value, length):
    buffer = [0 for i in range(length)]
    for i in range(length-1, -1, -1):
        buffer[i] = value & 0xFF
        value >>= 8
    for offset in offsets:
        fs.seek(base+offset)
        fs.write(bytes(buffer))
# check key in block
def check_key(fs, offset, key):
    adr = offset & 0xFFFFFFFFFFFFFE00
    ost = offset - adr
    try:
        fs.seek(adr)
    except:
        raise Exception("seek() error with offset = 0x%016X" % offset)
        #print("seek() error with offset = 0x%016X" % offset)
        #return 0
    block = fs.read(HDD_SECTOR_SIZE)[ost:]
    if len(block) == 0:
        return -1
    if key_cmp(block, key):
        return 1
    return 0
# find next full frame
def scan_pass(fs, offset):
    result = check_key(fs, offset, FRAME_HEADER_START)
    if result == 1:
        offset += FRAME_HEADER_SIZE
        result = check_key(fs, offset, FRAME_DATA_START)
        if result == 1:
            offset += FRAME_DATA_SIZE
            result = check_key(fs, offset, FRAME_FOOTER_START)
    return result
# write file header, file footer and set metadata to destination file
def complete_file(fs, f_count, f_timestamp, f_fname):
    pos = FILE_HEADER_SIZE + f_count * FRAME_SIZE
    # file header
    fs.seek(0)
    fs.write(file_header)
    set_value(fs, 0, DURATION_OFFSETS,   f_count,     4)
    set_value(fs, 0, [0x002C],           pos,         8)
    set_value(fs, 0, TIMESTAMPS_OFFSETS, f_timestamp, 4)
    # file footer
    fs.seek(pos)
    fs.write(file_footer)
    set_value(fs, pos, DURATION_OFFSETS,         f_count,     4)
    set_value(fs, pos, [0x001C, 0x002C, 0x2A23], pos,         8)
    set_value(fs, pos, TIMESTAMPS_OFFSETS,       f_timestamp, 4)
    fs.close()
    # log message
    print("%i frames saved to file <%s>\r\n" % (f_count, f_fname))

# scan task
def main():
    # target disk select
    disks = ["%s:" % i for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists("%s:" % i)]
    for d in range(len(disks)):
        print("%i - %s" % (d, disks[d]))
    disk = open("\\\\.\\" + disks[int(input("select disk: "))], "rb")
    # destinaton path select
    path = input("select destination path: ")
    # scan cycle
    offset      = 0
    f_count     = 0
    f_prev_no   = None
    f_timestamp = None
    f_fname     = None
    while True:
        r = scan_pass(disk, offset)
        # scan pass failed -> end of disk space
        if r == -1:
            break
        # another frame found
        if r == 1:
            disk.seek(offset)
            buffer = disk.read(FRAME_SIZE)
            # get metadata
            n = 0
            for i in range(5):
                n <<= 8
                n |= buffer[0x16+i]
            Y = from_bcd(buffer[0x043])
            M = from_bcd(buffer[0x042])
            D = from_bcd(buffer[0x041])
            h = from_bcd(buffer[0x040])
            m = from_bcd(buffer[0x03F])
            s = from_bcd(buffer[0x03E])
            f = from_bcd(buffer[0x03D])
            # complete file, if this frame is last in series
            if (f_prev_no != None) and ((n-1) != f_prev_no):
                complete_file(fh, f_count, f_timestamp, f_fname)
                f_count   = 0
                f_prev_no = None
                f_fname   = None
            # init first frame in current series
            if f_count == 0:
                f_timestamp = to_timestamp(h, m, s, f)
                f_fname     = "%s\\%016X.mxf" % (path, offset)
                fh = open(f_fname, "wb")
            # copy frame to destinaton file
            fh.seek(FILE_HEADER_SIZE+f_count*FRAME_SIZE)
            fh.write(buffer)
            # print frame info
            print("%016X: FRAME no=%i %04i-%02i-%02i %02i:%02i:%02i.%02i" % (offset, n, Y, M, D, h, m, s, f*4))
            # to next frame
            f_count  += 1
            f_prev_no = n
            offset   += FRAME_SIZE
        else:
            # the sequence was interrupted -> complete file
            if f_count != 0:
                complete_file(fh, f_count, f_timestamp, f_fname)
                f_count   = 0
                f_prev_no = None
                f_fname   = None
            # jump to next block
            offset += 256
            # scan progress info
            if (offset & 0x000000003FFFFFFF) == 0:
                print("%iGb scaned." % (offset/(1024**3)))
    disk.close()
    print("done.")

try:
    main()
except Exception as ex:
    print("main function ended with error: %s" % ex)
    traceback.print_exc()
print("press any key and <Enter> ...")
input()
