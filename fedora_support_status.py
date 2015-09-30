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
    import pkgdb2client
except ImportError:
    pkgdb2client = None

try:
    import requests
except ImportError:
    requests = None
    import pycurl
    from StringIO import StringIO
    import simplejson as json

import yum


PKGDB_ORPHANED = "Orphaned"
PKGDB_RETIRED = "Retired"
PKGDB_APPROVED = "Approved"

COMMON_STATES = {PKGDB_ORPHANED: "Unmaintained", PKGDB_RETIRED: "Removed"}

RAWHIDE_VERSION = 24
NEWEST_EPEL = 7

LEGACY_EPEL_BRANCHES = {5: "el5", 6: "el6", }
PKGDB_CACHE_URL = "https://till.fedorapeople.org/pkgdbcache/"


def get_os_info():
    info = {}
    try:
        osrelease = open("/etc/os-release").read()
        for line in osrelease.splitlines():
            key, value = line.split("=", 1)
            value = value.strip('"')
            info[key] = value

    except IOError:
        info = {}

    return info


def get_pkgdb_packages(status=PKGDB_ORPHANED, branches="master",
                       use_cache=True):
    if use_cache is True:
        # cachefile = "{}-{}.json".format(branches, status)
        cachefile = "%s-%s.json" % (branches, status)
        cacheurl = PKGDB_CACHE_URL + cachefile
        if requests is None:
            resp = StringIO()
            c = pycurl.Curl()
            c.setopt(c.URL, cacheurl)
            c.setopt(c.WRITEFUNCTION, resp.write)
            c.perform()
            c.close()
            result = json.loads(resp.getvalue())
        else:
            resp = requests.get(cacheurl)
            result = resp.json()
    else:
        if pkgdb2client is None:
            raise RuntimeError(
                "Error: required module pkgdb2client not found")
        pkgdb = pkgdb2client.PkgDB()
        result = pkgdb.get_packages(branches=branches, status=status,
                                    page="all")
    return [x["name"] for x in result["packages"]]


def get_installed():
    yumbase = yum.YumBase()
    # do not show info about enabled plugins
    yumbase.preconf.debuglevel = 0

    srpms = {}
    installed = yumbase.rpmdb.returnPackages()
    for pkg in installed:
        srpm = pkg.sourcerpm.rsplit('-', 2)[0]
        srpms.setdefault(srpm, []).append(pkg)

    return srpms


def get_support_status(installed=None, release=RAWHIDE_VERSION,
                       check_missing=True):
    if installed is None:
        installed = get_installed()

    if release == RAWHIDE_VERSION:
        branch = "master"
    elif release <= NEWEST_EPEL:
        branch = LEGACY_EPEL_BRANCHES.get(release, "epel" + str(release))
    else:
        branch = "f" + str(release)

    support_status = {}

    fedora_pkgs = []

    for state in [PKGDB_ORPHANED, PKGDB_RETIRED]:
        pkgdb_pkgs = get_pkgdb_packages(status=state, branches=branch)
        fedora_pkgs.extend(pkgdb_pkgs)
        for pkg in pkgdb_pkgs:
            if pkg in installed:
                support_status.setdefault(state, {})[pkg] = installed[pkg]

    if check_missing:
        # pkgdb query is very slow, therefore it should be disabled if cache is
        # not used
        fedora_pkgs.extend(get_pkgdb_packages(status=PKGDB_APPROVED,
                                              branches=branch))
        installed_fedora = [p for p in installed if
                            installed[p][0].Packager == "Fedora Project"]

        for pkg in installed_fedora:
            if pkg not in fedora_pkgs:
                support_status.setdefault("Missing", {})[pkg] = installed[pkg]

    return support_status


if __name__ == "__main__":
    installed = get_installed()
    osinfo = get_os_info()

    if osinfo.get("ID") == "fedora":
        latest_release = RAWHIDE_VERSION
        flavor = "Fedora"
    else:
        latest_release = NEWEST_EPEL
        flavor = "EPEL"

    # Tested on Fedora 19. CentOS 5 and RHEL 7
    if "VERSION_ID" in osinfo:
        installed_version = osinfo["VERSION_ID"]
    else:
        installed_version = yum.YumBase().conf.yumvar["releasever"]

    if flavor == "EPEL":
        # handle versions like 5Server or 7.0
        installed_version = installed_version[0]

    baseversion = int(installed_version)
    for version in range(baseversion, latest_release + 1):
        support_status = get_support_status(installed, version)
        for state in support_status:
            for basepkg, subpkgs in sorted(
                    support_status.get(state, {}).items(),
                    key=lambda x: x[0].lower()):

                # print("{} (Fedora {}): {}".format(state, version, basepkg))
                common_state = COMMON_STATES.get(state, state)
                print("%s in %s %s: %s" % (common_state, flavor, version,
                                           basepkg))
                for pkg in subpkgs:
                    # print("    {0.nevra}: {0.summary}".format(pkg))
                    print("    %s-%s-%s.%s: %s" % (
                        pkg.name, pkg.version, pkg.release, pkg.arch,
                        pkg.summary))

                print("")
            print("")
