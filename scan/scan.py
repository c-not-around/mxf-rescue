# -*- coding: utf-8 -*-


import sys, os


FILE_HEADER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x02, 0x04, 0x00]
FILE_FOOTER_START  = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x02, 0x01, 0x01, 0x04, 0x04, 0x00]
FRAME_HEADER_START = [0x06, 0x0E, 0x2B, 0x34, 0x02, 0x05, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x04, 0x01, 0x01, 0x00]
FRAME_DATA_START   = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x06, 0x0E, 0x06, 0x0D, 0x03, 0x19, 0x01, 0x45, 0x00]
FRAME_FOOTER_START = [0x06, 0x0E, 0x2B, 0x34, 0x01, 0x02, 0x01, 0x01, 0x0D, 0x01, 0x03, 0x01, 0x16, 0x04, 0x03, 0x00]


def key_cmp(key, pattern):
    for i in range(16):
        if key[i] != pattern[i]:
            return False
    return True


disks = ["%s:" % i for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists("%s:" % i)]
for d in range(len(disks)):
    print("%i - %s" % (d, disks[d]))
d = int(input("select disk: "))
disk = "\\\\.\\" + disks[d]

f = open(disk, 'rb')
offset = 7*1024**3
while True:
    f.seek(offset)
    block = f.read(256)
    if len(block) == 0:
        break
    if key_cmp(block, FILE_HEADER_START):
        print("%016X: FILE_HEADER" % offset)
    elif key_cmp(block, FILE_FOOTER_START):
        print("%016X: FILE_FOOTER" % offset)
    elif key_cmp(block, FRAME_HEADER_START):
        v1 = ""
        for i in range(7):
            v1 += "%02X" % block[0x0014+i]
        v2 = ""
        for i in range(8):
            v2 += "%02X" % block[0x003C+i]
        fn = int(block[0x3D])
        fn = 10 * (fn >> 4) + (fn & 0x0F)
        kn = int(block[0x3E])
        print("%016X: FRAME_HEADER %s %s | frame=%i kadr=%i" % (offset, v1, v2, fn, kn))
    elif key_cmp(block, FRAME_DATA_START):
        print("%016X: FRAME_DATA" % offset)
    elif key_cmp(block, FRAME_FOOTER_START):
        print("%016X: FRAME_FOOTER" % offset)
    offset += 256
    if (offset & 0x000000003FFFFFFF) == 0:
        print("%iGb" % (offset/(1024**3)))
f.close()
