# -*- coding: utf-8 -*-


import sys, os


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
# offsets of duration in file header
DURATION_OFFSETS   = [0x0BC8, 0x0C27, 0x0CEF, 0x0D6F, 0x15F2, 0x0E37, 0x0EB7, 0x0F7F, 0x0FFF, 0x10C7, 0x1147, 0x120F,
                      0x128F, 0x1357, 0x13D7, 0x1593, 0x16BA, 0x173A, 0x1802, 0x1882, 0x194A, 0x19CA, 0x1A92, 0x1B12,
                      0x1BDA, 0x1C5A, 0x1D22, 0x1DA2]
# offsets of timestamps in file header, file footer
TIMESTAMPS_OFFSETS = [0x0C1B, 0x15E6]


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
# insert timestamp to buffer
def set_timestamp(fs, ts):
    buf = [0, 0, 0, 0]
    for i in range(3, -1, -1):
        buf[i] = ts
        ts >>= 8
        offset += 1
    for o in TIMESTAMPS_OFFSETS:
        fs.seek(o)
        fs.write(buf)


# load file header, file footer
f = open("header.mxf", "rb")
f.seek(0)
file_header = f.read(FILE_HEADER_SIZE)
f.close()
f = open("footer.mxf", "rb")
f.seek(0)
file_footer = f.read(FILE_FOOTER_SIZE)
f.close()

# target disk select
'''disks = ["%s:" % i for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists("%s:" % i)]
for d in range(len(disks)):
    print("%i - %s" % (d, disks[d]))
d = int(input("select disk: "))
disk = "\\\\.\\" + disks[d]'''
disk = r"D:\temp\mxf\work\01707.mxf"

# destinaton path select
path = input("select destination path: ")

# scan cycle
d = open(disk, "rb")
offset = 0
f_header_exists = False
f_body_exists   = False
while True:
    d.seek(offset)
    block = d.read(256)
    # end of disk space
    if len(block) == 0:
        break
    # check keys
    if key_cmp(block, FRAME_HEADER_START):
        n = 0
        for i in range(5):
            n <<= 8
            n |= block[0x16+i]
        Y = from_bcd(block[0x043])
        M = from_bcd(block[0x042])
        D = from_bcd(block[0x041])
        h = from_bcd(block[0x040])
        m = from_bcd(block[0x03F])
        s = from_bcd(block[0x03E])
        f = from_bcd(block[0x03D])
        print("%016X: FRAME_HEADER no=%i %04i-%02i-%02i %02i:%02i:%02i.%02i" % (offset, n, Y, M, D, h, m, s, f))
        f_header_exists = True
    elif key_cmp(block, FRAME_DATA_START):
        print("%016X: FRAME_DATA" % offset)
        f_body_exists = True
    elif key_cmp(block, FRAME_FOOTER_START):
        print("%016X: FRAME_FOOTER" % offset)
        
    # to next block
    offset += 256
d.close()
print("done.")
