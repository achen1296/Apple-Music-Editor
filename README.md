# Apple Music DB Editor

Editor for Apple Music's Library.musicdb file.

Based on and copying some code from:
- https://home.vollink.com/gary/playlister/musicdb.html
- https://github.com/rinsuki/musicdb2sqlite
- https://github.com/jsharkey13/musicdb-to-json
(see the comments in the code for where I am copying, everything else is mine)

However, unlike these, this project aims not only to read the Library.musicdb file, but also to be able to edit it. How can this be, when large parts of the file format remain a mystery? Simple:
- *start with a known valid file*
- make the desired edits
- change all of the lengths in the headers (which are part of the known format) as needed
- copy back all of the other data exactly as-is

This approach means we cannot *add* whole new entries to arrays, e.g. add a new song. (In the future I might try doing this by copying the mystery data from another entry of the same type.)

*Note that this code does not support the book subtype of boma sections, because, as mentioned below, my library doesn't have any I could test with, which makes me suspect they are no longer in use anyway.*

*In general, I just know it works on my own library file with the types of edits I wanted to do, so I can't give any guarantees about what it does to your library file. For this reason I've made it automatically make backups when you use the program to edit your library, unless you specifically turn them off.*

# Miscellaneous Observations

Keep in mind these observations are only based on my personal library file, which is the only one I have access to (although I do have 2 copies — one from now (December 2025), and one from 3 months ago (September), which have some significant differences as described below).

- Apple Music appears to use `zlib` compress level 1 (best speed) (experimentally verified by using `load_library` then `save_library` with no edits and seeing which one produces an identical file), but it also seems to accept any compression level (tried saving with different compression levels and opening Apple Music). (Not that there's any particular reason to use another compression level when Apple Music will resave the library itself the next time you open it.)
- On the other hand, it doesn't seem to like it when the size of the encrypted portion is changed — at least none of the sizes I tried was accepted. (Again, not that there's any reason to change this.)

## boma Sections

- When UTF-16 is mentioned below, it is always UTF-16LE, not BE, matching the convention for integers.
- Offset 16 is always 0
- Offset 20
    - *With the sole exception of one with the subtype number 0x1ff (big-endian), boma sections with 0x01000000 (i.e. 1 in 4 little-endian bytes) at offset 16 indicate there is a UTF-16 string at offset 36.*
        - Aside from the usually first 16 boma bytes, the 0x1ff section contains only the aforementioned 1 at offset 20, 2 copies of my library ID at offset 28, and then all 0s for the remainder of the section (which is 64 bytes long in total). (The library ID doesn't appear anywhere else except in the places already documented on vollink.)
    - *boma sections with 0x02000000 at offset 20 indicate that there is a UTF-8 string at offset 36*
    - Other than ipfa (>245k times) and the above (>62k times for 1, >8.2k (once for each track) times for 2), other common values (appearing more than once) for offset 20 included:
        - the beginning of XML strings (505 times)
        - SLst (165 times), 0x01010003 (161 times), 0x00010003 (only 3 times) — all of these contained mostly 0s and appeared near playlist data and each other
        - The beginning of a file path "C:" in UTF-16 (2 times — the 0x1FD and 0x200 boma sections mentioned below)
- New or different subtypes
    - My library file doesn't seem to have any book-type boma sections in my library (as of December 2025) -- even including 3 that have the numbers 0x1FC, 0x1FD, and 0x200 respectively (as they are listed on vollink as big-endian). I can only speculate that they have been retired due to being unnecessarily large. (Even more curiously, there are no boma sections with these subtype numbers (nor the remaining one mentioned as book-type on vollink, 0x42) in a copy of my library from 3 months ago (September 2025).) Instead, they are:
        - 0x1FC: the file location of the "iTunes Library.itl" file I imported in UTF-8 at offset 20
        - 0x1FD: the file location of the root folder of my music files in UTF-16 at offset 20
        - 0x200: the same as the previous
    - My file ends with a new, undocumented section type LPma, which is contained in its own hsma section. However, aside from its signature and size, it's all 0s. (This section is not present in the library from 3 months ago.)
    - New boma subtype number 0x0b000000, which appears to be the file location of each track in UTF-8 at 36 (including the 2 at offset 20)
    - 0x43 appears to also be the file location, but in UTF-16 at 36 (including the 1 at 20)
    - I indpendently discovered that the play count is contained in the boma subtype 0x17000000, before noticing that jsharkey13 also had this information
    - 0x190 and 0x191 artist names UTF-16 at 36