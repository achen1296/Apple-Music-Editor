""" This script dumps out a description of what different values occur at different offsets, and how many times. This is useful to look for patterns like:
- What values are even possible at a particular offset?
- Does a particular offset always have a unique value among instances of a certain section type (implying it might be an ID or hash), or can it be shared?
- Are some values extremely common? Can you correlate this with some feature of your library file? """

import json

from library_musicdb import *


if __name__ == "__main__":
    lib = Library()
    ls = (
        LibrarySearcher()
        .descendants_of_type(itma)
    )

    start = 0
    size = 4

    r = []  # fill in a specific list of offsets if you want to narrow focus to them
    # e.g. r = [20, 24, 36]

    offset_values: dict[int, dict[str, int]] = {}
    for s in ls.search(lib):
        for i in (r or range(start, len(s._data), size)):
            if i not in offset_values:
                offset_values[i] = {}
            b = bytes(s._data[i:i+size])

            try:
                unicode = show_control_chars(f" '{b.decode("utf8")}'")
            except UnicodeDecodeError:
                unicode = ""

            if len(b) < size:
                number = f"<too short for int of size {size}>"
            else:
                number = s.get_int((i, size))

            key = f"{b.hex()} {number}{unicode}"

            offset_values[i][key] = offset_values[i].get(key, 0) + 1

    # sort descending count
    for i in offset_values:
        offset_values[i] = {
            k: v
            for k, v in sorted(
                offset_values[i].items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
    with open("count_offset_values.json", "w") as f:
        json.dump(offset_values, f, indent="\t")
