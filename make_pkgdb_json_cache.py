#!/usr/bin/python -tt
# vim: fileencoding=utf8
# Copyright (c) 2014 Till Maas <opensource@till.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# }}}
""" :author: Till Maas
    :contact: opensource@till.name
    :license: MIT
"""

try:
    import simplejson as json
except ImportError:
    import json

import os
import sys
import tempfile

import pkgdb2client


def get_active_branches():
    pkgdb = pkgdb2client.PkgDB()

    branches = []
    for status in ["Active", "Under Development"]:
        for collection in pkgdb.get_collections(
                clt_status=status)["collections"]:
            branches.append(collection["branchname"])
    return branches


if __name__ == "__main__":
    pkgdb = pkgdb2client.PkgDB()
    states = ["Approved", "Retired", "Orphaned"]
    try:
        outdir = sys.argv[1]
    except IndexError:
        outdir = "./"

    for branch in get_active_branches():
        for status in states:
            result = pkgdb2client.PkgDB().get_packages(
                branches=branch, status=status, page="all")
            outfilename = "{}-{}.json".format(branch, status)
            outfile = tempfile.NamedTemporaryFile(
                dir=outdir, suffix=outfilename, delete=False)
            json.dump(result, outfile)
            outfile.close()
            os.rename(outfile.name, os.path.join(outdir, outfilename))
