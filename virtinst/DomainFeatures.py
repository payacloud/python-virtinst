#
# Copyright 2010  Red Hat, Inc.
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

import XMLBuilderDomain
from XMLBuilderDomain import _xml_property

def _none_or_bool(val):
    if val is None:
        return val
    return bool(val)

class DomainFeatures(XMLBuilderDomain.XMLBuilderDomain):
    """
    Class for generating <features> XML
    """

    def __init__(self, conn, parsexml=None, parsexmlnode=None):
        XMLBuilderDomain.XMLBuilderDomain.__init__(self, conn, parsexml,
                                                   parsexmlnode)

        self._acpi = None
        self._apic = None
        self._pae = None

    def get_acpi(self):
        return self._acpi
    def set_acpi(self, val):
        self._acpi = _none_or_bool(val)
    acpi = _xml_property(get_acpi, set_acpi,
                         xpath="./acpi", is_bool=True)

    def get_apic(self):
        return self._apic
    def set_apic(self, val):
        self._apic = _none_or_bool(val)
    apic = _xml_property(get_apic, set_apic,
                         xpath="./apic", is_bool=True)
    
    def get_pae(self):
        return self._pae
    def set_pae(self, val):
        self._pae = _none_or_bool(val)
    pae = _xml_property(get_pae, set_pae,
                        xpath="./pae", is_bool=True)

    def __setitem__(self, attr, val):
        setattr(self, attr, val)
    def __getitem__(self, attr):
        getitem(self, attr)
    def __delitem__(self, attr):
        setattr(self, attr, None)


    def _get_xml_config(self, defaults={}):
        ret = ""

        feature_xml = ""
        if self.acpi or (self.acpi is None and defaults.get("acpi")):
            feature_xml += "<acpi/>"
        if self.apic or (self.apic is None and defaults.get("apic")):
            feature_xml += "<apic/>"
        if self.pae:
            feature_xml += "<pae/>"

        if feature_xml:
            ret += "  <features>\n"
            ret += "    %s\n" % feature_xml
            ret += "  </features>"

        return ret
