# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import imp
import shutil
import json
import tempfile

from six.moves.urllib import parse

from rdopkg.repoman import RepoManager
from rdopkg.helpers import cdir
from rdopkg.utils.cmd import git


RDOINFO = 'https://review.rdoproject.org/r/rdoinfo.git'


def fetch_rdoinfo(rdoinfo_repo):
    userdir = os.path.join(os.path.expanduser('~/'),
                           '.opm-spec-sync')
    if not os.path.isdir(userdir):
        os.mkdir(userdir)
    rm = RepoManager(userdir, rdoinfo_repo, verbose=True)
    rm.init(force_fetch=True)
    file, path, desc = imp.find_module('rdoinfo', [rm.repo_path])
    rdoinfo = imp.load_module('rdoinfo', file, path, desc)
    return rdoinfo.parse_info_file(os.path.join(userdir,
                                                'rdoinfo/rdo.yml'))


def load_metadata_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)


def transform_mod_name(modname):
    if '-' in modname:
        return modname.split('-')[-1]
    if '/' in modname:
        return modname.split('/')[-1]


def is_from_puppetlabs(url):
    up_url = parse.urlsplit(url)
    path = up_url.path.split(".git")[0]
    path = path.split("/")[-1]
    if path.startswith("puppetlabs-"):
        return True
    else:
        return False


def generate_package_name(modname):
    return "puppet-%s" % transform_mod_name(modname)


def get_download_url(url):
    upstream_url = parse.urlsplit(url)
    path = upstream_url.path.split(".git")[0]
    dl_url = ("https",
              upstream_url.netloc,
              "%s/archive/%%{version}.tar.gz" % path,
              "", "", "")
    dl_url = parse.urlunparse(dl_url)
    return dl_url


def generate_spec_file(out_path, prj_name, info_pm):
    puppetlabs_name = None
    metadata = load_metadata_file('metadata.json')
    out = open(os.path.join(out_path,
                            '%s.spec'
                            % prj_name), 'w')

    # FIXME
    download_url = get_download_url(info_pm['upstream'])

    if is_from_puppetlabs(info_pm['upstream']):
        puppetlabs_name = prj_name.replace('puppet-', 'puppetlabs-', 1)
        out.write('%%define upstream_name %s\n\n' % puppetlabs_name)

    out.write('Name:\t\t\t%s\n' % prj_name)
    out.write('Version:\t\tXXX\n')
    out.write('Release:\t\tXXX\n')
    out.write('Summary:\t\t%s\n' % metadata['summary'])
    out.write('License:\t\t%s\n\n' % metadata['license'])
    out.write('URL:\t\t\t%s\n\n' % metadata['project_page'])
    out.write('Source0:\t\t%s\n\n' % download_url)
    out.write('BuildArch:\t\tnoarch\n\n')

    for dep in metadata['dependencies']:
        out.write('Requires:\t\t%s\n'
                  % generate_package_name(dep['name']))

    out.write('Requires:\t\tpuppet >= 2.7.0\n')
    out.write('\n')
    out.write('%%description\n%s\n\n' % metadata['summary'])
    out.write('%prep\n')
    if puppetlabs_name is not None:
        out.write('%setup -q -n %{upstream_name}-%{upstream_version}\n')
    else:
        out.write('%setup -q -n %{name}-%{version}\n')
    cleanup_cmds = """
find . -type f -name ".*" -exec rm {} +
find . -size 0 -exec rm {} +
find . \( -name "*.pl" -o -name "*.sh"  \) -exec chmod +x {} +
find . \( -name "*.pp" -o -name "*.py"  \) -exec chmod -x {} +
find . \( -name "*.rb" -o -name "*.erb" \) -exec chmod -x {} +
find . \( -name spec -o -name ext \) | xargs rm -rf\n
"""
    out.write(cleanup_cmds)

    out.write('%build\n\n')
    install_cmds = """
%%install
rm -rf %%{buildroot}
install -d -m 0755 %%{buildroot}/%%{_datadir}/openstack-puppet/modules/%s/
cp -rp * %%{buildroot}/%%{_datadir}/openstack-puppet/modules/%s/
""" % (transform_mod_name(prj_name), transform_mod_name(prj_name))

    out.write(install_cmds)
    if "nova" in generate_package_name(metadata['name']):
        out.write("rm -f %{buildroot}/%{_datadir}/openstack-puppet/modules/nova/files/nova-novncproxy.init\n")
    else:
        out.write("\n\n")

    files_cmds = """
%%files
%%{_datadir}/openstack-puppet/modules/%s/\n\n
""" % transform_mod_name(prj_name)

    out.write(files_cmds)
    out.write('%changelog\n\n')
    out.close()


if __name__ == '__main__':
    rdoinfo = fetch_rdoinfo(RDOINFO)
    wdir = tempfile.mkdtemp()

    if len(sys.argv) == 2:
        rdoinfo['packages'] = [r for r in rdoinfo['packages'] if
                               r['project'] == sys.argv[1]]

    for pkg in rdoinfo['packages']:
        if pkg['conf'] == 'rpmfactory-puppet':
            upstream_url = pkg['upstream']
            project = pkg['project']
            print "Attempt to clone %s from %s to %s" % (project,
                                                         upstream_url,
                                                         wdir)

            pdir = os.path.join(wdir, project)
            if os.path.isdir(pdir):
                shutil.rmtree(pdir)
            try:
                with cdir(wdir):
                    git('clone', upstream_url, project)
                with cdir(pdir):
                    if os.path.isfile('metadata.json'):
                        generate_spec_file(wdir, project, pkg)
            except Exception, e:
                print "[FAILED] Clone from %s (%s)" % (upstream_url, e)
