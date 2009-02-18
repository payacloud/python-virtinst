#
# Copyright 2006-2009  Red Hat, Inc.
# Jeremy Katz <katzj@redhat.com>
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

import re
import logging
import libxml2
import libvirt
import __builtin__

import _util
import VirtualDevice
from virtinst import _virtinst as _

class VirtualNetworkInterface(VirtualDevice.VirtualDevice):

    TYPE_BRIDGE  = "bridge"
    TYPE_VIRTUAL = "network"
    TYPE_USER    = "user"

    def __init__(self, macaddr=None, type=TYPE_BRIDGE, bridge=None,
                 network=None, model=None, conn=None):
        VirtualDevice.VirtualDevice.__init__(self, conn)

        if (macaddr is not None and __builtin__.type(macaddr) is not str):
            raise ValueError, _("MAC address must be a string.")

        if macaddr is not None:
            form = re.match("^([0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}$",macaddr)
            if form is None:
                raise ValueError, \
                    _("MAC address must be of the format AA:BB:CC:DD:EE:FF")

        self._network = None

        self.macaddr = macaddr
        self.type = type
        self.bridge = bridge
        self.network = network
        self.model = model
        if self.type == self.TYPE_VIRTUAL:
            if network is None:
                raise ValueError, _("A network name was not provided")
        elif self.type == self.TYPE_BRIDGE:
            pass
        elif self.type == self.TYPE_USER:
            pass
        else:
            raise ValueError, _("Unknown network type %s") % (type,)

    def get_network(self):
        return self._network
    def set_network(self, newnet):
        def _is_net_active(netobj):
            """Apparently the 'info' command was never hooked up for
               libvirt virNetwork python apis."""
            if not self.conn:
                return True
            return self.conn.listNetworks().count(netobj.name())

        if newnet is not None and self.conn:
            try:
                net = self.conn.networkLookupByName(newnet)
            except libvirt.libvirtError, e:
                raise ValueError(_("Virtual network '%s' does not exist: %s") \
                                   % (newnet, str(e)))
            if not _is_net_active(net):
                raise ValueError(_("Virtual network '%s' has not been "
                                   "started.") % newnet)

        self._network = newnet
    network = property(get_network, set_network)

    def is_conflict_net(self, conn):
        """is_conflict_net: determines if mac conflicts with others in system

           returns a two element tuple:
               first element is True if fatal collision occured
               second element is a string description of the collision.
           Non fatal collisions (mac addr collides with inactive guest) will
           return (False, "description of collision")"""
        if self.macaddr is None:
            return (False, None)
        # get Running Domains
        ids = conn.listDomainsID()
        vms = []
        for i in ids:
            try:
                vm = conn.lookupByID(i)
                vms.append(vm)
            except libvirt.libvirtError:
                # guest probably in process of dieing
                logging.warn("conflict_net: Failed to lookup domain id %d" % i)
        # get inactive Domains
        inactive_vm = []
        names = conn.listDefinedDomains()
        for name in names:
            try:
                vm = conn.lookupByName(name)
                inactive_vm.append(vm)
            except:
                # guest probably in process of dieing
                logging.warn("conflict_net: Failed to lookup domain %d" % name)

        # get the Host's NIC MACaddress
        hostdevs = _util.get_host_network_devices()

        if self.countMACaddr(vms) > 0:
            return (True, _("The MAC address you entered is already in use by another active virtual machine."))
        for (dummy, dummy, dummy, dummy, host_macaddr) in hostdevs:
            if self.macaddr.upper() == host_macaddr.upper():
                return (True, _("The MAC address you entered conflicts with a device on the physical host."))
        if self.countMACaddr(inactive_vm) > 0:
            return (False, _("The MAC address you entered is already in use by another inactive virtual machine."))
        return (False, None)

    def setup(self, conn):
        if self.macaddr is None:
            while 1:
                self.macaddr = _util.randomMAC(type=conn.getType().lower())
                if self.is_conflict_net(conn)[1] is not None:
                    continue
                else:
                    break
        else:
            ret, msg = self.is_conflict_net(conn)
            if msg is not None:
                if ret is False:
                    logging.warning(msg)
                else:
                    raise RuntimeError(msg)

        if not self.bridge and self.type == "bridge":
            self.bridge = _util.default_bridge()

    def get_xml_config(self):
        src_xml = ""
        model_xml = ""
        if self.type == self.TYPE_BRIDGE:
            src_xml =   "      <source bridge='%s'/>\n" % self.bridge
        elif self.type == self.TYPE_VIRTUAL:
            src_xml =   "      <source network='%s'/>\n" % self.network

        if self.model:
            model_xml = "      <model type='%s'/>\n" % self.model

        return "    <interface type='%s'>\n" % self.type + \
               src_xml + \
               "      <mac address='%s'/>\n" % self.macaddr + \
               model_xml + \
               "    </interface>"

    def countMACaddr(self, vms):
        if not self.macaddr:
            return
        count = 0
        for vm in vms:
            doc = None
            try:
                doc = libxml2.parseDoc(vm.XMLDesc(0))
            except:
                continue
            ctx = doc.xpathNewContext()
            try:
                for mac in ctx.xpathEval("/domain/devices/interface/mac"):
                    macaddr = mac.xpathEval("attribute::address")[0].content
                    if macaddr and _util.compareMAC(self.macaddr, macaddr) == 0:
                        count += 1
            finally:
                if ctx is not None:
                    ctx.xpathFreeContext()
                if doc is not None:
                    doc.freeDoc()
        return count

# Back compat class to avoid ABI break
class XenNetworkInterface(VirtualNetworkInterface):
    pass
