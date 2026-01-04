""" Compares library binaries more intelligently than raw binary comparison using the section structure (though it does still assume children are always in the same order). """

import json
import sys

from library_musicdb import *


def diff(s1: Section | None, s2: Section | None, *, total_offset_1=0, total_offset_2=0) -> dict:
    if s1.__class__ != s2.__class__:
        return {
            "type_mismatch": [s1.__class__.__name__, s2.__class__.__name__]
        }  # does not make any sense to further compare contents or subsections

    # shouldn't both be None, if only one None then already caught
    assert s1 is not None and s2 is not None

    diff_dict = {}

    l1 = len(s1._data)
    l2 = len(s2._data)
    diff_start = -1
    in_diff = False
    diff_data_1 = bytearray()
    diff_data_2 = bytearray()
    for i in range(0, min(l1, l2)):
        if not in_diff:
            if s1._data[i] != s2._data[i]:
                in_diff = True
                diff_start = i
                diff_data_1 = bytearray([s1._data[i]])
                diff_data_2 = bytearray([s2._data[i]])
        else:
            if s1._data[i] != s2._data[i]:
                diff_data_1.append(s1._data[i])
                diff_data_2.append(s2._data[i])
            else:
                in_diff = False
                for name, offset in s1.offsets.items():
                    size = s1.offset_int_sizes[name]
                    if offset <= diff_start < offset + size:
                        if diff_start == offset:
                            diff_start_str = f"{name} ({diff_start})"
                        else:
                            diff_start_str = f"{name} + {diff_start - offset} ({diff_start})"
                        break
                else:
                    diff_start_str = f"{diff_start}"

                for name, offset in s1.offsets.items():
                    size = s1.offset_int_sizes[name]
                    if offset <= i < offset + size:
                        if i == offset:
                            diff_end_str = f"{name} ({i})"
                        else:
                            diff_end_str = f"{name} + {i - offset} ({i})"
                        break
                else:
                    diff_end_str = f"{i}"

                diff_dict[f"offsets {diff_start_str} to {diff_end_str}"] = [
                    diff_data_1.hex().upper(),
                    diff_data_2.hex().upper(),
                ]

    if l1 < l2:
        diff_dict[f"offsets {l1} to {l2}"] = [
            "<end of section>",
            diff_data_2.hex().upper(),
        ]
    elif l2 < l1:
        diff_dict[f"offsets {l2} to {l1}"] = [
            diff_data_1.hex().upper(),
            "<end of section>",
        ]

    total_offset_1 += s1.size
    total_offset_2 += s2.size

    # if all children have a subtype, use the subtype to match them up
    # if there's more than one of a subtype, match them up in the order encountered
    # otherwise just use order
    subsections1: list[tuple[int, int, Section]] = []
    subsections2: list[tuple[int, int, Section]] = []
    if all(
        "subtype" in s.offsets
        for s in s1.subsections
    ) and all(
        "subtype" in s.offsets
        for s in s1.subsections
    ):
        sub_total_offset_1 = total_offset_1
        for s in s1.subsections:
            subsections1.append(
                (
                    s.get_int("subtype"),
                    sub_total_offset_1,
                    s,
                )
            )
            sub_total_offset_1 += s.total_size
        subsections1 = sorted(subsections1, key=lambda t: t[0])

        sub_total_offset_2 = total_offset_2
        for s in s2.subsections:
            subsections2.append(
                (
                    s.get_int("subtype"),
                    sub_total_offset_2,
                    s,
                )
            )
            sub_total_offset_2 += s.total_size
        subsections2 = sorted(subsections2, key=lambda t: t[0])

        all_subtypes = sorted({s[0] for s in subsections1} | {s[0] for s in subsections2})
    else:
        sub_total_offset_1 = total_offset_1
        for s in s1.subsections:
            subsections1.append(
                (
                    -1,
                    sub_total_offset_1,
                    s,
                )
            )
            sub_total_offset_1 += s.total_size

        sub_total_offset_2 = total_offset_2
        for s in s2.subsections:
            subsections2.append(
                (
                    -1,
                    sub_total_offset_2,
                    s,
                )
            )
            sub_total_offset_2 += s.total_size

        all_subtypes = [-1]

    for subtype in all_subtypes:
        if subtype < 0:
            subtype_str = ""
        else:
            subtype_str = f"subtype {subtype} "

        iter1 = iter(subsections1)
        iter2 = iter(subsections2)

        count = 0

        sub_total_offset_1 = total_offset_1  # in case all None
        sub_total_offset_2 = total_offset_2
        while True:
            while True:
                try:
                    subtype1, sub_total_offset_1, subsection1 = next(iter1)
                except StopIteration:
                    subtype1 = subsection1 = None
                    break
                else:
                    if subtype1 == subtype:
                        break

            while True:
                try:
                    subtype2, sub_total_offset_2, subsection2 = next(iter2)
                except StopIteration:
                    subtype2 = subsection2 = None
                    break
                else:
                    if subtype2 == subtype:
                        break

            if subtype1 is None and subtype2 is None:
                break

            sub_d = diff(subsection1, subsection2, total_offset_1=sub_total_offset_1, total_offset_2=sub_total_offset_2)
            if any(sub_d.values()):
                diff_dict[f"child {subtype_str}#{count} ({sub_total_offset_1}/{sub_total_offset_2})"] = sub_d

            count += 1

    return {s1.__class__.__name__: diff_dict}


if __name__ == "__main__":
    if len(sys.argv) > 2:
        lib1 = Library(sys.argv[1])
        lib2 = Library(sys.argv[2])
    else:
        lib1 = Library(
            DEFAULT_LIBRARY_FILE.with_stem(
                input("library file 1: ")
            )
        )
        lib2 = Library(
            DEFAULT_LIBRARY_FILE.with_stem(
                input("library file 2: ")
            )
        )

    with open("diff.json", "w") as f:
        json.dump(diff(lib1, lib2), f, indent="\t")
