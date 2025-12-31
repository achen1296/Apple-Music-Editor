from collections import defaultdict
from enum import IntEnum
from io import BytesIO
from typing import Iterator, Type

from byte_util import (pack_int_into, pack_int_into_be, unpack_int,
                       unpack_int_be)
from date_util import datetime_to_int


class Section:
    """ When reading subsections:
    - if `subsection_class` is not `None`, attempts to load all subsections as this type
    - otherwise, attempts to use `subsection_class_by_subtype` and the value at the `"subtype"` offset (so that has to be given in `offsets`) to determine what class subsections (or more accurately, "the subsection" as so far all cases with a subtype only ever have one child) should be
    - if the subsection class cannot be determined or an exception occurs while trying to load it:
        - if the `total_size` offset is given, the generic `Section` class will be used as a last resort
        - otherwise we're out of luck and have no choice but to give up loading the rest of the file
    """

    expected_signature: bytes | None = None
    """ If not `None`, will be checked against the `"signature"` offset. """

    fixed_size: int | None = None
    """ While most sections are always the same size, this is intended to be used only for sections that do not have their size encoded in their data (on the off chance the size changes one day in the future, it would be better not to specify a fixed size). """
    size_start: int = 0
    """ Added to value of size offset, may be changed by subclass when size does not start from the beginning of the section. """
    total_size_start: int = 0
    """ Added to value of total size offset, may be changed by subclass when total size does not start from the beginning of the section. """

    subsection_class: Type["Section"] | None = None
    subsection_class_by_subtype: dict[int, Type["Section"]] = {}

    offsets: dict[str, int] = {
        "signature": 0,
        "size": 4,
        # not all kinds of section have these values, however these are common enough to include logic for them in the base class
        # "total_size"
        # "subsection_count"
        # "subtype"
        # "date_modified"
    }
    offset_int_sizes: defaultdict[str, int] = defaultdict(lambda: 4)
    """ Assume size 4 bytes if not specified (since that is the most common) """
    offset_int_enums: dict[str, Type[IntEnum]] = {}
    """ Indicate that an offset should use values from a specific `IntEnum`. Will show a warning (not an exception to leave the door open for future valid values that the code does not know) if this is not followed in `set_int`. This also improves readability of `__str__` output. """
    offset_aliases: set[str] = set()
    """ Added offset names to this set to prevent repeating the same offset in `as_dict`. """

    def __init__(self, data: BytesIO, size_hint: int | None = None):
        """ `size_hint` is only needed if there is neither a size offset nor a `fixed_size` class attribute given, and should come from the parent's `self.get_int("total_size") - self.get_int("size")` (this assumes there is only one child section). This is only supposed to be used for certain `boma` children which lack both a size offset and a fixed size, and as a last resort for unknown section types.

        (If a section type has neither a size offset nor a fixed size, but it does have some other way to determine its size from its own data, then the subclass should just extend `__init__`.) """

        self._edited = False
        self._changed_size = False
        self._updated_size_after_change = True
        self._subsection_count_changed = False

        start_offset = data.tell()

        # read this section
        if "size" in self.offsets:
            size_end_pos = self.offsets["size"] + self.offset_int_sizes["size"]
            self._data = bytearray(data.read(size_end_pos))
            read_end_pos = self.size_from_data + self.size_start
            self._data += data.read(read_end_pos - size_end_pos)
            assert self.size == read_end_pos  # make sure read() did not stop short
        elif self.fixed_size is not None:
            self._data = bytearray(data.read(self.fixed_size))
            assert self.size == self.fixed_size  # make sure read() did not stop short
        else:
            if size_hint is None:
                raise ValueError("size hint not provided when needed")
            self._data = bytearray(data.read(size_hint))
            assert self.size == size_hint  # make sure read() did not stop short

        if "signature" in self.offsets:
            self.signature = self._data[self.offsets["signature"]:self.offsets["signature"] + 4]
            if self.expected_signature is not None:
                assert self.signature == self.expected_signature
        else:
            self.signature = b""

        # read subsections -- only if there is either a total size or a subsection count in the data (sometimes both are present, doesn't matter which is used in that case for a valid file)
        self.subsections: list["Section"] = []

        if "total_size" in self.offsets:
            size_hint_for_child = self.total_size_from_data + self.total_size_start - self.size
        else:
            size_hint_for_child = None

        def append_subsection():
            nonlocal size_hint_for_child

            if not self.subsection_class:
                # don't need to figure out the subsection class until there actually is a subsection -- so leaf subsections may leave both subsection_class and subsection_class_by_subtype as the default values above without issue
                try:
                    self.subsection_class = self.subsection_class or self.subsection_class_by_subtype[self.get_int("subtype")]
                except KeyError:
                    if "subtype" in self.offsets:
                        message_prefix = f"couldn't figure out what kind of subsection {self.__class__.__name__} subtype {self.get_int("subtype")} should have"
                    else:
                        message_prefix = f"couldn't figure out what kind of subsection {self.__class__.__name__} should have"

                    if "total_size" in self.offsets:
                        print(f"warning: {message_prefix}, but can proceed with `Unknown` fallback type using parent's total size")
                        self.subsection_class = Unknown
                    else:
                        # todo try backing up to ancestors that *do* have a total size
                        raise ValueError(f"{message_prefix}, and total size is not provided to fall back on")

            self.subsections.append(
                self.subsection_class(data, size_hint=size_hint_for_child)
            )

        self.parent = self  # won't be reassigned if this is the root Section

        if "total_size" in self.offsets:
            # total size is preferred if both are available because it has a better chance of being able to proceed for unknown sections
            total_size = self.total_size_from_data + self.total_size_start
            while data.tell() < start_offset + total_size:
                append_subsection()
            assert data.tell() == start_offset + total_size
        elif "subsection_count" in self.offsets:
            for _ in range(0, self.subsection_count_from_data):
                append_subsection()

        for s in self.subsections:
            s.parent = self

    @property
    def size(self):
        if "size" in self.offsets:
            if not self._updated_size_after_change and self._changed_size:
                self.set_int("size", len(self._data) - self.size_start)
                # do not change back to self._changed_size = False because supersections might not have seen tha the size changed yet!
                # better to update the size multiple times redundantly than not to set it at all
                self._updated_size_after_change = True
        return len(self._data)

    @property
    def size_from_data(self):
        """ Use this one when loading! `size` will not be correct until this section is fully loaded! """
        return self.get_int("size")

    @property
    def total_size(self):
        """ Size of this section and all subsections, referred to as "associated sections length" on vollink """
        if "total_size" in self.offsets and any(s._changed_size or s._subsection_count_changed for s in self):
            total_size = sum(s.size for s in self)
            self.set_int("total_size", total_size - self.total_size_start)
            return total_size
        else:
            return sum(s.size for s in self)

    @property
    def total_size_from_data(self):
        """ Use this one when loading! `total_size` will not be correct until this section and all subsections are loaded! """
        if "total_size" not in self.offsets:
            raise ValueError(f"{self.__class__.__name__} section doesn't have a stored total size")
        return self.get_int("total_size")

    @property
    def subsection_count(self):
        """ Referred to as "how many sections follow" on vollink """
        if "subsection_count" in self.offsets and self._subsection_count_changed:
            self.set_int("subsection_count", len(self.subsections))
            self._subsection_count_changed = False
        return len(self.subsections)

    @property
    def subsection_count_from_data(self):
        """ Use this one when loading! `subsection_count` will not be correct until this section and all subsections are loaded! """
        if "subsection_count" not in self.offsets:
            raise ValueError(f"{self.__class__.__name__} section doesn't have a stored subsection count")
        return self.get_int("subsection_count")

    @property
    def children(self):
        """ Alias for subsections. """
        return self.subsections

    @property
    def subsection(self):
        """ Convenient alias for sections that are expected to have only one subsection. """
        return self.subsections[0]

    @property
    def child(self):
        """ Convenient alias for sections that are expected to have only one subsection. """
        return self.subsections[0]

    def _edit(self):
        self._edited = True

    def _edit_change_size(self):
        self._edited = True
        self._changed_size = True
        self._updated_size_after_change = False

    def _edit_change_subsection_count(self):
        self._edited = True
        self._subsection_count_changed = True

    @property
    def data(self):
        # this makes sure everything is updated when we go to write

        if "date_modified" in self.offsets and any(s._edited for s in self):
            self.set_int("date_modified", datetime_to_int())
            # do not change back to self._edited = False because supersections might not have seen yet

        # run the logic to update these in their property methods
        self.size
        self.total_size
        self.subsection_count

        return self._data

    def __iter__(self) -> Iterator["Section"]:
        """ Yield this section and all subsections (and subsubsections, etc., recursively) in the order they would appear in the file. To iterate over only direct subsections, just use `for subsection in section.subsections`. """
        yield self
        for s in self.subsections:
            yield from s

    def as_dict(self) -> dict:
        """ Summary dict of known data in this section (not any subsections). """
        return {
            offset_name: self.get_int(offset_name)
            for offset_name in self.offsets
            if offset_name not in self.offset_aliases
        }

    def __str__(self):
        return f"<{self.__class__.__name__} {self.as_dict()}>"

    def __repr__(self):
        return self.__str__()

    def tree(self):
        """ Return JSON-compatible object representing the tree structure (not any of the data) mainly for debugging. """
        if "subtype" in self.offsets:
            key = f"{self.__class__.__name__} (subtype {hex(self.get_int("subtype"))})"
        else:
            key = self.__class__.__name__
        return {
            key: [
                s.tree()
                for s in self.subsections
            ]
        }

    def set_bytes(self, offset: int | str, value: bytes):
        self._edit()
        if isinstance(offset, str):
            offset = self.offsets[offset]
        l = len(value)
        self._data[offset:offset+l] = value

    def get_bytes(self, offset: int | str, length: int):
        if isinstance(offset, str):
            offset = self.offsets[offset]
        return self._data[offset:offset + length]

    def set_int(
        self, key: str | tuple[int, int], value: int,
            *, _pack_int_into=pack_int_into,  # this argument is only for BigEndianSection subclass
    ):
        self._edit()
        if isinstance(key, str):
            if key in self.offset_int_enums:
                e = self.offset_int_enums[key]
                try:
                    # just check for the warning
                    e(value)
                except ValueError:
                    print(f"warning: when setting value {value} at offset named {key}, did not find a matching value in {e}")
            offset = self.offsets[key]
            size = self.offset_int_sizes[key]
        else:
            # assume the caller knows what they're doing, including not checking for IntEnum
            offset, size = key
        _pack_int_into(self._data, offset, value, size=size)

    def get_int(
            self, key: str | tuple[int, int],
            *, _unpack_int=unpack_int,  # this argument is only for BigEndianSection subclass
    ) -> int:
        e = None

        if isinstance(key, str):
            offset = self.offsets[key]
            size = self.offset_int_sizes[key]
            e = self.offset_int_enums.get(key, None)
        else:
            offset, size = key

        value: int = _unpack_int(self._data, offset, size=size)

        if e is not None:
            try:
                value = e(value)
            except ValueError:
                print(f"warning: when trying to interpret value at offset named {key} as {e} found unknown value {value} in the data instead")

        return value

    def set_boolean(self, key: str | int, value: bool):
        if isinstance(key, str):
            offset = self.offsets[key]
            assert self.offset_int_sizes[key] == 1, "size should be 1 for a boolean!"
        else:
            offset = key
        self.set_int((offset, 1), value)

    def get_boolean(self, key: str | int):
        if isinstance(key, str):
            offset = self.offsets[key]
            assert self.offset_int_sizes[key] == 1, "size should be 1 for a boolean!"
        else:
            offset = key
        return bool(self.get_int((offset, 1)))


class Unknown(Section):
    offsets = {}  # remove size offset to rely on the size_hint from parent


class BigEndianSection(Section):
    def set_int(self, *args, **kwargs):
        if "_pack_int_into" in kwargs:
            del kwargs["_pack_int_into"]
        super().set_int(*args, **kwargs, _pack_int_into=pack_int_into_be)

    def get_int(self, *args, **kwargs):
        if "_unpack_int" in kwargs:
            del kwargs["_unpack_int"]
        return super().get_int(*args, **kwargs, _unpack_int=unpack_int_be)
