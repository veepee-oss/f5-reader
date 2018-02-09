|PythonSupport|_ |License|_

f5reader - F5 Big-IP configuration reader
=========================================

| **Contact:** Denis 'jawa' Pompilio <dpompilio@vente-privee.com>
| **Sources:** https://git.vpgrp.io/core/f5-reader

Installation
------------

Install `f5reader` module from sources::

    python setup.py install

Usage
-----

Save F5 configuration as file using `f5-extractor.sh`::

    ./bin/f5-extractor.sh -l admin -c 1.1.1.1

From the command line::

    ~$ f5reader --help
    usage: f5reader [-h] [--version] [-c CFG_FILE] [--csv]

    F5 BigIP configuration reader

    optional arguments:
      -h, --help            show this help message and exit
      --version             show script version
      -c CFG_FILE, --config CFG_FILE
                            specify a configuration file to read
      --csv                 output virtual servers info as csv

License
-------

MIT LICENSE *(see LICENSE file)*

Miscellaneous
-------------

 ::

        ╚⊙ ⊙╝
      ╚═(███)═╝
     ╚═(███)═╝
    ╚═(███)═╝
     ╚═(███)═╝
     ╚═(███)═╝
      ╚═(███)═╝


.. |PythonSupport| image:: https://img.shields.io/badge/python-3.4,%203.5,%203.6-blue.svg
.. _PythonSupport: https://git.vpgrp.io/core/f5-reader
.. |License| image:: https://img.shields.io/badge/license-MIT-blue.svg
.. _License: https://git.vpgrp.io/core/f5-reader
