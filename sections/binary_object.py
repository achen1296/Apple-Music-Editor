from abc import ABCMeta
from typing import override

from zmq import IntEnum

from .section import Section


class StringEncoding(IntEnum):
    UTF_16_LE = 1
    UTF_8 = 2


class StringBase(Section, metaclass=ABCMeta):
    # abstract because no encoding, no "string" offset
    encoding = ""

    def get_string(self):
        return self._data[self.offsets["string"]:].decode(self.encoding)

    def set_string(self, value: str):
        self._edit()
        self._data[self.offsets["string"]:] = value.encode(self.encoding)
        # size will be taken care of in data property

    @override
    def update(self, d: dict[str | int | tuple[int, int], bytes | int | bool | str]):  # type: ignore the whole point is to change the type to allow a str value
        for k, v in d.items():
            if isinstance(v, str):
                if k != "string":
                    raise ValueError(f"the only key allowed for a string value is \"string\" (not {k})")

        if "string" in d:
            v = d["string"]
            if not isinstance(v, str):
                raise ValueError("key \"string\" must have a string value")
            self.set_string(v)
            del d["string"]

        super().update(d)  # type: ignore got rid of all string values

    @override
    @classmethod
    def from_scratch(cls, initial_values: dict[str | int | tuple[int, int], bytes | int | bool | str] = {}):  # type: ignore the whole point is to change the type to declare that a str value is allowed (no function changes)
        return super().from_scratch(initial_values)  # type: ignore update method overridden handle strings


class String(StringBase):
    size_start = 16
    offsets = {
        # **Section.offsets, # don't want "signature"
        "encoding": 0,
        "size": 4,
        "parent_subtype_counter": 8,
        "string": 16,
    }
    offset_int_enums = {
        "encoding": StringEncoding
    }
    default_values = {
        "size": 16,  # enough to get started in base from_scratch, then will immediately be overridden based on the string anyway
        "encoding": StringEncoding.UTF_16_LE,  # this is more common
    }

    def _set_encoding(self, encoding_int: int):
        if encoding_int == StringEncoding.UTF_8:
            self.encoding = "utf_8"
        elif encoding_int == StringEncoding.UTF_16_LE:
            self.encoding = "utf_16_le"
        else:
            raise ValueError(f"unexpected encoding for a string {encoding_int}")

    @override
    def __init__(self, *args, from_scratch=False, **kwargs):
        super().__init__(*args, from_scratch=from_scratch, **kwargs)

        if not from_scratch:
            self._set_encoding(self.get_int("encoding"))

    @override
    def update(self, d: dict[str | int | tuple[int, int], bytes | int | bool | str]):
        if not self.encoding:
            # for from_scratch need to make sure the encoding is set before the string
            self._set_encoding(
                d.get("encoding", self.default_values["encoding"])  # type: ignore
            )

        super().update(d)


class RawString(StringBase, metaclass=ABCMeta):  # abstract because no encoding
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "string": 0,
    }
    default_vales = {
        "size": 0,
    }


class RawStringUTF8(RawString):
    encoding = "utf_8"


class RawStringUTF16LE(RawString):
    encoding = "utf_16_le"


RawStringUTF16 = RawStringUTF16LE  # LE is by far more common


class RawStringUTF16BE(RawString):
    encoding = "utf_16_be"


class boma(Section):
    expected_signature = b"boma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subtype": 12,
    }
    default_values = {
        "size": 20
    }
    # subsection_class_by_subtype to be set in subclasses unique to each parent

    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = self.get_int("subtype")  # convenient to have this

    @override
    @classmethod
    def from_scratch(cls, initial_values: dict[str | int | tuple[int, int], bytes | int | bool | str] = {}):  # type: ignore the whole point is to change the type to declare that a str value is allowed for string children
        """ As a convenience, if `"subtype"` key is included, then will automatically attach an appropriate child with the `initial_values` not used by `boma` passed on (as none of them have a `"subtype"` themselves and all other keys are automatically handled). """
        initial_values_for_boma = {
            k: v
            for k, v in initial_values.items()
            if k in cls.offsets
        }
        b = super().from_scratch(initial_values_for_boma)  # type: ignore update method overridden handle strings
        if "subtype" in initial_values_for_boma:
            initial_values_for_child = {
                k: v
                for k, v in initial_values.items()
                if k not in cls.offsets
            }
            child_class = b.subsection_class_by_subtype[initial_values_for_boma["subtype"]]  # type: ignore
            b.add_child(
                child_class.from_scratch(initial_values_for_child)  # type: ignore
            )
        return b


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

        if isinstance(subsection.child, StringBase):
            return subsection.child.get_string()

        raise ValueError(f"subtype {subtype} is not supposed to be a string")

    def set_sub_string(self, subtype: str | int, value: str):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, StringBase):
            return subsection.child.set_string(value)

        raise ValueError(f"subtype {subtype} is not supposed to be a string")

    def get_sub_int(self, subtype: str | int, key: str | tuple[int, int]):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, StringBase):
            raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")

        return subsection.child.get_int(key)

    def set_sub_int(self, subtype: str | int, key: str | tuple[int, int], value: int):
        subsection = self.data_subsection_of_subtype(subtype)

        if isinstance(subsection.child, StringBase):
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
                if isinstance(subsection.child, StringBase):
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
