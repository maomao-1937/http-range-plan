# http-range-plan

[![tests](https://github.com/maomao-1937/http-range-plan/actions/workflows/tests.yml/badge.svg)](https://github.com/maomao-1937/http-range-plan/actions/workflows/tests.yml)

Resolve HTTP byte-range arithmetic before making a request. Give this small
offline CLI a representation length and one bounded `bytes` range value; get
per-member satisfiability, inclusive intervals, and a merged byte-coverage union.

## Run from source / 从源码运行

Requires Python 3.11 or newer. Standard library only; no installation, packages,
API keys, configuration files, or application environment variables are needed.
Download or clone this source, then run from its root:

```console
python http_range_plan.py examples/mixed.json
python http_range_plan.py examples/empty-suffix.json
python http_range_plan.py --help
```

On Windows, `py -3.11` may replace `python` if that is your Python launcher.
On Unix, your interpreter might be named `python3`. The input must be a named
local regular file; stdin (`-`) is unsupported. All committed examples are
synthetic. The application reads the supplied file and writes its report to
stdout. It never fetches a URL or writes a response body.

需要 Python 3.11+，只用标准库，无需安装依赖、配置文件、API 密钥或应用环境变量。
在项目根目录执行上述命令。输入是本地普通文件，不支持标准输入。示例均为合成数据。

## Input and supported grammar / 输入及语法

The entire UTF-8 JSON document must be an object with exactly two keys:

```json
{"length":20,"range":"bytes=0-2,2-5,9-10,12-99,20-"}
```

`length` is an integer from 0 through `9223372036854775807` (`2**63-1`). Boolean,
floating-point and exponent spellings are refused. Integers never pass through
binary floating-point. JSON BOMs, duplicate keys, nonfinite constants, malformed
UTF-8, and unpaired surrogate escapes are refused.

The range unit is ASCII case-insensitive: `bytes=`, `BYTES=`, and `ByTeS=` work.
Each member is `a-b`, `a-`, or `-n`, with ASCII decimal operands. Leading zeros
are allowed within the digit cap. Space and tab are allowed around whole
comma-separated members. There is no space around `=` or inside a member, and
no leading whitespace before `bytes`. Empty members, other units, and all
other syntax are refused with exit 2. This intentionally narrow profile also
refuses empty comma members that a tolerant HTTP list parser might ignore.
One malformed or unsupported member refuses the entire input; there is no
partial report that silently drops it.

For `a-b`, `a` must not exceed `b`. An end beyond EOF is clipped. For `a-`, the
end is `length-1`. A start at or beyond `length` is unsatisfiable. Suffix `-0`
is unsatisfiable; a positive suffix selects up to that many trailing bytes.

`length` 必须是指定范围内的 JSON 整数，布尔值、小数和指数形式均拒绝；不经过浮点转换。
仅支持大小写不敏感的 `bytes=`，以及 `a-b`、`a-`、`-n` 三种成员。
只允许成员两侧的空格和制表符，不允许空成员、等号两侧空白或连字符内部空白。
任一成员无效，整份输入退出 2，不输出部分成功结果。

## Output and exit codes / 输出及退出码

For the mixed example above, the compact JSON report contains:

```json
{"member_count":5,"satisfiable_count":4,"unsatisfiable_count":1,"members":[{"ordinal":1,"satisfiable":true,"interval":[0,2]},{"ordinal":2,"satisfiable":true,"interval":[2,5]},{"ordinal":3,"satisfiable":true,"interval":[9,10]},{"ordinal":4,"satisfiable":true,"interval":[12,19]},{"ordinal":5,"satisfiable":false,"interval":null}],"merged_intervals":[[0,5],[9,10],[12,19]],"covered_bytes":16}
```

Ordinals start at 1. Intervals include both endpoints. `merged_intervals` is
ascending and combines overlap and adjacency; `covered_bytes` counts each byte
only once. These numeric positions and counts are intended report evidence.
The report never echoes the raw range, header, file path, URL, or unknown JSON
keys. Errors use the fixed JSON object `{"error":"invalid_or_unsupported_input"}`;
no filename or parser snippet is included.

| Exit | Meaning |
| --- | --- |
| 0 | At least one protocol-satisfiable member; help also exits 0 |
| 1 | Every valid member is protocol-unsatisfiable |
| 2 | Malformed/unsupported input, exceeded limit, usage or I/O failure |

**Zero-length exception:** RFC 9110 section 14.1.2 explicitly treats a nonzero
suffix as protocol-satisfiable even for an empty representation. Therefore
`{"length":0,"range":"bytes=-1"}` exits 0, with `satisfiable:true`,
`interval:null`, `merged_intervals:[]`, and `covered_bytes:0`. Satisfiability and
nonempty byte coverage are separate facts. No `[0,-1]` interval is invented.

输出成员序号、协议可满足性、闭区间及合并后的唯一字节数，不回显原始 Range、路径或 URL。
退出 0 表示至少一个成员在协议定义上可满足；全不可满足退出 1；格式、范围、用法或 I/O
错误退出 2。特别地，长度为 0 时，非零后缀仍是协议可满足的，但实际覆盖为空，退出 0。

Closed stdout, including `--help`, exits 2 without a traceback or an interpreter
shutdown exit 120. Output can be truncated when its consumer closes the pipe.

## Fixed limits / 固定限制

| Item | Limit |
| --- | --- |
| Input file/read | 2 MiB (2,097,152 bytes) |
| JSON nesting | 32 simultaneously open object/array containers |
| Decoded JSON nodes | 10,000, counting root, keys, and values |
| JSON integer token | 20 decimal digits, excluding minus sign |
| Representation length | 0 through `2**63-1` |
| Range value | 65,536 ASCII characters (64 KiB) |
| Members | 1,000 |
| Each range operand | 20 ASCII decimal digits |

These are fixed refusal limits, not configurable runtime options. JSON container
depth is checked before recursive decoding. Node count is checked after decoding,
within the input byte cap. Large bounded operands are evaluated with exact Python
integers; the tool does not enumerate bytes or allocate a response body.

所有上限固定，不通过配置或环境变量修改；超限退出 2。JSON 在解码前检查容器深度，
解码后检查节点数。计算使用精确整数，不逐字节枚举、不分配响应正文。

## Local-file boundary and scope / 文件边界与用途

URI schemes, UNC paths (including mixed slash prefixes), Windows device paths,
drive-relative paths, alternate streams, control characters, and reserved device
components are rejected lexically before stat/open. Windows drive-absolute paths
are allowed. The conservative refusal profile also covers spaces/dots before
extensions and `CLOCK$`, without claiming every spelling is a proven OS device
alias. `CONIN$`, `CONOUT$`, and COM/LPT reserved components are refused. Directories and
special files are refused; the opened descriptor must also be regular. Reads are
bounded and read-only. Symlinks to regular files are allowed. A local-looking path
can be backed by a network mount, junction or symlink; this is not an isolation or
filesystem provenance guarantee. Another process can change a file during a read.

This is caller-supplied length arithmetic. It makes no network requests, starts no
subprocesses, and does not construct multipart responses. It does not check GET
usage, HTTP statuses, If-Range, validators, server acceptance/policy, actual resource
length, or amplification/security properties. Merging adjacent intervals is a
reporting choice, not a prediction of a server's multipart behavior.

读取前先按字符串拒绝 URI、UNC、设备路径、保留设备名等；只读普通文件并限制读取长度。
本地路径可能经挂载、链接指向其他存储，因此不保证底层存储位置。工具只计算用户提供的长度，
不发送网络请求、不启动子进程、不生成分段响应，也不证明服务器会接受 Range 或具有安全性。

## Verification / 验证

```console
python -m unittest discover -s tests -v
```

Locally verified on CPython 3.11.15, Windows 10 build 26300, on 2026-11-03.
The suite includes 19,663 independent point-set oracle cases, real CLI exit codes,
strict-input refusals, path rejection before access, read-only checks, and real
closed OS pipes. See [TESTING.md](TESTING.md) for the recorded scope and
[RESEARCH.md](RESEARCH.md) for primary sources and a fair curl alternative.
Other Python/OS combinations require their own execution evidence.

本地实际验证环境为 CPython 3.11.15 / Windows 10 build 26300。
测试包含 19,663 个独立集合枚举预期、真实 CLI、只读和断管检查。其他环境需另行运行验证。

MIT License, copyright 2026 maomao-1937.
