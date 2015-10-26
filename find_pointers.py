# TODO: Someitmes it gets tripped up by a consistent 2nd byte of the pointer, and it counts it as a delimiter. How to avoid this?
# TODO: Define a function to identify pointers that point to other pointer tables - identify whether some segment of the tables' unpacked values are increasing or decreasing by 0x4 the whole time.

import re

files = ['ST1.EXE',]

file_blocks = [('ST1.EXE', ((0xd873, 0xd933), (0xd984, 0x10f85), (0x10fca, 0x11595), (0x117c7, 0x119a3), (0x11d42, 0x1204e))),]

pointers = {}
# hex loc: (hex a, hex b)

pointer_regex = r"(\\x[0-f][0-f]\\x[0-f][0-f](\\x[0-f][0-f]\\x[0-f][0-f]))(\\x[0-f][0-f]\\x[0-f][0-f]\2){2,}"

def unpack(s, t):
    return (t * 0x100) + s
    
def pack(h):
    s = h % 0x100
    t = h // 0x100
    return (s, t)
    
def go_to_pointer(pointer, offset):
    return unpack(pointer[0], pointer[1]) + offset
    
def find_pointers():
    p = re.compile(pointer_regex)
    for file in files:
        in_file = open(file, 'rb')
        print file
        bytes = in_file.read()
        #text.decode('shift_jis', errors='ignore').encode('utf-8')
        only_hex = ""
        for c in bytes:
            #print ord(c)
            only_hex += "\\x%02x" % ord(c)
        #print only_hex
        #print bytes.encode('hex')
        tables = p.finditer(only_hex)
        for table in tables:
            last_part = table.group(3).split('\\x')
            #print last_part
            if last_part[1] == last_part[2] == last_part[3] == last_part[4]: # ignore FFFFFFFFFF sections
                pass
            elif "\\x00\\x00\\x00\\x00" in table.group(0):  # sometimes they sneak by. catch them here
                pass
            else:
                print table.group(0)
                start = table.start() / 4 # divide by four, since 4 characters per byte in our dump)
                stop = table.end() / 4
                count = (stop - start) / 4 # div by 4 again, since 4 bytes per pointer
                delimiter = table.group(2)
                print str(count) + " pointers at " + hex(start) + ", delimiter: " + delimiter
        #out_file = open('dump_' + file, 'w+')
        #out_file.write(only_hex)
        
def find_string_offsets():
    pointeds = []
    diffs = []
    for (file, blocks) in file_blocks:
        for block in blocks:
            print file
            block_start = block[0]
            block_stop = block[1]
            block_length = block_stop - block_start
            in_file = open(file, 'rb')
            in_file.seek(block_start)
            bytes = in_file.read(block_length)
            only_hex = ""
            for c in bytes:
                only_hex += "\\x%02x" % ord(c)
            strings = only_hex.split('\\x00')
            for s in strings:
                if s:
                    string_start = only_hex.index(s)
                    offset = hex(block_start + (string_start / 4))
                    pointeds.append(offset)
                    #string_bytes = s.replace('\\x', '').decode('hex')
                    print offset
                
    for p in range(len(pointeds)-1):
        diff = int(pointeds[p+1], 16) - int(pointeds[p], 16)
        diffs.append(diff)
        print diff
    print pointeds
    print diffs
        
find_string_offsets()