#
# Utility functions for the command line drivers
#
# Copyright 2006-2007  Red Hat, Inc.
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

import os, sys
import logging
import logging.handlers
import locale
from optparse import OptionValueError, OptionParser

import libvirt
import util
from virtinst import Guest, CapabilitiesParser, VirtualNetworkInterface, \
                     VirtualGraphics, VirtualAudio
from virtinst import _virtinst as _

MIN_RAM = 64
force = False

class VirtOptionParser(OptionParser):
    '''Subclass to get print_help to work properly with non-ascii text'''

    def _get_encoding(self, file):
        encoding = getattr(file, "encoding", None)
        if not encoding:
            (language, encoding) = locale.getlocale()
        return encoding

    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        encoding = self._get_encoding(file)
        file.write(self.format_help().encode(encoding, "replace"))

#
# Setup helpers
#

def setupLogging(appname, debug=False):
    # set up logging
    vi_dir = os.path.expanduser("~/.virtinst")
    if not os.access(vi_dir,os.W_OK):
        try:
            os.mkdir(vi_dir)
        except IOError, e:
            raise RuntimeError, "Could not create %d directory: " % vi_dir, e

    dateFormat = "%a, %d %b %Y %H:%M:%S"
    fileFormat = "[%(asctime)s " + appname + " %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamDebugFormat = "%(asctime)s %(levelname)-8s %(message)s"
    streamErrorFormat = "%(levelname)-8s %(message)s"
    filename = os.path.join(vi_dir, appname + ".log")

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    fileHandler = logging.handlers.RotatingFileHandler(filename, "a",
                                                       1024*1024, 5)

    fileHandler.setFormatter(logging.Formatter(fileFormat,
                                               dateFormat))
    rootLogger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler(sys.stderr)
    if debug:
        streamHandler.setLevel(logging.DEBUG)
        streamHandler.setFormatter(logging.Formatter(streamDebugFormat,
                                                     dateFormat))
    else:
        streamHandler.setLevel(logging.ERROR)
        streamHandler.setFormatter(logging.Formatter(streamErrorFormat))
    rootLogger.addHandler(streamHandler)

    # Register libvirt handler
    def libvirt_callback(ctx, err):
        if err[3] != libvirt.VIR_ERR_ERROR:
            # Don't log libvirt errors: global error handler will do that
            logging.warn("Non-error from libvirt: '%s'" % err[2])
    libvirt.registerErrorHandler(f=libvirt_callback, ctx=None)

    # Register python error handler to log exceptions
    def exception_log(type, val, tb):
        import traceback
        str = traceback.format_exception(type, val, tb)
        logging.exception("".join(str))
        sys.__excepthook__(type, val, tb)
    sys.excepthook = exception_log

def fail(msg):
    """Convenience function when failing in cli app"""
    logging.error(msg)
    sys.exit(1)

def getConnection(connect):
    if connect is None or connect.lower()[0:3] == "xen":
        if os.geteuid() != 0:
            fail(_("Must be root to create Xen guests"))

    return libvirt.open(connect)

#
# Prompting
#

def set_force(val=True):
    global force
    force = val

def prompt_for_input(prompt = "", val = None):
    if val is not None:
        return val
    if force:
        raise RuntimeError(_("Force flag is set but input was required. Prompt was: %s" % prompt))
    print prompt + " ",
    return sys.stdin.readline().strip()

def yes_or_no(s):
    s = s.lower()
    if s in ("y", "yes", "1", "true", "t"):
        return True
    elif s in ("n", "no", "0", "false", "f"):
        return False
    raise ValueError, "A yes or no response is required"

def prompt_for_yes_or_no(prompt):
    """catches yes_or_no errors and ensures a valid bool return"""
    if force:
        logging.debug("Forcing return value of True to prompt '%s'")
        return True

    while 1:
        input = prompt_for_input(prompt, None)
        try:
            res = yes_or_no(input)
            break
        except ValueError, e:
            print _("ERROR: "), e
            continue
    return res

#
# Ask for attributes
#

def get_name(name, guest):
    while 1:
        name = prompt_for_input(_("What is the name of your virtual machine?"), name)
        try:
            guest.name = name
            break
        except ValueError, e:
            print "ERROR: ", e
            name = None

def get_memory(memory, guest):
    while 1:
        try:
            memory = int(prompt_for_input(_("How much RAM should be allocated (in megabytes)?"), memory))
            if memory < MIN_RAM:
                print _("ERROR: Installs currently require %d megs of RAM.") %(MIN_RAM,)
                print ""
                memory = None
                continue
            guest.memory = memory
            break
        except ValueError, e:
            print _("ERROR: "), e
            memory = None

def get_uuid(uuid, guest):
    if uuid:
        try:
            guest.uuid = uuid
        except ValueError, e:
            print _("ERROR: "), e
            sys.exit(1)

def get_vcpus(vcpus, check_cpu, guest, conn):
    while 1:
        if check_cpu is None:
            break
        hostinfo = conn.getInfo()
        cpu_num = hostinfo[4] * hostinfo[5] * hostinfo[6] * hostinfo[7]
        if vcpus <= cpu_num:
            break
        res = prompt_for_input(_("You have asked for more virtual CPUs (%d) than there are physical CPUs (%d) on the host. This will work, but performance will be poor. Are you sure? (yes or no)") %(vcpus, cpu_num))
        try:
            if yes_or_no(res):
                break
            vcpus = int(prompt_for_input(_("How many VCPUs should be attached?")))
        except ValueError, e:
            print _("ERROR: "), e
    if vcpus is not None:
        try:
            guest.vcpus = vcpus
        except ValueError, e:
            print _("ERROR: "), e
            sys.exit(1)

def get_cpuset(cpuset, mem, guest, conn):
    if cpuset and cpuset != "auto":
        guest.cpuset = cpuset
    elif cpuset == "auto":
        caps = CapabilitiesParser.parse(conn.getCapabilities())
        if caps.host.topology is None:
            logging.debug("No topology section in caps xml. Skipping cpuset")
            return

        cells = caps.host.topology.cells
        if len(cells) <= 1:
            logging.debug("Capabilities only show <= 1 cell. Not NUMA capable")
            return

        cell_mem = conn.getCellsFreeMemory(0, len(cells))
        cell_id = -1
        mem = mem * 1024
        for i in range(len(cells)):
            if cell_mem[i] > mem and len(cells[i].cpus) != 0:
                # Find smallest cell that fits
                if cell_id < 0 or cell_mem[i] < cell_mem[cell_id]:
                    cell_id = i;
        if cell_id < 0:
            logging.debug("Could not find any usable NUMA cell/cpu combinations. Not setting cpuset.")
            return

        # Build cpuset
        cpustr = ""
        for cpu in cells[cell_id].cpus:
            if cpustr != "":
                cpustr += ","
            cpustr += str(cpu.id)
        logging.debug("Auto cpuset is: %s" % cpustr)
        guest.cpuset = cpustr
    return

def get_network(mac, network, guest):
    if mac == "RANDOM":
        mac = None
    if network == "user":
        n = VirtualNetworkInterface(mac, type="user")
    elif network[0:6] == "bridge":
        n = VirtualNetworkInterface(mac, type="bridge", bridge=network[7:])
    elif network[0:7] == "network":
        n = VirtualNetworkInterface(mac, type="network", network=network[8:])
    else:
        fail(_("Unknown network type ") + network)
    guest.nics.append(n)

def digest_networks(macs, bridges, networks):
    if type(bridges) != list and bridges != None:
        bridges = [ bridges ]

    if type(macs) != list and macs != None:
        macs = [ macs ]

    if type(networks) != list and networks != None:
        networks = [ networks ]

    if bridges is not None and networks != None:
        fail(_("Cannot mix both --bridge and --network arguments"))

    # ensure we have equal length lists
    if bridges != None:
        networks = map(lambda b: "bridge:" + b, bridges)

    if networks != None:
        if macs != None:
            if len(macs) != len(networks):
                fail(_("Need to pass equal numbers of networks & mac addresses"))
        else:
            macs = [ None ] * len(networks)
    else:
        if os.getuid() == 0:
            net = util.default_network()
            networks = [net[0] + ":" + net[1]]
        else:
            networks = ["user"]
        if macs != None:
            if len(macs) > 1:
                fail(_("Need to pass equal numbers of networks & mac addresses"))
        else:
            macs = [ None ]

    return (macs, networks)

def get_graphics(vnc, vncport, nographics, sdl, keymap, guest):
    if (vnc and nographics) or \
       (vnc and sdl) or \
       (sdl and nographics):
        raise ValueError, _("Can't specify more than one of VNC, SDL, or nographics")
    if nographics is not None:
        guest.graphics_dev = None
        return
    if vnc is not None:
        guest.graphics_dev = VirtualGraphics(type=VirtualGraphics.TYPE_VNC)
    if sdl is not None:
        guest.graphics_dev = VirtualGraphics(type=VirtualGraphics.TYPE_SDL)
    while 1:
        if guest.graphics_dev:
            break
        res = prompt_for_input(_("Would you like to enable graphics support? (yes or no)"))
        try:
            vnc = yes_or_no(res)
        except ValueError, e:
            print _("ERROR: "), e
            continue
        if vnc:
            guest.graphics_dev = VirtualGraphics(type=VirtualGraphics.TYPE_VNC)
        else:
            guest.graphics_dev = None
        break
    if vncport:
        guest.graphics_dev.port = vncport
    if keymap:
        guest.graphics_dev.keymap = keymap

def get_sound(sound, guest):

    # Sound is just a boolean value, so just specify a default of 'es1370'
    # model since this should provide audio out of the box for most modern
    # distros
    if sound:
        guest.sound_devs.append(VirtualAudio(model="es1370"))

### Option parsing
def check_before_store(option, opt_str, value, parser):
    if len(value) == 0:
        raise OptionValueError, _("%s option requires an argument") %opt_str
    setattr(parser.values, option.dest, value)

def check_before_append(option, opt_str, value, parser):
    if len(value) == 0:
        raise OptionValueError, _("%s option requires an argument") %opt_str
    parser.values.ensure_value(option.dest, []).append(value)

