#
# Copyright 2007-2011 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Refer to the README and COPYING files for full details of the license
#

"""
This module provides DSA software versioning information for
python based components
"""
version_name = "Snow Man"
software_version = "4.9"
software_revision = "0"

version_info = {
    'version_name': version_name,
    'software_version': software_version,
    'software_revision': software_revision,
    'supportedRHEVMs': ['3.0'],
    'supportedProtocols': ['2.2', '2.3'],
    'clusterLevels': ['3.0', '3.1'],
}
