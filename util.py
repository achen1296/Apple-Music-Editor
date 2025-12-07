import struct


def expect[T](actual: T, expected: T, message: str):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    if actual != expected:
        raise ValueError(f"{message} (expected: {expected}, actual: {actual})")


def expect_one_of[T](actual: T, expected_patterns: list[T | None], message: str):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    if any(actual == x for x in expected_patterns):
        return
    raise ValueError(f"{message} (expected: {expected_patterns}, actual: {actual})")


def unpack_one(fmt: str, b: bytes, offset:int):
    # copied from https://github.com/jsharkey13/musicdb-to-json
    # changes:
    # - used unpack_from instead
    #   - consequently adjusted all callers, which in any case were using byte slices
    #   - so this change saves making copies of the slices in memory
    #   - and also saves having to specify the size in the slice redundantly with the format
    return struct.unpack_from(fmt, b, offset)[0]
