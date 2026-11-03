# Research and scope

Primary sources checked on 2026-11-03:

| Source | Facts used |
| --- | --- |
| [RFC 9110 section 14.1](https://www.rfc-editor.org/rfc/rfc9110#section-14.1) | Range units are case-insensitive; the range mechanism is extensible. |
| [RFC 9110 section 14.1.2](https://www.rfc-editor.org/rfc/rfc9110#section-14.1.2) | Inclusive byte positions, closed/open/suffix ranges, clipping, and protocol satisfiability; a nonzero suffix remains satisfiable for an empty representation. |
| [RFC 9110 section 5.6.1](https://www.rfc-editor.org/rfc/rfc9110#section-5.6.1) | HTTP list syntax is broader than this tool's explicitly bounded nonempty-member profile. |
| [curl manual, --range](https://curl.se/docs/manpage.html#-r) | curl requests byte ranges and documents that server support varies. |

The initial candidate assumption that every range over a zero-length
representation was unsatisfiable was corrected from section 14.1.2 before
implementation. The implementation and independent oracle both separate
protocol satisfiability from the existence of covered bytes. No verbatim source
passage is reproduced here.

Design inference: an offline interval report can help a developer inspect overlap,
adjacency and EOF clipping using a known representation length. This is a proposed
workflow benefit, not measured adoption, saved time, speed, or security evidence.

Fair alternative: use curl when the question is whether a live server responds to
a range request, or when actual bytes need downloading. curl covers broader
transfer behavior and mature protocol machinery. This project has narrower scope:
deterministic arithmetic over a local JSON file, without network access. Neither
an offline result nor a merged interval union proves server policy or acceptance.

The grammar and caps are product decisions. Refusing empty list members and
whitespace variants does not claim those forms are universally invalid HTTP.
There is no GET/method, status, If-Range, multipart construction or resource-policy
validation here. The product has no networking, subprocess, server or SQLite code.

中文：依据为 RFC 9110 与 curl 官方文档。零长度表示的非零后缀例外在实现前核实并修正，
协议可满足不等于实际覆盖非空。离线规划的实用价值属于设计推断，无用户采用或节省时间的数据。
实际请求和服务器行为应选 curl 等传输工具验证；本项目只提供有限语法下的算术证据。
