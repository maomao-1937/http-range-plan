#!/usr/bin/env python3
"""Bounded, offline HTTP byte-range interval arithmetic (Python 3.11+)."""
import json
import os
import re
import stat
import sys

MAX_BYTES = 2 * 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 10000
MAX_HEADER = 65536
MAX_MEMBERS = 1000
MAX_DIGITS = 20
MAX_LENGTH = 2**63 - 1
MEMBER = re.compile(r'(?:([0-9]{1,20})-([0-9]{1,20})?|-([0-9]{1,20}))', re.ASCII)
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', 'CLOCK$', 'CONIN$', 'CONOUT$'} | {
    prefix + digit for prefix in ('COM', 'LPT') for digit in '123456789¹²³'
}
HELP = ('Usage: python http_range_plan.py INPUT\n'
        'Read one local UTF-8 JSON file with length and range fields.\n'
        'Exit: 0 any protocol-satisfiable member; 1 none; 2 invalid/unsupported/I/O.\n'
        'See README.md for the bounded bytes grammar and limits.\n')


class InputError(ValueError):
    """Neutral input refusal; never carries user-supplied text."""


def _reject(*_args):
    raise InputError()


def _integer(token):
    if len(token.lstrip('-')) > MAX_DIGITS:
        raise InputError()
    return int(token)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError()
        result[key] = value
    return result


def _check_depth(text):
    # Before recursive json decoding: braces inside strings are not structure.
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > MAX_DEPTH:
                raise InputError()
        elif char in ']}':
            depth -= 1


def parse_input(data):
    """Strict bounded JSON; preserve integer arithmetic without a float stage."""
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise InputError()
    try:
        text = data.decode('utf-8', errors='strict')
        _check_depth(text)
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                           parse_float=_reject, parse_constant=_reject)
    except (ValueError, UnicodeError, RecursionError):
        raise InputError() from None
    stack = [value]
    count = 0
    while stack:
        item = stack.pop()
        count += 1
        if count > MAX_NODES:
            raise InputError()
        if isinstance(item, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in item):
            raise InputError()
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    if type(value) is not dict or set(value) != {'length', 'range'}:
        raise InputError()
    length, header = value['length'], value['range']
    _validate_types(length, header)
    return length, header


def _validate_types(length, header):
    if type(length) is not int or not 0 <= length <= MAX_LENGTH or type(header) is not str:
        raise InputError()


def plan(length, header):
    """Resolve all members atomically and union nonempty inclusive intervals."""
    _validate_types(length, header)
    if len(header) > MAX_HEADER or header[:6].lower() != 'bytes=' or not header.isascii():
        raise InputError()
    pieces = header[6:].split(',')
    if len(pieces) > MAX_MEMBERS:
        raise InputError()
    members, intervals = [], []
    for ordinal, piece in enumerate(pieces, 1):
        match = MEMBER.fullmatch(piece.strip(' \t'))
        if match is None:
            raise InputError()
        first, last, suffix = match.groups()
        interval = None
        if suffix is not None:
            size = int(suffix)
            satisfiable = size > 0
            if satisfiable and length:
                interval = [max(0, length - size), length - 1]
        else:
            start = int(first)
            end = int(last) if last is not None else length - 1
            if last is not None and start > end:
                raise InputError()
            satisfiable = start < length
            if satisfiable:
                interval = [start, min(end, length - 1)]
        members.append({'ordinal': ordinal, 'satisfiable': satisfiable, 'interval': interval})
        if interval is not None:
            intervals.append(interval)
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    satisfiable_count = sum(item['satisfiable'] for item in members)
    return {'member_count': len(members), 'satisfiable_count': satisfiable_count,
            'unsatisfiable_count': len(members) - satisfiable_count, 'members': members,
            'merged_intervals': merged, 'covered_bytes': sum(b - a + 1 for a, b in merged)}


def _validate_path(path):
    if not isinstance(path, str) or not path or path == '-' or any(
            ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in path):
        raise InputError()
    # Reject UNC, mixed slash network prefixes, device namespaces, URI schemes,
    # drive-relative paths, alternate streams, and Windows reserved components
    # lexically on every platform, before any filesystem call.
    if len(path) >= 2 and path[0] in '/\\' and path[1] in '/\\':
        raise InputError()
    tail = path
    if re.match(r'^[A-Za-z]:[/\\]', path):
        tail = path[2:]
    if ':' in tail:
        raise InputError()
    for component in re.split(r'[/\\]', tail):
        base = component.rstrip(' .').split('.', 1)[0].rstrip(' .').upper()
        if base in RESERVED:
            raise InputError()


def read_local(path):
    """Read only a named regular file, with an independent descriptor check."""
    _validate_path(path)
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        raise InputError()
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise InputError()
        with os.fdopen(fd, 'rb', closefd=False) as source:
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise InputError()
        return data
    finally:
        os.close(fd)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ['--help'] or args == ['-h']:
            output, code = HELP, 0
        else:
            if len(args) != 1 or args[0].startswith('-'):
                raise InputError()
            length, header = parse_input(read_local(args[0]))
            report = plan(length, header)
            output = json.dumps(report, separators=(',', ':'), ensure_ascii=True) + '\n'
            code = 0 if report['satisfiable_count'] else 1
    except (InputError, OSError, ValueError, RecursionError):
        output, code = '{"error":"invalid_or_unsupported_input"}\n', 2
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except (OSError, ValueError):
        # Immediate exit avoids a second failing interpreter shutdown flush (120).
        os._exit(2)
    return code


if __name__ == '__main__':
    sys.exit(main())
