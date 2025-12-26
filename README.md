# Apple Music DB Editor

Editor for Apple Music's Library.musicdb file.

Based on and copying some code from:

- https://home.vollink.com/gary/playlister/musicdb.html
- https://github.com/rinsuki/musicdb2sqlite
- https://github.com/jsharkey13/musicdb-to-json
  (see the comments in the code for where I am copying, everything else is mine)

However, unlike these, this project aims not only to read the Library.musicdb file, but also to be able to edit it. How can this be, when large parts of the file format remain a mystery? Simple:

- _start with a known valid file_
- make the desired edits
- change all of the lengths/counts in the headers (which are part of the known format) as needed
- copy back all of the other data exactly as-is

This approach means we cannot _add_ whole new entries to arrays, e.g. add a new song. (In the future I might try doing this by copying the mystery data from another entry of the same type.)

_Note that this code does not support the book subtype of boma sections, because, as mentioned below, my library doesn't have any I could test with, which makes me suspect they are no longer in use anyway._

_In general, I just know it works on my own library file with the types of edits I wanted to do, so I can't give any guarantees about what it does to your library file. For this reason I've made it automatically make backups when you use the program to edit your library, unless you specifically turn them off._

# Observations

Keep in mind these are only based on my personal library file (although I do have 2 copies — one from now (December 2025), and one from 3 months ago (September), which have some significant differences as described below).

There are quite a few places where I independently discovered something and then realized that jsharkey13 had also already done so. But I did come up with some genuine new information.

- Apple Music appears to use `zlib` compress level 1 (best speed) (experimentally verified by using `load_library` then `save_library` with no edits and seeing which one produces an identical file), but it also seems to accept any compression level (tried saving with different compression levels and opening Apple Music). (Not that there's any particular reason to use another compression level when Apple Music will resave the library itself the next time you open it.)
- On the other hand, it doesn't seem to like it when the size of the encrypted portion is changed — at least none of the sizes I tried was accepted. (Again, not that there's any reason to change this.)
- My file ends with a new, undocumented section type LPma, which is contained in its own hsma section (which has "section subtype" 0x11). However, aside from its signature and size, it's all 0s. (This section is not present in the library from 3 months ago.)

## List Sections (start with l) and hsma

- Seem to be completely described on vollink, all other data is all 0s (why the 0s are there is not clear other than perhaps reserved space, this is true throughout the format)
- not plma

## hfma

- My musicdb file type (outer hfma offset 56) is 7, not one of the known ones
- The inner and outer ones differ at offset 64 (4 bytes), neither being 0, so this seems to have some meaning (both both have 0x14 at 60)
- offset 92 "Apple store ID" is 0 if not signed in

## plma

- offset 104: found repeated 178 times in each of:
  - offset 244 of itma
  - offset 220 of 0x1 boma
  - offset 300 of 0x1 boma
- there is more unknown data but it's nigh impossible to make anything of it because it's all isolated 1 bits in a sea of 0s

## iama (Albums)

- Many offsets are 0 much (sometimes nearly all) of the time, but some unique value for each one the rest of the time
- offset 24: either 0x02000001 or 0x02010001, the former is more common; possibly this is a set of 4 single-byte flags
- offset 28 always 1
- offset 32, 8 bytes: ID of the first track in the album (my guess is that this is to speed up retrieving information like the artwork that the iama doesn't store directly) but sometimes 0
- offset 40, 2 bytes: just documenting that it's probably not 4 bytes since offset 42, 2 bytes always 0, too short for searching for the values to be of any use
- offset 64, 8 bytes: repeat of offset 16 but sometimes 0 (seems to be 0 for newer songs? maybe after iTunes transition?)
- offset 100, 4 bytes: most recent last played date of any song in the album (0 for never?)
- offset 104: nearly always 0, but when not 0 found duplicated at offset 180 of a 0x1 boma and nowhere else
- offset 120: nearly always 0, but when not 0 found duplicated at offset 120 of an iAma and nowhere else

## iAma (Artists)

- Many offsets are 0 much (sometimes nearly all) of the time, but some unique value for each one the rest of the time
- offset 24, 28 not zero but always 2, 1 respectively
- offset 52, 4 bytes: ID of the artist in the Apple Music store. Convert to integer and plug it into the URL "https://music.apple.com/us/artist/\<ID\>", for example 0x6c0c0700 (little endian) -> 461932 -> "https://music.apple.com/us/artist/461932" (the band Europe). 0 for artists that are not on the store, i.e. custom artist names on audio files you didn't buy from Apple Music (this was the clue I needed to figure this out).
  - searching through the file revealed these IDs repeating at offset 188 of 0x1 boma sections!
- offset 64, 16 bytes: almost always 0, but when not 0 it's the artwork UUID (see itma offset 256) — specifically the ones where, in the sqlite table artwork_source, the value of the column location_type is 2, and that seems to indicate a remote image because the value of location is in this case always something like "https://is1-ssl.mzstatic.com/image/thumb/Music\<number\>/v4/\<several path components with a UUID\>/\<some image name\>".
- offset 80, 8 bytes: repeat of offset 16 but sometimes 0
- offset 120: see iama offset 120
- some more unknown isolated bits

## itma (Tracks)

- offset 8, 4-byte ints, in the approximate range 1000-3000
  - actually 2 bytes would be enough for all of these
  - this offset's data changes when the equalizer is changed from "none" to something else, but it doesn't matter which equalizer is chosen
  - however, the pair of values isn't consistent between tracks
  - Wild guess: Maybe an average volume? Something to do with volume would at least explain why it changes with equalizer
- offset 24, 4-byte ints, ascending even numbers starting from 1002 — completely consistent
- Many offsets are 0 much (sometimes nearly all) of the time, but some unique value for each one the rest of the time
- offset 52, 1 byte: is the checkbox for "use work & movement" (0 = unchecked, 1 = checked), keeps the associated information regardless of whether this is checked, only affects whether it's displayed or not
- offset 51, 1 byte: checkbox for "show composer in all views"
- offset 188, 4 bytes: Apple Store ID of the artist (see iAma)
- offset 256, 16 bytes: 0s if no artwork, otherwise the UUID of the artwork used as a primary key in the artwork.sqlite file accompanying Library.musicdb
  - whichever one is the "default" if there's more than one attached
  - the way the ID is formatted in text as XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX in artwork.sqlite suggests to me it is a UUID
  - artwork.sqlite file seems to be used to map tracks to their artwork, and from artwork to cache files in the artwork folder
- offset 96, 4 bytes: almost always 0, but when it's not 0, the value is not unique, so if it's an ID it's not for the track itself, however the value is not repeated anywhere else except other itma's
- offset 116, 4? bytes: a number that is <100, maybe some kind of count
- offset 220, 8 bytes: almost always 0, but when not 0, repeated at 320, and at 348 in 0x1 boma, and many of the values in different itma sections in in sequences with each other, e.g. I had most of the values between 550078139443950 and 550078139443980 (decimal) close together
- offset 244, 4 bytes: almost always 0, but otherwise see plma 104
- offset 256, 16 bytes: rarely 0, otherwise the same value is shared by dozens or even hundreds of itma's and occasionally is repeated at 263 of lpma
- offset 280-308: all dense bits
- offset 320, 8 bytes: see 220
- offset 336, 4 bytes: almost always 0, but one value appears 242 times, then many other values appear 3 times or less
- some more unknown isolated bits

## lpma

- built-in playlists:
  - "####!####"
  - "Music"
  - "Music Videos"
  - "TV & Movies"
  - "Downloaded" (songs purchased from Apple Music that are downloaded locally)
- offset 26, 1 byte: changes from 4b to 3c when an artwork is added the first time, when suggestion flag (favorite/suggest less, as it is called by jsharkey13) is changed the first time, but not sure what the value means
- offset 50: playlist ID of parent playlist folder, which is implemented as a special playlist
- offset 263, 16 bytes: UUID of the artwork for the playlist, see itma
  - (the modification date at 138 makes sense)
- offset 223, 1 byte — favorite/suggest less, 0 = default, 2 = favorite, 3 = suggest less, 1 = undo suggest less (and also undo favorite) (same values as for itma offset 62 as found by jsharkey13)
- offset 324, 4 bytes — date suggestion flag was last changed (0 for never)
- changing view options updates the modification date for a playlist, but the changes are saved in .plist files in the preferences folder
- a lot of mysteries here...

## boma

- When UTF-16 is mentioned below, it is always UTF-16LE, not BE, matching the convention for integers.
- Offset 16 is always 0
- Offset 20
  - _With the sole exception of one with the subtype number 0x1ff (big-endian), boma sections with 0x01000000 (i.e. 1 in 4 little-endian bytes) at offset 16 indicate there is a UTF-16 string at offset 36._
    - Aside from the usually first 16 boma bytes, the 0x1ff section contains only the aforementioned 1 at offset 20, 2 copies of my library ID at offset 28, and then all 0s for the remainder of the section (which is 64 bytes long in total). (The library ID doesn't appear anywhere else except in the places already documented on vollink.)
      - update (2025-12-23): now there is only one copy of the library ID...
  - _boma sections with 0x02000000 at offset 20 indicate that there is a UTF-8 string at offset 36_
  - Other than ipfa (>245k times) and the above (>62k times for 1, >8.2k (once for each track) times for 2), other common values (appearing more than once) for offset 20 included:
    - the beginning of XML strings (505 times)
    - "SLst" (165 times), 0x01010003 (161 times), 0x00010003 (only 3 times) — all of these contained mostly 0s and appeared near playlist data and each other
    - The beginning of a file path "C:" in UTF-16 (2 times — the 0x1FD and 0x200 boma sections mentioned below)
- New or different subtypes
  - My library file doesn't seem to have any book-type boma sections in my library (as of December 2025) -- even including 3 that have the numbers 0x1FC, 0x1FD, and 0x200 respectively (as they are listed on vollink as big-endian). I can only speculate that they have been retired due to being unnecessarily large. (Even more curiously, there are no boma sections with these subtype numbers (nor the remaining one mentioned as book-type on vollink, 0x42) in a copy of my library from 3 months ago (September 2025).) Instead, they are:
    - 0x1FC: the file location of the "iTunes Library.itl" file I imported in UTF-8 at offset 20
    - 0x1FD: the file location of the root folder of my music files in UTF-16 at offset 20
    - 0x200: the same as the previous
  - New boma subtype number 0x0b000000, which appears to be the file location of each track in UTF-8 at 36 _and URL-encoded_ ("file://localhost/C:/...", spaces replaced with "%20", etc.)
  - 0x43 appears to also be the file location, but in UTF-16 at 36 (not URL-encoded)
  - 0x190 and 0x191 artist names UTF-16 at 36
- 0x1: track numerics
  - offset 20, 2 bytes: another counter ascending by 2 starting from 1003
  - offset 28, 8 bytes: an ID, doesn't appear anywhere else
  - offset 80, 4 bytes or maybe 8 bytes: some values shared by thousands of tracks, but don't appear anywhere else
  - offset 96, 2 bytes: number of artworks
  - offset 104, 4 bytes: total file size of all artworks in bytes
  - offset 144, 4 bytes: 0 if no custom lyrics, otherwise seems to be some kind of tiny hash because having the same lyrics always produces the same result. However, the actual lyrics are only stored embedded in the audio file.
  - isolated unknown bits
- 0x7: equalizer
  - listed as "not sure" on vollink, but a new section with this subtype appears when I change the equalizer of a song from "none" to something else
  - always a UTF-16 string that looks like "#!#\<number\>#!#" where the number is different for each equalizer option
- 0x17: plays and skips
  - offset 20: track ID repeated
- 0xca: smart playlist
  - _seeing this data change with a smart playlist setting confirms that 0xca boma subtype also has something to do with smart playlists, which was only known for 0xc9 before_ (even more strongly than the fact that it only appears under them)
  - offset 20, 1 byte: live updating checkbox (0 = false, 1 = true)
  - offset 21, 1 byte: checkbox to enable matching rules (related data is still stored even when disabled)
    - GUI enforces that one must have either this or the limit (offset 22) enabled
  - "limit to \<count\> \<units\> selected by \<method\>"
    - offset 22, 1 byte: checkbox to enable the limit (related data is still stored even when disabled)
    - offset 23, 1 byte: units
      - 0x03 = items
      - 0x01 = minutes
      - 0x04 = hours
      - 0x02 = megabytes
      - 0x05 = gigabytes
    - offset 24, 1 byte: selection method
      - 0x02 = random
      - 0x06 = album
      - 0x07 = artist
      - 0x09 = genre
      - 0x05 = title
      - 0x1c = highest rating
      - 0x1a = most recently played
      - 0x19 = most often played
      - 0x15 = most recently added
      - offset 33, 1 byte: reverse flag — when set to 0x01 instead of 0x00:
        - highest rating becomes lowest rating
        - most → least
        - always 0x00 for the other values of offset 24 (but I wonder if they could be reversed too by setting this bit)
    - offset 28, 4 bytes: count
  - offset 32: match only checked items checkbox (note: to be able to toggle this in the GUI, must have "Settings" → "General" → "Show" → "Song list checkboxes" checked; the checkboxes this refers to can be seen by changing "View as" to "Songs" (not in any other view))
- 0xc9: also smart playlist
  - playlist folders are a special kind of smart playlist — I haven't fully investigated the details, but I manually constructed a smart playlist with the rules "match any of the following" with "playlist is"... entries with the playlists in the folder, and the binary was extremely similar
  - starting at offset 20, contains "SLst" subsections
    - _AHA! This is why boma sections always have 0x14 00 00 00 at offset 4! This is in fact the "section length" of boma, and offset 8 is the "associated sections length" — therefore boma is not actually an unusual special case as all previous investigators have believed, but in fact following the usual pattern exactly! Even the subtype value matches the hsma sections, which also have a subtype at offset 12 that give a hint about what's inside! Instead, it is the sections_ inside _of the boma sections that often break the patterns:_
      - by often having a signature that is not made of ASCII characters only, e.g. the observation about the string encoding — 0x01000000 is the signature for UTF-16 string sections, and 0x02000000 is the signature for UTF-8 string sections
      - by having the length at offset 4 represent something other than the entire section length, e.g. the strings again where what we thought was offset 24 of the boma (offset 4 of the string section) is the length of the string that starts at offset 36 of the boma (offset 16 of the string section)
      - by being straight-up data without a signature or section length, e.g. some XML strings
      - basically, they are all unique, which is why everyone though the boma sections broke the patterns
      - this is probably also why those counter values started at >1000 — to avoid colliding with strings and other potential future signatures
    - offsets below are given relative to the start of the SLst section
    - offset 4 is _not_ the length of the SLst section (for example, often have 0x00010001 which is 16777472 in little-endian, this looks like some bit flags instead)
    - offset 11, 4 bytes: number of rules contained (are these subsections too?), possibly including other SLst sections (for playlist folders: number of children — presumably each is a rule "playlist is..." under a "match _any_ of the following" (todo: verify))
    - offset 15, 1 byte: "match ... of the following rules"
      - 0x00 = all
      - 0x01 = any
    - offset 72?: rules — all offsets below are given as relative to the start of a single rule
      - text match:
        - offset 0, 4 bytes: field
          - 0x03 = album
          - 0x47 = album artist
          - ...
        - offset 4, 1 byte: comparison method
          - 0x01000002 = contains
          - 0x03000002 = does not contain
          - 0x01000001 = is (exact full match)
          - 0x03000001 = is not
          - 0x01000004 = begins with
          - 0x01000008 = ends with
          - looks like first byte 01 is positive, 03 is negative, and each kind of comparison is a bit flag at the end (which makes me wonder if e.g. 0x03000004 "does not begin with" would work even if not presented as an option in the GUI)
        - offset 55, 2 bytes: the length of the text in bytes
        - offset 57: the text in UTF-16
    - seems like it would be trivial to change the rules and see what changed in the file to learn the rest of them, as I did for the above, so I haven't bothered to do that yet
- 0xce: ipfa
  - smart playlists (including playlist folders) redundantly contain all boma ipfa entries for all the songs they contain, so this doesn't have to be recalculated ever time (I wonder what would happen if this cache and the actual ones that match the rules disagree?); the track ID is the same for the same track, but the ipfa ID (and the "short number varies" at offset 28) is not


## Direct Contents of MP3 Files

- Uses [ID3 tags](https://id3.org/id3v2.3.0)
- id3 tag version is read out of the MP3 file's ID3 header
- lyrics
