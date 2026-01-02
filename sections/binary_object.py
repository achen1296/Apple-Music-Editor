from abc import ABCMeta
from typing import Literal, override

from .section import Section


class String(Section):
    size_start = 16
    offsets = {
        **Section.offsets,
        "parent_subtype_counter": 8,
        "string": 16,
    }

    @override
    @classmethod
    def from_scratch(cls, initial_size: int, initial_values: dict[str | int | tuple[int, int], bytes | int | bool] = {}, initial_string: str = "", encoding: Literal["utf_16_le", "utf_8"] = "utf_16_le"):
        s = super().from_scratch(initial_size, initial_values)
        s.encoding = encoding
        if encoding == "utf_16_le":
            s.set_bytes("signature", b"\x01\x00\x00\x00")
        elif s.encoding == "utf_8":
            s.set_bytes("signature", b"\x02\x00\x00\x00")
        else:
            raise ValueError
        s.set_string(initial_string)
        return s

    @override
    def __init__(self, *args, from_scratch=False, **kwargs):
        super().__init__(*args, **kwargs)

        if not from_scratch:
            if self.signature == b"\x02\x00\x00\x00":
                self.encoding = "utf_8"
            elif self.signature == b"\x01\x00\x00\x00":
                self.encoding = "utf_16_le"
            else:
                raise ValueError(f"unexpected signature for a string {self.signature}, don't know what encoding to use")

    def get_string(self):
        return self._data[self.offsets["string"]:].decode(self.encoding)

    def set_string(self, value: str):
        self._edit()
        self._data[self.offsets["string"]:] = value.encode(self.encoding)
        # size will be taken care of in data property


class RawString(Section, metaclass=ABCMeta):  # abstract because no encoding
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "string": 0,
    }
    encoding = ""

    @override
    @classmethod
    def from_scratch(cls, initial_size: int, initial_values: dict[str | int | tuple[int, int], bytes | int | bool] = {}, initial_string: str = ""):
        s = super().from_scratch(initial_size, initial_values)
        s.set_string(initial_string)
        return s

    def get_string(self):
        return self._data.decode(self.encoding)

    def set_string(self, value: str):
        self._edit()
        self._data = value.encode(self.encoding)


class RawStringUTF8(RawString):
    encoding = "utf_8"


class RawStringUTF16LE(RawString):
    encoding = "utf_16_le"


RawStringUTF16 = RawStringUTF16LE  # LE is by far more common


class RawStringUTF16BE(RawString):
    encoding = "utf_16_be"


AnyString = String | RawString


class boma(Section):
    expected_signature = b"boma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subtype": 12,
    }
    # subsection_class_by_subtype to be set in subclasses unique to each parent

    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = self.get_int("subtype")  # convenient to have this


class BinaryObjectParentSection(Section):
    """ Add methods for boma subsections """

    data_subtypes: dict[str, int] = {}
    """ Used to assign a name to subtype numbers for readability purposes. """
    data_subtype_aliases: set[str] = set()
    """ Added data subtype names to this set to prevent repeating the same offset in `as_dict`. """

    def data_subsection_of_subtype(self, subtype: str | int):
        if isinstance(subtype, str):
            subtype = self.data_subtypes[subtype]
        for s in self.subsections:
            if isinstance(s, boma) and s.subtype == subtype:
                return s  # assumes there's only one subsection with the specified subtype
        raise KeyError(self, subtype)

    def get_sub_string(self, subtype: str | int):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, AnyString):
            return subsection.child.get_string()

        raise ValueError(f"subtype {subtype} is not supposed to be a string")

    def set_sub_string(self, subtype: str | int, value: str):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, AnyString):
            return subsection.child.set_string(value)

        raise ValueError(f"subtype {subtype} is not supposed to be a string")

    def get_sub_int(self, subtype: str | int, key: str | tuple[int, int]):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, AnyString):
            raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")

        return subsection.child.get_int(key)

    def set_sub_int(self, subtype: str | int, key: str | tuple[int, int], value: int):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, AnyString):
            raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")

        subsection.child.set_int(key, value)

    @override
    def as_dict(self):
        d = super().as_dict()
        for subtype_name in self.data_subtypes:
            if subtype_name in self.data_subtype_aliases:
                continue
            try:
                subsection = self.data_subsection_of_subtype(subtype_name)
            except KeyError:
                pass
            else:
                if isinstance(subsection.child, AnyString):
                    d[subtype_name] = subsection.child.get_string()
                else:
                    d[subtype_name] = subsection.child.as_dict()
        return d

# don't know where these boma subtypes go because they aren't in my library
# listed as "book" type on vollink: 0x42,
# "unknown 64x4b hex string": 0x1f4,
# another "unknown 64x4b hex string": 0x1fe,
# "xml block (unknown utility)": 0x2bc,
# "xml block (unknown utility)": 0x3cc,
