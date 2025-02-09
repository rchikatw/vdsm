#!/usr/bin/python3
#
# Copyright 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import print_function

'''
Hook to enable disk UNMAP(TRIM) for disk devices.

Syntax:
   diskunmap=(off|on)

Example:
   diskunmap=on
'''

import os
import sys
import traceback
from xml.dom import minidom

import hooking


def addDiscardUnmap(domxml):
    for disk in domxml.getElementsByTagName('disk'):
        device = disk.getAttribute('device')
        target = disk.getElementsByTagName('target')[0]
        bus = target.getAttribute('bus')
        if ((device == 'disk' or device == 'lun')
           and (bus == 'scsi' or bus == 'ide')):
            driver = disk.getElementsByTagName('driver')[0]
            driver.setAttribute('discard', 'unmap')


def main():
    if 'diskunmap' in os.environ:
        unmapConfig = os.environ['diskunmap']
        domxml = hooking.read_domxml()
        if unmapConfig == 'on':
            addDiscardUnmap(domxml)
            hooking.write_domxml(domxml)


def test():
    text = '''<disk device="disk" snapshot="no" type="block">
<address bus="0" controller="0" target="0" type="drive" unit="0"/>
<source dev="/rhev/data-center/mnt/blockSD/
b4cf7d74-6a07-4138-9d4f-80b14c3acefd/images/
1580607a-b240-4199-99ac-3d2162934ba6/e5ba276f-dcba-4582-b13f-c165afa2f575"/>
<target bus="ide" dev="hda"/>
<serial>1580607a-b240-4199-99ac-3d2162934ba6</serial>
<driver cache="none" error_policy="stop" io="native"
name="qemu" type="raw"/>
</disk>'''

    xmldom = minidom.parseString(text)

    disk = xmldom.getElementsByTagName('disk')[0]
    print("\nDisk device definition before execution: \n%s"
          % disk.toxml(encoding='UTF-8'))

    addDiscardUnmap(xmldom)

    print("\nDisk device after setting discard attribute: \n%s"
          % disk.toxml(encoding='UTF-8'))


if __name__ == '__main__':
    try:
        if '--test' in sys.argv:
            test()
        else:
            main()
    except:
        hooking.exit_hook(' diskunmap hook: [unexpected error]: %s\n' %
                          traceback.format_exc())
