# Reinsertion script for 46 Okunen Monogatari: The Shinka Ron.

# Crashes to keep in mind:
# 1) Crash on entering History/Encyclopedia
# Seems to be related to either the Yes/No/Cancel (right before calls to SINKA.DAT) or creature name length changes.
# Workaround for now is using creature names with the same length as the jp versions.
# Will have to look closer at what causes the
# The culprit is probably some kind of change to the location of a ref to SINKA.DAT around 0x11870.
# Editing yes/no/cancel breaks Encyclopedia. If I keep them the same length ("No    ") it seems fine.
# But can I edit the creatures??? Nope, that breaks it.
# With all creature names except Thelodus? Nope, Encyclopedia crashes.
# What about just Thelodus? Nope, that breaks it.
# What about "Thelodus  "? Yeah, that works fine.
# They both work without the creature names.
# TODO: Can I extend the name-length of creatures you can't become without an issue?
# All the creatures with short names are stuff like jellyfish, coral, urchin... stuff you can't evolve into.
# Maybe I can get away with extending their names without causing an encyclopedia crash...

# 2) Crash on changing maps.
# I have to split up the blocks exactly right! Gotta place the spaces right before filenames...
# I wonder how sensitive it is? Do I need to do this for every .GDT image, or just new maps or exes?
# More importantly, I wonder why the pointer adjustments themselves don't seem to have any effect...
# TODO: Look really closely and see which pointers are getting adjusted, particularly the filename ones.

# TODO: Game boots to black screen when the first block is filled in...
# Probably has something to do with a poorly placed space, or a bad determination of blocks to begin with?

# TODO: Crazy shit happens when trying to confirm an evolution.
# When there are creature names (different lengths), you don't get a yes/no choice and it gets glitchy.
# (But it's fine when you use equal-length creature names.)
# Fine when menu items & intro thelodus dialogue are inserted.
# First dialogue block (& evo files) doesn't break it.
# Something in the end-of-first-map dialogue breaks it...
# Related: "Is this alright?" choices "0, 6, es"
# and "Is this alright?" choice 0.
#  Fine with yes/no/cancel, menu items, evo files/cancel. Issue might be with creature names??

# TODO: Extra menu item when first dialogue block is filled in. "There was a hidden Hemicyclapsis!"
# Something is going wrong with the very first block - jut "cancel" being filled in messes it up.
# Workaround: Use "Cancel    ".

# TODO: Weird stuff going on with "Escape." Is it getting replaced somewhere else??

# TODO: Moving overflow to the error block/spare block.
    # 0) Actually figure out where they are
    # 1) In the rom, replace the jp text with equivalent number of spaces
    # 2) Replace all of the error block with equivalent number of spaces
    # 3) Place all the text in the error block (what about control codes???)
    # 4) Rewrite all the pointer values to point to new locations
 # What about control codes??? If I move text from one block to another, I'll need to move hte control code as
# Note the first instance of overflow, slice it until the end of the block, save that raw code for later.

from __future__ import division
import os
import math
from binascii import unhexlify
from utils import *
from openpyxl import load_workbook
from shutil import copyfile
from collections import OrderedDict

script_dir = os.path.dirname(__file__)
src_path = os.path.join(script_dir, 'original_roms')
dest_path = os.path.join(script_dir, 'patched_roms')

src_rom_path = os.path.join(src_path, "46 Okunen Monogatari - The Sinkaron (J) A user.FDI")
dest_rom_path = os.path.join(dest_path, "46 Okunen Monogatari - The Sinkaron (J) A user.FDI")

copyfile(src_rom_path, dest_rom_path)

dump_xls = "shinkaron_dump_test.xlsx"
pointer_xls = "shinkaron_pointer_dump.xlsx"

files_to_translate = ['ST1.EXE', 'SINKA.DAT']

def get_translations(file, dump_xls):
    # Parse the excel dump and return a dict full of translation tuples.
    trans = OrderedDict() # translations[offset] = (japanese, english)
    
    wb = load_workbook(dump_xls)
    ws = wb.get_sheet_by_name(file)

    total_rows = total_replacements = 0
    overflow_block_lo, overflow_block_hi = spare_block[file]  # Doesn't need translations.

    for row in ws.rows[1:]:  # Skip the first row, it's just labels
        total_rows += 1
        offset = int(row[0].value, 16)

        if (offset >= overflow_block_lo) and (offset <= overflow_block_hi):
            continue

        japanese = row[2].value
        english = row[4].value

        if english:
            total_replacements += 1
        else:
            english = ""

        trans[offset] = (japanese, english)

    translation_percent = int(math.floor((total_replacements / total_rows) * 100))
    #for o, (_, eng) in trans.iteritems():
    #    print hex(o), eng
    print file, str(translation_percent) + "% complete"

    return trans

def get_dat_translations(file, dump_xls):
    # I failed to record accurate offsets for the .dat files, and I'm paying the price.
    # But I can load up a list full of (jp, eng) tuples and replace the first instance of each one,
    # and it should be fine.
    trans = []
    wb = load_workbook(dump_xls)
    ws = wb.get_sheet_by_name(file)

    total_rows = total_replacements = 0
    for row in ws.rows[1:]:
        total_rows += 1
        japanese = row[2].value
        english = row[4].value
        if english:
            total_replacements += 1
        else:
            english = ""
        trans.append((japanese, english))
    translation_percent = int(math.floor((total_replacements / total_rows) * 100))
    print file, str(translation_percent) + "% complete"
    return trans

def get_pointers(file, ptr_xls):
    # Parse the pointer excel, calculate differences in pointer values,
    # and return dictionaries of pointers and diffs.
    ptrs = OrderedDict()              # text_offset: pointer_offset
    ptr_diffs = OrderedDict()         # text_offset: diff
    ptr_count = 0

    pointer_diff = 0           # Cumulative diff.
    previous_text_offset = file_blocks[file][0][0]

    previous_text_block = 0
    current_text_block = 0
    current_block_end = file_blocks[file][0][1]

    pointer_wb = load_workbook(ptr_xls)
    pointer_sheet = pointer_wb.get_sheet_by_name("Sheet1") # For now, they are all in the same sheet... kinda ugly.

    for row in pointer_sheet.rows:
        if row[0].value != file:
            continue                          # Access ptrs for the current file only.

        ptr_count += 1
            
        text_offset = int(row[1].value, 16)
        pointer_offset = int(row[2].value, 16)
        ptrs[text_offset] = pointer_offset
        if get_current_block(text_offset, file):
            current_text_block = get_current_block(text_offset, file)
        #first_overflow = first_offset_in_block(file, current_text_block, overflow_text)

        if (current_text_block > previous_text_block) and current_text_block:
            current_block_end = file_blocks[file][current_text_block][1]
            pointer_diff = 0

        #new_text_offset = text_offset + pointer_diff
        #if first_overflow:
        #    if (new_text_offset > first_overflow) and (new_text_offset < current_block_end):
        #        # Pointers are tricky. We to store the ones between the overflow text and the end of the block
        #        # but not the pointers between blocks normally.
        #        print hex(text_offset), "overflows past", hex(current_block_end), "with diff", pointer_diff
        #        overflow_text.append(text_offset)

        #try:
        #    current_block_end = file_blocks[file][current_text_block][1] # the hi value.
        #except TypeError:
        #    pass
        #print hex(current_block_end)
        # Rather than look for something with the exact pointer, look for any translated text with a value between previous_pointer_offset (excl) and text_offset (incl)
        # Calculate the diff, then add it to pointer_diff. There might be three or more bits of text betweeen the pointers (ex. dialogue)

        lo = previous_text_offset
        hi = text_offset
        for n in range((lo), (hi)):
            try:
                jp, eng = translations[n]
                len_diff = len(eng) - (len(jp)*2)

                #end_of_string = n + len(eng) + pointer_diff
                #if end_of_string > current_block_end:
                #    print hex(n), "overflows past", hex(current_block_end), "with diff", pointer_diff, "and len", len(eng)
                #    overflow_text.append(n)
                    # When you first hit overflow, they have totally different pointer diffs anyway
                    # So reset pointer_diff to have a fresh start when the new block begins.
                    #pointer_diff = 0
                    # TODO: Hmm... if you reset the first thing at the end of a block, it may not catch the rest...
                    # Gotta slice the rest of the block and save it somewhere for reinsertion in the spare block.

                #print current_text_block, previous_text_block
                #if current_text_block != previous_text_block:
                    # First text in a new block. Reset the pointer diff.
                #    pointer_diff = 0
                    # Then, add all the poitners that got missed between the first and end.
                    #print previous_text_block
                #    first = first_offset_in_block(file, previous_text_block, overflow_text)
                    #last = current_block_end
                #    print "lo hi", hex(first), hex(n)
                #    for p, t in ptrs.iteritems():
                #        if (p < first) and (p >= n):
                #            overflow_text.append(t)
                #            print "adding", hex(t), "to overflow"

                # If the eng part of the translation is blank, don't calculate a pointer diff.
                # But we still want it to be put in the overflow_text list.
                if not eng:
                    continue

                pointer_diff += len_diff
            except KeyError:
                continue

        if current_text_block:
            previous_text_block = current_text_block
        previous_text_offset = text_offset
        ptr_diffs[text_offset] = pointer_diff
        #print hex(text_offset), ptr_diffs[text_offset]

    #print "Pointer count: ", ptr_count
    return ptrs, ptr_diffs


def get_file_strings(rom_path):
    file_strings = {}
    for file in files_to_translate:
        start = file_start[file]
        length = file_length[file]
        file_strings[file] = file_to_hex_string(rom_path, start, length)
    return file_strings


def get_block_strings(file, rom_path):
    block_strings = []
    for index, block in enumerate(file_blocks[file]):
        lo, hi = block
        block_length = hi - lo
        block_start = file_start[file] + lo

        block_strings.append(file_to_hex_string(rom_path, block_start, block_length))
    return block_strings

def get_overflow(file, rom_path, overflow_text):
    # Fetch all the overflow/remainder of a block, text and control codes.
    overflow_locs = overflow_text
    overflow_bytestrings = []
    f = open(rom_path, 'rb')
    for (block_lo, block_hi), i in file_blocks[file].enumerate():
        end_of_block = block_hi
        for text in overflow_locs:
            if (text >= block_lo) and (text <= block_hi):
                start = file_start[file] + text
                length = (block_hi - block_lo) - text
                overflow_bytestrings.append(file_to_hex_string(file, start, length))
            # Then remove the rest of the overflow text in that block.
            for text in overflow_locs:
                if (text >= block_lo) and (text <= block_hi):
                    overflow_locs.remove(text)
    return overflow_bytestrings


def edit_pointers(file, pointer_diffs, file_string):
    patched_file_string = file_string

    pointer_constant = pointer_constants[file]
    overflow_block_lo, overflow_block_hi = spare_block[file]

    adjustment_count = 0

    for text_location, diff in pointer_diffs.iteritems():
        #if diff == 0:
        #    continue
        # TODO: Redirect the old error message strings. (Or just don't, since the patch is perfect and they'll never show up?)
        if (text_location >= overflow_block_lo) and (text_location <= overflow_block_hi):
            #print "It's an error code ", text_location
            text_location = overflow_block_lo

        pointer_location = pointers[text_location]

        old_value = text_location - pointer_constant
        old_bytes = pack(old_value)
        old_bytestring = "{:02x}".format(old_bytes[0]) +"{:02x}".format(old_bytes[1]) 

        #print hex(pointer_location)
        #print "old:", old_value, old_bytes, old_bytestring

        new_value = old_value + diff

        new_bytes = pack(new_value)
        new_bytestring = "{:02x}".format(new_bytes[0]) +"{:02x}".format(new_bytes[1]) 
        #print "new:", new_value, new_bytes, new_bytestring

        location_in_string = pointer_location * 2

        old_slice = patched_file_string[location_in_string:]
        new_slice = old_slice.replace(old_bytestring, new_bytestring, 1)
        #print patched_file_string.index(old_slice)
        patched_file_string = patched_file_string.replace(old_slice, new_slice, 1)

        adjustment_count += 1

    #print compare_strings(file_string, patched_file_string)
    #print "Pointer adjustments:", adjustment_count
    return patched_file_string


def edit_text(file, translations, rom_string):
    # Replace each jp bytestring with eng bytestrings in the text blocks.
    # Return a new file string.
    creature_block_lo, creature_block_hi = creature_block[file]
    previous_replacement_offset = 0

    for original_location, (jp, eng) in translations.iteritems():
        if eng == "":
            # If there treally is no english translation, skip the replacement.
            continue

        #current_block_end = file_blocks[file][get_current_block(original_location, file)][1]
        #print hex(current_block_end)
        #try:
        #    diff = pointer_diffs[original_location]
        #except KeyError:
        #    try:
        #        original_location -= 1
        #        diff = pointer_diffs[original_location]
        #    except KeyError:
        #        print "KeyError", hex(original_location)
        #        diff = 0

        #new_string_end = (original_location) + len(jp)*2 + diff

        #if new_string_end > current_block_end:
        #    print "overflow at", hex(original_location-1), "past", current_block_end
        #    overflow_text.append(original_location-1)
        #    eng = ""

        if original_location in overflow_text:
            eng = ""

        jp_bytestring = ""
        sjis = jp.encode('shift-jis')
        for c in sjis:
            hx = "%02x" % ord(c)
            if hx == '20': # SJS spaces get mis-encoded as ascii, which means the strings don't get found. Fix to 81-40
                hx = '8140'
            jp_bytestring += hx

        eng_bytestring = ""
        for c in eng:
            eng_bytestring += "%02x" % ord(c)

        if (original_location >= creature_block_lo) and (original_location <= creature_block_hi):
            this_string_diff = (len(jp)*2) - len(eng)
            if this_string_diff >= 0:
                eng_bytestring += "00"*this_string_diff
            else:
                # Append the 00s to the jp_bytestring so they get replaced - keep the length the same.
                jp_bytestring += "00"*((-1)*this_string_diff)

        #print hex(original_location)
        current_block = get_current_block(original_location, file)
        block_string = block_strings[current_block]
        try:
            old_slice = block_string[previous_replacement_offset:]
            i = old_slice.index(jp_bytestring)//2
        except ValueError:
            previous_replacement_offset = 0
            old_slice = block_string
            # Why is block_strings[0] different from the one that is set before this in edit_dat_text?
            i = old_slice.index(jp_bytestring)//2

        new_slice = old_slice.replace(jp_bytestring, eng_bytestring, 1)
        new_block_string = block_strings[current_block].replace(old_slice, new_slice, 1)
        block_strings[current_block] = new_block_string

        previous_replacement_offset += i

    file_string = file_strings[file]
    patched_file_string = file_string

    print overflow_text

    for i, blk in enumerate(block_strings):
        block_diff = len(blk) - len(original_block_strings[i])   # if block is too short, negative; too long, positive
        print len(original_block_strings[i]), len(blk)
        print block_diff
        if block_diff < 0:
            number_of_spaces = ((-1)*block_diff)//2
            inserted_spaces_index = file_blocks[file][i][0] + (len(blk)//2)
            blk += '20' * number_of_spaces  # Fill it up with ascii 20 (space)

            print number_of_spaces, "added at", hex(inserted_spaces_index)
        elif block_diff > 0:
            print "Something went wrong, it's too long"

        patched_file_string = patched_file_string.replace(original_block_strings[i], blk, 1)
        
    rom_string = rom_string.replace(file_string, patched_file_string)

    return rom_string

def edit_dat_text(file, file_string):
    translations = get_dat_translations(file, dump_xls)

    patched_file_string = file_string

    for (jp, eng) in translations:
        if eng == "":
            continue
        jp_bytestring = ""
        sjis = jp.encode('shift-jis')
        for c in sjis:
            hx = "%02x" % ord(c)
            if hx == '20': # SJS spaces get mis-encoded as ascii, which means the strings don't get found. Fix to 81-40
                hx = '8140'
            jp_bytestring += hx

        eng_bytestring = ""
        for c in eng:
            eng_bytestring += "%02x" % ord(c)
        patched_file_string = patched_file_string.replace(jp_bytestring, eng_bytestring, 1)
    return patched_file_string

def change_starting_map(map_number):
    # Current map: MAP105.MAP
    # Change to MAP103.MAP to test combat more easily?
    starting_map_number_location = 0xedaa + file_start['ST1.EXE']
    new_map_bytes = str(map_number).encode()
    f = open(dest_rom_path, 'rb+')
    f.seek(starting_map_number_location)
    f.write(new_map_bytes)
    f.close()
    # omg this worked on the first try

full_rom_string = file_to_hex_string(dest_rom_path)
file_strings = get_file_strings(dest_rom_path)

for file in files_to_translate:
    if file == "SINKA.DAT" or file == 'SEND.DAT':
        # Edit the file separately. That'll have to do for now.
        dat_path = os.path.join(src_path, file)
        dest_dat_path = os.path.join(dest_path, file)
        dat_file_string = file_to_hex_string(dat_path)

        patched_dat_file_string = edit_dat_text(file, dat_file_string)

        with open(dest_dat_path, "wb") as output_file:
            data = unhexlify(patched_dat_file_string)
            output_file.write(data)
        continue

    overflow_text = []
    overflow_hex = []

    translations = get_translations(file, dump_xls)
    pointers, pointer_diffs = get_pointers(file, pointer_xls)

    #print overflow_text

    # First, rewrite the pointers - that doesn't change the length of anything.
    old_file_string = file_strings[file]
    new_file_string = edit_pointers(file, pointer_diffs, file_strings[file])
    full_rom_string = full_rom_string.replace(old_file_string, new_file_string)
    file_strings[file] = new_file_string

    # Then, rewrite the actual text.
    #min_pointer_diff = min(pointer_diffs.itervalues()) # What's this for?
    #dest_rom.seek(file_start[file])

    # Then get individual strings of each text block, and put them in a list.
    block_strings = get_block_strings(file, dest_rom_path)
    original_block_strings = list(block_strings)   # Needs to be copied - simple assignment would just pass the reference.

    full_rom_string = edit_text(file, translations, full_rom_string)

    # Write the data to the patched file.
    with open(dest_rom_path, "wb") as output_file:
        data = unhexlify(full_rom_string)
        output_file.write(data)

#change_starting_map(105)
# 100: open water, volcano cutscene immediately, combat
# 101: caves, hidden hemicyclapsis (fast combat example)
# 105: (default) thelodus sea