"""Independent small-set oracle and real-process boundaries; no network."""
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'http_range_plan.py'
if SOURCE.exists():
    spec = importlib.util.spec_from_file_location('http_range_plan', SOURCE)
    product = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(product)
else:
    product = None


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(product, 'range planner implementation is missing')

    def test_exhaustive_independent_point_set_oracle(self):
        # Oracle enumerates positions; product must resolve/merge intervals.
        forms = [('closed', a, b) for a in range(8) for b in range(a, 8)]
        forms += [('open', a, None) for a in range(8)]
        forms += [('suffix', n, None) for n in range(9)]
        cases = 0
        for length in range(7):
            for left, right in itertools.product(forms, repeat=2):
                pieces, points, expected = [], set(), []
                for kind, a, b in (left, right):
                    if kind == 'closed':
                        pieces.append(f'{a}-{b}')
                        selected = {i for i in range(length) if a <= i <= b}
                        sat = a < length
                    elif kind == 'open':
                        pieces.append(f'{a}-')
                        selected = {i for i in range(length) if i >= a}
                        sat = a < length
                    else:
                        pieces.append(f'-{a}')
                        selected = {i for i in range(length) if i >= length - a} if a else set()
                        sat = a > 0
                    expected.append((sat, [min(selected), max(selected)] if selected else None))
                    points |= selected
                report = product.plan(length, 'bytes=' + ','.join(pieces))
                self.assertEqual([(m['satisfiable'], m['interval']) for m in report['members']], expected)
                self.assertEqual(report['covered_bytes'], len(points))
                actual = set()
                last = -2
                for a, b in report['merged_intervals']:
                    self.assertGreater(a, last + 1)
                    actual.update(range(a, b + 1))
                    last = b
                self.assertEqual(actual, points)
                self.assertEqual(report['satisfiable_count'], sum(s for s, _ in expected))
                cases += 1
        self.assertEqual(cases, 19663)

    def test_zero_length_suffix_protocol_satisfiable(self):
        result = product.plan(0, 'bytes=-1')
        self.assertEqual(result['members'], [{'ordinal': 1, 'satisfiable': True, 'interval': None}])
        self.assertEqual(result['covered_bytes'], 0)
        self.assertEqual(result['merged_intervals'], [])

    def test_merge_adjacency_overlap_and_gap(self):
        result = product.plan(20, 'ByTeS= 9-10,0-2,2-4,\t5-5,12-99,20- ')
        self.assertEqual(result['merged_intervals'], [[0, 5], [9, 10], [12, 19]])
        self.assertEqual(result['covered_bytes'], 16)
        self.assertEqual(result['unsatisfiable_count'], 1)

    def test_large_exact_integer_and_operands(self):
        n = 2**63 - 1
        report = product.plan(n, f'bytes={n-1}-99999999999999999999,-00000000000000000001')
        self.assertEqual(report['merged_intervals'], [[n-1, n-1]])
        self.assertEqual(report['covered_bytes'], 1)

    def test_reject_complete_malformed_header(self):
        for header in ('bytes=0-1,2-1', 'bytes=0-1,,2-3', 'bytes=0-1,', 'bytes=',
                       'bytes =0-1', 'bytes= 0 -1', 'bytes=0- 1', 'items=0-1',
                       'bytes=0-1\r\n', 'bytes=١-٢', 'bytes=+1-2', 'bytes=-',
                       'bytes=0-1,items=2-3', 'bytes=1-2-3', 'bytes=0-1\u00a0'):
            with self.subTest(header=header), self.assertRaises(product.InputError):
                product.plan(10, header)

    def test_header_and_member_and_operand_caps(self):
        self.assertEqual(product.plan(1, 'bytes=' + ','.join(['0-0']*1000))['member_count'], 1000)
        for header in ('bytes=' + ','.join(['0-0']*1001), 'bytes='+'0'*21+'-', 'bytes='+' '*65536+'0-1'):
            with self.assertRaises(product.InputError):
                product.plan(1, header)

    def test_length_type_bounds(self):
        for length in (True, False, -1, 2**63, 1.0, '1', None):
            with self.subTest(length=length), self.assertRaises(product.InputError):
                product.plan(length, 'bytes=0-1')

    def test_strict_json_rejections(self):
        payloads = [b'{"length":1,"length":2,"range":"bytes=0-0"}',
                    b'{"length":NaN,"range":"bytes=0-0"}',
                    b'{"length":Infinity,"range":"bytes=0-0"}',
                    b'{"length":1.0,"range":"bytes=0-0"}',
                    b'{"length":1,"range":"\\ud800"}',
                    b'{"length":1,"range":"bytes=0-0","\\udfff":0}',
                    b'\xef\xbb\xbf{}', b'\xff', b'[]', b'{}',
                    b'{"length":1,"range":"bytes=0-0","extra":0}',
                    b'{"length":'+b'1'*21+b',"range":"bytes=0-0"}',
                    b'['*34+b'0'+b']'*34,
                    b'['+b','.join([b'0']*10001)+b']', b' '* (2*1024*1024+1)]
        for payload in payloads:
            with self.subTest(payload_length=len(payload)), self.assertRaises(product.InputError):
                product.parse_input(payload)

    def test_json_integer_preserved(self):
        length, header = product.parse_input(b'{"length":9223372036854775807,"range":"bytes=-1"}')
        self.assertEqual(length, 9223372036854775807)
        self.assertIs(type(length), int)

    def test_lexical_rejection_precedes_file_access(self):
        paths = ['https://private.invalid/a', 'file:///secret', '//host/secret', '\\\\host\\secret',
                 '/\\host/x', '\\/host/x', '\\\\?\\C:\\secret', '\\\\.\\NUL',
                 'C:secret', 'a:stream', 'NUL.json', 'dir/CON.txt', 'dir/COM1',
                 'dir/LPT9.txt', 'CONIN$', 'dir/COM¹.txt', 'private\nname', '-']
        for path in paths:
            with self.subTest(path=path), patch.object(product.os, 'stat', side_effect=AssertionError('stat called')), \
                    patch.object(product.os, 'open', side_effect=AssertionError('open called')):
                with self.assertRaises(product.InputError):
                    product.read_local(path)

    def test_local_regular_read_only_and_directory_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'input.json'
            content = b'{"length":4,"range":"bytes=-2"}'
            file.write_bytes(content)
            before = file.stat().st_mtime_ns
            self.assertEqual(product.read_local(str(file)), content)
            self.assertEqual(file.read_bytes(), content)
            self.assertEqual(file.stat().st_mtime_ns, before)
            with self.assertRaises(product.InputError):
                product.read_local(folder)

    def test_reserved_alias_punctuation_before_extension_preaccess(self):
        for path in ('NUL .csv', 'CON .json', 'dir/COM1 .txt', 'CLOCK$',
                     'dir/CONIN$ .txt', 'dir/CONOUT$..txt'):
            with self.subTest(path=path), patch.object(product.os, 'stat', side_effect=AssertionError('stat called')), \
                    patch.object(product.os, 'open', side_effect=AssertionError('open called')):
                with self.assertRaises(product.InputError):
                    product.read_local(path)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.exists(), 'range planner implementation is missing')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, 'http_range_plan.py', *args], cwd=ROOT,
                              capture_output=True, timeout=15)

    def test_fixture_exit_codes_and_json(self):
        for name, code in [('mixed.json', 0), ('unsatisfiable.json', 1), ('empty-suffix.json', 0), ('invalid.json', 2)]:
            result = self.run_cli('examples/'+name)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(result.stderr, b'')
            report = json.loads(result.stdout)
            if code != 2:
                self.assertIn('covered_bytes', report)

    def test_neutral_errors_no_input_echo(self):
        secret = 'PRIVATE_SENTINEL_77'
        for args in [(secret,), ('--'+secret,), ('https://'+secret+'/x',)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(secret.encode(), result.stdout + result.stderr)
            self.assertNotIn(b'Traceback', result.stdout + result.stderr)

    def test_help_and_usage(self):
        self.assertEqual(self.run_cli('--help').returncode, 0)
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli('a', 'b').returncode, 2)

    def test_real_closed_stdout_including_help(self):
        for arg in ('examples/mixed.json', '--help'):
            reader, writer = os.pipe()
            os.close(reader)
            with os.fdopen(writer, 'wb') as sink:
                proc = subprocess.Popen([sys.executable, 'http_range_plan.py', arg], cwd=ROOT,
                                        stdout=sink, stderr=subprocess.PIPE)
                _, stderr = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(stderr, b'')


if __name__ == '__main__':
    unittest.main()
