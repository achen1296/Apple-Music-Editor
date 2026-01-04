import struct


def unpack(fmt: str, b: bytes, offset: int):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    # changes:
    # - used unpack_from instead
    #   - consequently adjusted all callers, which in any case were using byte slices
    #   - so this change saves making copies of the slices in memory
    #   - and also saves having to specify the size in the slice redundantly with the format
    return struct.unpack_from(fmt, b, offset)[0]


def pack_into(fmt: str, b: bytes, offset: int, value: int):
    struct.pack_into(fmt, b, offset, value)


INT_SIZE_FORMATS_LE = {
    1: "<B",
    2: "<H",
    4: "<I",
    8: "<Q",
}

INT_SIZE_FORMATS_BE = {
    1: ">B",
    2: ">H",
    4: ">I",
    8: ">Q",
}

# for this project, little-endian is far more common, so left the function names without _le


def unpack_int(b: bytes, offset: int, *, size: int = 4) -> int:
    return unpack(INT_SIZE_FORMATS_LE[size], b, offset)


def pack_int_into(b: bytearray, offset: int, value: int, *, size: int = 4):
    struct.pack_into(INT_SIZE_FORMATS_LE[size], b, offset, value)


def pack_int(value: int, *, size: int = 4):
    return struct.pack(INT_SIZE_FORMATS_LE[size], value)


def unpack_int_be(b: bytes, offset: int, *, size: int = 4) -> int:
    return unpack(INT_SIZE_FORMATS_BE[size], b, offset)


def pack_int_into_be(b: bytearray, offset: int, value: int, *, size: int = 4):
    struct.pack_into(INT_SIZE_FORMATS_BE[size], b, offset, value)


def pack_int_be(value: int, *, size: int = 4):
    return struct.pack(INT_SIZE_FORMATS_BE[size], value)


def show_control_chars(s: str):
    # for debugging
    return "".join(
        c
        # printable, tab, or newline (both kinds) pass through as-is
        if 0x20 <= ord(c) <= 0x7e or c in "\t\r\n"
        # for non-printables, replace with \x code
        else f"<{ord(c):02x}>"
        for c in s
    )
