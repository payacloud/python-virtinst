#
# Copyright 2011  Red Hat, Inc.
# Cole Robinson <crobinso@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free  Software Foundation; either version 2 of the License, or
# (at your option)  any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.

import os

import VirtualDevice
from virtinst import _gettext as _
from XMLBuilderDomain import _xml_property

class VirtualFilesystem(VirtualDevice.VirtualDevice):

    _virtual_device_type = VirtualDevice.VirtualDevice.VIRTUAL_DEV_FILESYSTEM

    _target_props = ["dir", "name", "file", "dev"]

    TYPE_MOUNT = "mount"
    TYPE_TEMPLATE = "template"
    TYPE_FILE = "file"
    TYPE_BLOCK = "block"
    TYPE_DEFAULT = "default"
    TYPES = [TYPE_MOUNT, TYPE_TEMPLATE, TYPE_FILE, TYPE_BLOCK, TYPE_DEFAULT]

    MODE_PASSTHROUGH = "passthrough"
    MODE_MAPPED = "mapped"
    MODE_SQUASH = "squash"
    MODE_DEFAULT = "default"
    MOUNT_MODES = [MODE_PASSTHROUGH, MODE_MAPPED, MODE_SQUASH, MODE_DEFAULT]

    @staticmethod
    def type_to_source_prop(fs_type):
        """
        Convert a value of VirtualFilesystem.type to it's associated XML
        source @prop name
        """
        if (fs_type == VirtualFilesystem.TYPE_MOUNT or
            fs_type == VirtualFilesystem.TYPE_DEFAULT or
            fs_type is None):
            return "dir"
        elif fs_type == VirtualFilesystem.TYPE_TEMPLATE:
            return "name"
        elif fs_type == VirtualFilesystem.TYPE_FILE:
            return "file"
        elif fs_type == VirtualFilesystem.TYPE_BLOCK:
            return "dev"
        return "dir"

    def __init__(self, conn, parsexml=None, parsexmlnode=None, caps=None):
        VirtualDevice.VirtualDevice.__init__(self, conn, parsexml,
                                             parsexmlnode, caps)

        self._type = None
        self._mode = None
        self._target = None
        self._source = None

        if self._is_parse():
            return

        self.mode = self.MODE_DEFAULT
        self.type = self.TYPE_DEFAULT

    def _get_type(self):
        return self._type
    def _set_type(self, val):
        if val is not None and not self.TYPES.count(val):
            raise ValueError(_("Unsupported filesystem type '%s'" % val))
        self._type = val
    type = _xml_property(_get_type, _set_type, xpath="./@type")

    def _get_mode(self):
        return self._mode
    def _set_mode(self, val):
        if val is not None and not self.MOUNT_MODES.count(val):
            raise ValueError(_("Unsupported filesystem mode '%s'" % val))
        self._mode = val
    mode = _xml_property(_get_mode, _set_mode, xpath="./@accessmode")

    def _get_source(self):
        return self._source
    def _set_source(self, val):
        if self.type != self.TYPE_TEMPLATE:
            val = os.path.abspath(val)
        self._source = val
    def _xml_get_source_xpath(self):
        xpath = None
        ret = "./source/@dir"
        for prop in self._target_props:
            xpath = "./source/@" + prop
            if self._xml_ctx.xpathEval(xpath):
                ret = xpath

        return ret
    def _xml_set_source_xpath(self):
        ret = "./source/@" + self.type_to_source_prop(self.type)
        return ret
    source = _xml_property(_get_source, _set_source,
                           xml_get_xpath=_xml_get_source_xpath,
                           xml_set_xpath=_xml_set_source_xpath)

    def _get_target(self):
        return self._target
    def _set_target(self, val):
        if not os.path.isabs(val):
            raise ValueError(_("Filesystem target '%s' must be an absolute "
                               "path") % val)
        self._target = val
    target = _xml_property(_get_target, _set_target, xpath="./target/@dir")


    def _get_xml_config(self):
        mode = self.mode
        ftype = self.type
        source = self.source
        target = self.target

        if mode == self.MODE_DEFAULT:
            mode = None
        if ftype == self.TYPE_DEFAULT:
            ftype = None

        if not source or not target:
            raise ValueError(
                _("A filesystem source and target must be specified"))

        fsxml = "    <filesystem"
        if ftype:
            fsxml += " type='%s'" % ftype
        if mode:
            fsxml += " accessmode='%s'" % mode
        fsxml += ">\n"

        fsxml += "      <source %s='%s'/>\n" % (
                                            self.type_to_source_prop(ftype),
                                            source)
        fsxml += "      <target dir='%s'/>\n" % target

        fsxml += "    </filesystem>"

        return fsxml
