# Security policy

Report suspected vulnerabilities privately to **cagtay.fabry@bam.de**. Include
the package and Python versions, operating system, a minimal reproducer, and
the potential impact. Please avoid posting exploit details in a public issue
while a private report is being assessed.

The project is an initial alpha integration. Security fixes target the current
release/development line; older versions do not have a separate maintenance
commitment. Python 3.10 remains in compatibility testing as requested, despite
its upstream end of life; those tests do not extend Python's security support.

The package depends on an embedded QuickJS runtime and vendors Pele. Their
versions are pinned. Report integration issues here; the maintainer can coordinate
issues affecting upstream dependencies. The wrapper passes diagram source as
data and does not expose arbitrary JavaScript execution or fetch external images.
Pele's SVG security model and limitations still apply; consumers determine how
rendered SVG is displayed. See [Pele security documentation](https://pele.run/security).
