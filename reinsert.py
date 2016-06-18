""" Reinsertion script for 46 Okunen Monogatari: The Shinka Ron."""

from collections import OrderedDict

from utils import SRC_ROM_PATH, DEST_ROM_PATH
from utils import pack, get_current_block
from utils import sjis_to_hex_string, sjis_to_hex_string_preserve_spaces 
from utils import ascii_to_hex_string
from cheats import change_starting_map

from disk import Disk, EXEFile, DATFile

FILES_TO_TRANSLATE = ['ST1.EXE', 'ST2.EXE', 'ST3.EXE', 'ST4.EXE', 'ST5.EXE', 'ST5S1.EXE',
                      'ST5S2.EXE', 'ST5S3.EXE', 'ST6.EXE', 'OPENING.EXE'] #'SINKA.DAT', 
                      #'ENDING.EXE', 'SEND.DAT']

# for testing the oh-so-problematic Ch5:
#FILES_TO_TRANSLATE = ['ST5.EXE', 'ST5S1.EXE', 'ST5S2.EXE', 'ST5S3.EXE']

def edit_text(file):
    """Replace each japanese string with the translated english string."""
    # TODO: If I can make this iterate through blocks instead of strings in translations,
    # it'd be a bit simpler! No more checking what block we're in constantly.
    pointer_diff = 0
    previous_text_offset = file.blocks[0].start
    previous_replacement_offset = 0
    current_block = file.blocks[0]
    previous_block_index = 0
    is_overflowing = False
    overflow_bytestrings = OrderedDict()

    for original_location, (jp, eng) in file.translations.iteritems():
        # Check if we've changed blocks yet.
        block_index = get_current_block(original_location, file)
        if block_index != previous_block_index:
            # Reset all relevant variables.
            current_block = file.blocks[block_index]
            pointer_diff, previous_replacement_offset = 0, 0
            is_overflowing = False

        previous_block_index = block_index

        # If it's overflowing already, all the following strings get replaced anyway.
        # Skip strings until reaching the next block.
        if is_overflowing:
            continue

        jp_bytestring = sjis_to_hex_string(jp)
        eng_bytestring = ascii_to_hex_string(eng)

        # jp_bytestring might include ASCII; if it's not found, try the ascii preserving method.
        try:
            j = current_block.blockstring.index(jp_bytestring)
        except ValueError: # substring not found
            jp_bytestring = sjis_to_hex_string_preserve_spaces(jp)

        if eng_bytestring:
            new_text_offset = original_location + len(eng_bytestring)//2 + pointer_diff
        else:
            new_text_offset = original_location + len(jp_bytestring)//2 + pointer_diff

        if new_text_offset >= current_block.stop:
            is_overflowing = True
            # Pointers usually point to control codes before the text. So look for a recent pointer.
            # But don't backtrack as far as previous_text_offset (maybe already translated)
            recent_pointer = file.most_recent_pointer(previous_text_offset, original_location)

            start_in_block = (recent_pointer - current_block.start)*2
            overflow_bytestring = current_block.original_blockstring[start_in_block:]
            # Store the start and end of the overflow bytestring, 
            # to make sure all pointers are adjusted in the range.
            overflow_lo, overflow_hi = recent_pointer, current_block.stop
           
            overflow_bytestrings[(overflow_lo, overflow_hi)] = overflow_bytestring

        if not is_overflowing:
            file.edit_pointers_in_range((previous_text_offset, original_location), pointer_diff)

        previous_text_offset = original_location

        if eng == "":
            # No replacement necessary - pointers are edited, so we're done here.
            continue

        if is_overflowing:
            # Then we want to blank the entire overflow bytestring.
            # So use the rest of the function already there to do that.
            eng = ""
            jp_bytestring = overflow_bytestring

        # Recalculate in case it got altered due to overflow.
        eng_bytestring = ascii_to_hex_string(eng)
        this_string_diff = (len(eng_bytestring) - len(jp_bytestring)) // 2

        # Pad creature name strings.
        if file.creature_block:
            if file.creature_block.start <= original_location <= file.creature_block.stop:
                if this_string_diff <= 0:
                    eng_bytestring += "00"*(this_string_diff*(-1))
                else:
                    jp_bytestring += "00"*(this_string_diff)
                this_string_diff = (len(eng_bytestring) - len(jp_bytestring)) // 2

        pointer_diff += this_string_diff

        old_slice = current_block.blockstring[previous_replacement_offset*2:]
        i = old_slice.index(jp_bytestring)//2
        previous_replacement_offset += i//2
        new_slice = old_slice.replace(jp_bytestring, eng_bytestring, 1)

        j = file.blocks[block_index].blockstring.index(old_slice)
        current_block.blockstring = current_block.blockstring.replace(old_slice, new_slice, 1)

    # If there's a spare block, fill it with the overflow.
    if file.spare_block:
        move_overflow(file, overflow_bytestrings)
    elif overflow_bytestrings:
        print overflow_bytestrings
        # TODO: This is important, since it appears to be overflowing in ST5S2. Activate later!
        #assert not overflow_bytestrings, "Things are overflowing but there's no room for them!'"

    for block in file.blocks:
        block.incorporate()


def move_overflow(file, overflow_bytestrings):
    """Insert the overflow strings in the spare block, and reroute their pointers."""
    file.spare_block.blockstring = ""

    for (lo, hi), bytestring in overflow_bytestrings.iteritems():
        # (How much functionality is this repeating??)
        # The first pointer must be adjusted to point to the beginning of the spare block.
        pointer_diff = (file.spare_block.start - lo) + len(file.spare_block.blockstring)//2
        previous_text_location = lo
        # Find all the translations that need to be applied.
        for i in [i for i in range(lo, hi) if i in file.translations]:
            japanese, english = file.translations[i]

            jp_bytestring = sjis_to_hex_string(japanese)
            eng_bytestring = ascii_to_hex_string(english)

            this_string_diff = len(eng_bytestring) - len(jp_bytestring) // 2
            j = bytestring.index(jp_bytestring)
            bytestring = bytestring.replace(jp_bytestring, eng_bytestring)
            # TODO: Again, why -1? Gotta justify magic numbers.
            file.edit_pointers_in_range((previous_text_location-1, i), pointer_diff)
            previous_text_location = i
            pointer_diff += this_string_diff

        file.spare_block.blockstring += bytestring

    assert len(file.spare_block.blockstring)//2 <= file.spare_block.stop - file.spare_block.start
    file.spare_block.incorporate()


if __name__ == '__main__':
    DiskA = Disk(SRC_ROM_PATH, DEST_ROM_PATH)

    for filename in FILES_TO_TRANSLATE:
        if filename in ('SINKA.DAT', 'SEND.DAT'):
            gamefile = DATFile(DiskA, filename)
            gamefile.translate()
            gamefile.write()

        else:
            gamefile = EXEFile(DiskA, filename)

            # Then get individual strings of each text block, and put them in a list.
            block_strings = gamefile.blocks
            original_block_strings = list(block_strings)

            edit_text(gamefile)

            gamefile.incorporate()
            gamefile.write()
            gamefile.report_progress()

    DiskA.write()

    #change_starting_map('ST1.EXE', 100)
    #change_starting_map('ST5.EXE', 600)

# 100: open water, volcano cutscene immediately, combat
# 101: caves, hidden hemicyclapsis, Gaia's Heart in upper right
# 202: useful! take one step, die from fresh water, respawn as an Ichthyostega!
# 204: mountain, right near the top! easy access to combat, cut scenes - plus fish equivs of animals

# testing new ch5 starting maps:
# 600: ch6 world map; can't use menus?; dying (at imp guy in africa, ch5) sends you to glitch land ch5