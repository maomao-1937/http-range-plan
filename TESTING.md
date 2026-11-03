# Testing evidence

Run from the repository root:

```console
python -m unittest discover -s tests -v
```

Actual local result on 2026-11-03: **16 tests passed**, CPython 3.11.15,
Windows-10-10.0.26300-SP0. Final observed suite time: 1.169 seconds. Timing is an
observation of one local run, not a performance promise. Hosted CI is recorded
separately by the release controller; no hosted result is claimed here.

The initial pre-implementation run failed all 15 then-existing tests because the
implementation was missing. The first GREEN passed those 15. A subsequent focused
reserved-device alias regression failed five subcases on filesystem access, then
passed after basename normalization and CLOCK$ refusal were added. Final GREEN
passed all 16. Builder RED/GREEN logs are retained in the parent batch evidence,
outside the product repository.

The independent core oracle enumerates byte-position sets for lengths 0–6 and
all ordered pairs drawn from 53 closed/open/suffix forms: **19,663 cases**. It
checks protocol satisfiability separately from byte coverage, expected per-member
intervals, exact union coverage, ascending order and separation of merged
intervals. It imports the pure arithmetic core; it does not spawn 19,663 CLIs.

Additional checks cover empty representation/nonzero suffix, suffix zero, EOF
boundaries, clipping, adjacency, overlap, gaps, mixed satisfiability, large exact
integers, unit case, invalid whole-header rejection, operand/header/member limits,
duplicate/nonfinite/surrogate/UTF-8/BOM/shape/depth/node/byte refusals, and type bounds.

CLI processes use the script basename, repository cwd, and 15-second timeouts.
They verify examples with exits 0/1/2, neutral privacy-preserving errors, help and
usage. Two real OS pipes have their read ends closed before the product is
launched, covering both a normal report and `--help`; each exits 2, with empty
stderr and no shutdown exit 120. Synthetic files are read back unchanged with
unchanged modification time. Lexically forbidden paths are checked with stat/open
patched to fail if reached, including conservative punctuation/space and CLOCK$
refusals; this does not establish that every spelling is an actual Windows device.
There is no network or actual HTTP-server test, and no claim of server acceptance.

Manual source-invocation smoke checks actually run:

```console
python http_range_plan.py examples/mixed.json
python http_range_plan.py examples/empty-suffix.json
```

The first produced 5 members, 4 satisfiable, 1 unsatisfiable, 3 merged intervals,
and 16 covered bytes. The second produced a satisfiable member with null interval,
an empty union, and zero covered bytes. `checks.json` supplies five reproducible
controller checks using committed synthetic fixtures and help.

中文：上述为本地实际运行记录。独立预期以小范围字节集合枚举，不复用实现的区间算法。
测试覆盖协议可满足性和实际覆盖的区别、严格输入、路径访问前拒绝、只读与真实断管。
没有实际 HTTP 服务测试，不能据此声称服务器会接受该请求。
