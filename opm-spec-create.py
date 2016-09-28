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
import jinja2
import tempfile

from jinja2 import Environment, FileSystemLoader

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

def load_template_dir(template_dir):
    return jinja2.FileSystemLoader(os.getcwd() + '/' + template_dir)

def scrub_metadata(metadata,pkg):
    if 'description' not in metadata:
        metadata['description'] = 'FIXME: NONE FOUND'
    metadata['name'] = generate_package_name(metadata['name'])
    for dep in metadata['dependencies']:
        dep['name'] = generate_package_name(dep['name'])
    metadata['source0'] = get_download_url(pkg['upstream'])
    metadata['project'] = transform_mod_name(pkg['project'])
    metadata['from_puppetlabs'] = is_from_puppetlabs(pkg['upstream'])
    if is_from_puppetlabs(pkg['upstream']):
        metadata['project_name'] = pkg['project'].replace('puppet-', 'puppetlabs-', 1)
        metadata['upstream_name'] = 'upstream_name'
    else:
        metadata['upstream_name'] = 'name'

    return metadata

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
    dl_url = ""
    upstream_url = parse.urlsplit(url)
    path = upstream_url.path.split(".git")[0]
    if '/openstack/' in path:
        dl_url = "https://tarballs.openstack.org/%{name}/%{name}-%{version}.tar.gz"
    else:
        dl_url = ("https",
                upstream_url.netloc,
                "%s/archive/%%{version}.tar.gz" % path,
                "", "", "")
        dl_url = parse.urlunparse(dl_url)
    return dl_url


def generate_spec_file(out_path, pkg, template):
    project = pkg['project']
    metadata = scrub_metadata(load_metadata_file('metadata.json'), pkg)
    out = os.path.join(out_path,
                       '%s.spec'
                       % project)
    rend_out = template.render(metadata=metadata)
    print_spec(rend_out, out)
    print "The spec file is available at: %s.spec" % (os.path.join(out_path,
                                                                   project))

def print_spec(spec, out):
    out = open(out, 'w')
    out.write(spec)
    out.close()

if __name__ == '__main__':
    rdoinfo = fetch_rdoinfo(RDOINFO)
    wdir = tempfile.mkdtemp()
    loader= load_template_dir('templates')
    env = Environment(loader=loader)
    template = env.get_template('puppet.spec')

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
            except Exception, e:
                print "[FAILED] Clone from %s (%s)" % (upstream_url, e)

            with cdir(pdir):
                if os.path.isfile('metadata.json'):
                    print "Attempt to generate spec file for %s" % project
                    generate_spec_file(wdir, pkg, template)
