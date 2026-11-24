# Security

This repository holds a vocabulary and the Python that checks and projects it: the checks under `tools/` and the
installable pipeline package `tools/itpra-onto`. It runs no service and handles no data. The checks run in CI and on
a contributor's machine; the package also runs wherever a consumer installs it, over the vocabulary and over the
consumer's own files.

If you find a problem that could affect consumers — for example a check or a build that can be made to run code or
read outside its inputs from a crafted file — report it privately through GitHub's security advisory feature for this
repository ("Report a vulnerability") rather than in a public issue. You will get an acknowledgement, and a fix lands
as an ordinary release.

Problems with the vocabulary itself (a wrong definition, a missing term) are not security matters: open an issue or a
pull request.
