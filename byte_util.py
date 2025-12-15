import struct


def expect_one_of[T](actual: T, expected_patterns: list[T | None], message: str):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    if any(actual == x for x in expected_patterns):
        return
    raise ValueError(f"{message} (expected: {expected_patterns}, actual: {actual})")


def unpack_one(fmt: str, b: bytes, offset: int):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    # changes:
    # - used unpack_from instead
    #   - consequently adjusted all callers, which in any case were using byte slices
    #   - so this change saves making copies of the slices in memory
    #   - and also saves having to specify the size in the slice redundantly with the format
    return struct.unpack_from(fmt, b, offset)[0]


def unpack_int(b: bytes, offset: int) -> int:
    return unpack_one("<I", b, offset)


def pack_int_into(b: bytearray, offset: int, value: int):
    struct.pack_into("<I", b, offset, value)


def pack_int(value: int):
    return struct.pack("<I", value)
