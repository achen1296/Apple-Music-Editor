""" This script is used to dump the raw binary contents of different sections to the "section_binaries" directory to inspect them. """

import re

from library_musicdb import *
from library_search import LibrarySearcher

if __name__ == "__main__":
    write_subsections = True
    print_sections = True

    lib = Library()
    ls = (
        LibrarySearcher()
        # for example:
        .descendants_of_type(Track)
    )

    bins_dir = Path("section_binaries")
    bins_dir.mkdir(exist_ok=True)

    for i, s in enumerate(ls.search(lib)):
        if print_sections:
            print(s)

        # try to name the file something descriptive

        try:
            subtype = f" (subtype {hex(s.get_int("subtype"))})"
        except KeyError:
            subtype = ""

        name_data = ""
        if isinstance(s, DataContainerSection):
            try:
                name_data = f" {s.get_sub_string("name")}"
            except KeyError:
                pass

        # use the enumeration count to ensure a unique file name and indicate the order the sections appear in the file

        file_name = re.sub(
            r"[\\/:*?\"<>|\s]", # some characters not allowed in file names
            "_",
            f"{i} {s.__class__.__name__}{subtype}{name_data}"
        )

        with open(bins_dir/f"{file_name}.bin", "wb") as f:
            if not write_subsections:
                f.write(s._data)
            else:
                for s2 in s:
                    f.write(s2._data)
