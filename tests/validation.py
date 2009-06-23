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

import libvirt
import virtinst
from virtinst import VirtualDisk

# Test helpers
from storage import createPool, createVol

import unittest
import logging
import traceback
import os

# Template for adding arguments to test
# { 'label' : { \
#       'VAR' : { \
#           'invalid' : [param],
#           'valid'   : [param]},
#       '__init__'  : { \
#           'invalid' : [{'initparam':val}],
#           'valid'   : [{'initparam':val}]}
#
#   Anything in 'valid' should throw no error
#   Anything in 'invalid' should throw ValueError or TypeError

# We install several storage pools on the connection to ensure
# we aren't bumping up against errors in that department.
logging.debug("\n\nStarting 'validation' storage setup.")
testconn = libvirt.open("test:///default")
testcaps = virtinst.CapabilitiesParser.parse(testconn.getCapabilities())

virtimage = virtinst.ImageParser.parse_file("tests/image-xml/image.xml")

offdskpaths = [ "/dev", ]
for path in offdskpaths:
    createPool(testconn, virtinst.Storage.StoragePool.TYPE_DISK,
               tpath=path, start=False, fmt="dos")

dirpaths = [ "/var/lib/libvirt/images", "/", "/tmp" ]
for path in dirpaths:
    createPool(testconn, virtinst.Storage.StoragePool.TYPE_DIR,
               tpath=path, start=True)

dskpaths = [ "/somedev", "/dev/disk/by-uuid" ]
for path in dskpaths:
    createPool(testconn, virtinst.Storage.StoragePool.TYPE_DISK,
               fmt="dos", tpath=path, start=False)

# Create a usable pool/vol pairs
p = createPool(testconn, virtinst.Storage.StoragePool.TYPE_DIR,
               tpath="/pool-exist", start=True, poolname="pool-exist")
dirvol = createVol(p, "vol-exist")
volinst = virtinst.Storage.StorageVolume(pool=p, name="somevol", capacity=1)
logging.debug("Ending 'validation' storage setup.\n\n")

args = {

'guest' : {
    'name'  : {
        'invalid' : ['123456789', 'im_invalid!', '', 0,
                     'verylongnameverylongnameverylongnamevery'
                     'longnameveryvery', "test" # In use,
                     ],
        'valid'   : ['Valid_name.01'] },
    'memory' : {
        'invalid' : [-1, 0, ''],
        'valid'   : [200, 2000] },
    'maxmemory' : {
        'invalid' : [-1, 0, ''],
        'valid'   : [200, 2000], },
    'uuid'      : {
        'invalid' : [ '', 0, '1234567812345678123456781234567x'],
        'valid'   : ['12345678123456781234567812345678',
                     '12345678-1234-1234-ABCD-ABCDEF123456']},
    'vcpus'     : {
        'invalid' : [-1, 0, 1000, ''],
        'valid'   : [ 1, 32 ] },
    'graphics'  : {
        'invalid' : ['', True, 'unknown', {}, ('', '', '', 0),
                     ('','','', 'longerthan16chars'),
                     ('','','','invalid!!ch@r')],
        'valid'   : [False, 'sdl', 'vnc', (True, 'sdl', '', 'key_map-2'),
                     {'enabled' : True, 'type':'vnc', 'opts':5900} ]},
    'type'      : {
        'invalid' : [],
        'valid'   : ['sometype'] },
    'cdrom'     : {
        'invalid' : ['', 0, '/somepath'],
        'valid'   : ['/dev/loop0']
    },
    'arch'      : {
        'invalid' : [],
        'valid'   : ["i386", 'i686', 'x86_64'],
    },
},

'fvguest'  : {
    'os_type'   : {
        'invalid' : ['notpresent',0,''],
        'valid'   : ['other', 'windows', 'unix', 'linux']},
    'os_variant': {
        'invalid' : ['', 0, 'invalid'],
        'valid'   : ['rhel5', 'sles10']},
},

'disk' : {
    'init_conns' : [ testconn, None ],
    '__init__' : {
        'invalid' : [{ 'path' : 0},
                     { 'path' : '/root' },
                     { 'path' : 'valid', 'size' : None },
                     { 'path' : "valid", 'size' : 'invalid' },
                     { 'path' : 'valid', 'size' : -1},
                     { 'path' : 'notblock', 'type' : VirtualDisk.TYPE_BLOCK},
                     { 'path' :'/dev/null', 'type' : VirtualDisk.TYPE_BLOCK},
                     { 'path' : None },
                     { 'path' : "noexist", 'size' : 900000, 'sparse' : False },
                     { 'path' : "noexist", 'type' : VirtualDisk.DEVICE_CDROM},
                     { 'volName' : ("pool-exist", "vol-exist")},
                     { 'conn' : testconn, 'volName' : ("pool-noexist",
                                                       "vol-exist")},
                     { 'conn' : testconn, 'volName' : ("pool-exist",
                                                       "vol-noexist")},
                     { 'conn' : testconn, 'volName' : ( 1234,
                                                       "vol-noexist")},
                     { 'path' : 'valid', 'size' : 1,
                       'driverCache' : 'invalid' },
                    ],

        'valid' :   [{ 'path' : '/dev/loop0' },
                     { 'path' : 'nonexist', 'size' : 1 },
                     { 'path' :'/dev/null'},
                     { 'path' : None, 'device' : VirtualDisk.DEVICE_CDROM},
                     { 'path' : None, 'device' : VirtualDisk.DEVICE_FLOPPY},
                     { 'conn' : testconn, 'volName' : ("pool-exist",
                                                       "vol-exist")},
                     { 'conn' : testconn, 'path' : "/pool-exist/vol-exist" },
                     { 'conn' : testconn, 'path' : "/pool-exist/vol-noexist",
                       'size' : 1 },
                     { 'conn' : testconn, 'volInstall': volinst},
                     { 'path' : 'nonexist', 'size' : 1,
                       'driverCache' : 'writethrough' },
                    ]
                },
    'shareable' : {
        'invalid': [ None, 1234 ],
        'valid': [ True, False ] },
},

'installer' : {
    'init_conns' : [ testconn, None ],
    'boot' : {
        'invalid' : ['', 0, ('1element'), ['1el', '2el', '3el'],
                     {'1element': '1val'},
                     {'kernel' : 'a', 'wronglabel' : 'b'}],
        'valid'   : [('kern', 'init'), ['kern', 'init'],
                     { 'kernel' : 'a', 'initrd' : 'b'}]},
    'extraargs' : {
        'invalid' : [],
        'valid'   : ['someargs']},
    'arch' : {
        'invalid' : [],
        'valid'   : ['i686', 'i386', 'x86_64'],
    }
},

'distroinstaller' : {
    'init_conns' : [ testconn, None ],
    'location'  : {
        'invalid' : ['nogood', 'http:/nogood', [], None,
                     ("pool-noexist", "vol-exist"),
                     ("pool-exist", "vol-noexist"),
                    ],
        'valid'   : ['/dev/null', 'http://web', 'ftp://ftp', 'nfs:nfsserv',
                     '/tmp', # For installing from local dir tree
                     ("pool-exist", "vol-exist"),
                    ]}
},

'livecdinstaller' : {
    'init_conns' : [ testconn, None ],
    'location'  : {
        'invalid' : ['path-noexist',
                     ("pool-noexist", "vol-exist"),
                     ("pool-exist", "vol-noexist"),
                    ],
        'valid'   : ['/dev/null', ("pool-exist", "vol-exist"),
                    ]}
},

'imageinstaller' : {
    '__init__' : {
        'invalid' : \
            [{'image' : virtimage, 'capabilities': testcaps, 'boot_index': 5},
             {'image' : virtimage, 'capabilities': "foo"},],
        'valid'   : \
            [{'image' : virtimage, 'capabilities': testcaps, 'boot_index': 1},
            {'image' : virtimage },
            {'image' : virtimage, 'capabilities': testcaps, 'conn': None},],
    }
},

'network'   : {
    'init_conns' : [ testconn, None ],
    '__init__'  : {
        'invalid' : [ {'macaddr':0}, {'macaddr':''}, {'macaddr':'$%XD'},
                      {'type':'network'} ],
        'valid'   : []}
},

'clonedesign' : {
    'original_guest' :{
        'invalid' : ['idontexist'],
        'valid'   : ['test']},
    'clone_name': { 'invalid' : [0, 'test' # Already in use
                                ],
                    'valid'   : ['some.valid-name_9']},
    'clone_uuid': { 'invalid' : [0],
                    'valid'   : ['12345678123456781234567812345678']},
    'clone_mac' : { 'invalid' : ['badformat'],
                    'valid'   : ['AA:BB:CC:DD:EE:FF']},
    'clone_bs'  : { 'invalid' : [], 'valid'   : ['valid']},
},

'inputdev' : {
    'init_conns' : [ testconn ],
    'type' : {
        'valid'   : [ "mouse", "tablet"],
        'invalid' : [ "foobar", 1234]},
    'bus' : {
        'valid'   : [ "ps2", "xen", "usb"],
        'invalid' : [ "foobar", 1234]},
},

'chardev' : {
    'init_conns' : [ testconn ],
    'source_path': {
        'invalid'   : [],
        'valid'     : [ "/some/path" ]},
    'source_mode': {
        'invalid'   : [ None ],
        'valid'     : virtinst.VirtualCharDevice.char_modes },
    'source_host': {
        'invalid'   : [],
        'valid'     : [ "some.source.host" ]},
    'source_port': {
        'invalid'   : [ "foobar"],
        'valid'     : [ 1234 ]},
    'connect_host': {
        'invalid'   : [],
        'valid'     : [ "some.connect.com" ]},
    'connect_port': {
        'invalid'   : [ "foobar"],
        'valid'     : [ 1234 ]},
    'wire_mode': {
        'invalid'   : [ None ],
        'valid'     : virtinst.VirtualCharDevice.char_wire_modes },
}

} # End of validation dict


class TestValidation(unittest.TestCase):

    def _getInitConns(self, label):
        if args[label].has_key("init_conns"):
            return args[label]["init_conns"]
        return [testconn]

    def _runObjInit(self, testclass, valuedict, defaultsdict=None):
        if defaultsdict:
            for key in defaultsdict.keys():
                if not valuedict.has_key(key):
                    valuedict[key] = defaultsdict.get(key)
        testclass(*(), **valuedict)

    def _testInvalid(self, name, obj, testclass, paramname, paramvalue):
        try:
            if paramname == '__init__':
                self._runObjInit(testclass, paramvalue)
            else:
                setattr(obj, paramname, paramvalue)

            msg = ("Expected TypeError or ValueError: None Raised.\n"
                   "For '%s' object, paramname '%s', val '%s':" %
                   (name, paramname, paramvalue))
            raise AssertionError, msg

        except AssertionError:
            raise
        except (TypeError, ValueError):
            # This is an expected error
            pass
        except Exception, e:
            msg = ("Unexpected exception raised: %s\n" % e +
                   "Original traceback was: \n%s\n" % traceback.format_exc() +
                   "For '%s' object, paramname '%s', val '%s':" %
                   (name, paramname, paramvalue))
            raise AssertionError, msg

    def _testValid(self, name, obj, testclass, paramname, paramvalue):

        try:
            if paramname is '__init__':
                conns = self._getInitConns(name)
                if paramvalue.has_key("conn"):
                    conns = [paramvalue["conn"]]
                for conn in conns:
                    paramvalue["conn"] = conn
                    self._runObjInit(testclass, paramvalue)
            else:
                setattr(obj, paramname, paramvalue)
        except Exception, e:
            msg = ("Validation case failed, expected success.\n" +
                   "Exception received was: %s\n" % e +
                   "Original traceback was: \n%s\n" % traceback.format_exc() +
                   "For '%s' object, paramname '%s', val '%s':" %
                   (name, paramname, paramvalue))
            raise AssertionError, msg

    def _testArgs(self, obj, testclass, name, exception_check=None,
                  manual_dict=None):
        """@obj Object to test parameters against
           @testclass Full class to test initialization against
           @name String name indexing args"""
        logging.debug("Testing '%s'" % name)
        testdict = args[name]
        if manual_dict != None:
            testdict = manual_dict

        for paramname in testdict.keys():
            if paramname == "init_conns":
                continue

            for val in testdict[paramname]['invalid']:
                self._testInvalid(name, obj, testclass, paramname, val)

            for val in testdict[paramname]['valid']:
                if exception_check:
                    if exception_check(obj, paramname, val):
                        continue
                self._testValid(name, obj, testclass, paramname, val)


    # Actual Tests
    def testGuestValidation(self):
        PVGuest = virtinst.ParaVirtGuest(connection=testconn,
                                         type="xen")
        self._testArgs(PVGuest, virtinst.Guest, 'guest')

    def testDiskValidation(self):
        disk = VirtualDisk("/dev/loop0")
        self._testArgs(disk, VirtualDisk, 'disk')

    def testFVGuestValidation(self):
        FVGuest = virtinst.FullVirtGuest(connection=testconn,
                                         type="xen")
        self._testArgs(FVGuest, virtinst.FullVirtGuest, 'fvguest')

    def testNetworkValidation(self):
        network = virtinst.VirtualNetworkInterface(conn=testconn)
        self._testArgs(network, virtinst.VirtualNetworkInterface, 'network')

        # Test MAC Address collision
        hostmac = virtinst.util.get_host_network_devices()
        if len(hostmac) is not 0:
            hostmac = hostmac[0][4]

        for params in ({'macaddr' : hostmac},):
            network = virtinst.VirtualNetworkInterface(*(), **params)
            self.assertRaises(RuntimeError, network.setup, \
                              testconn)

        # Test dynamic MAC/Bridge success
        try:
            network = virtinst.VirtualNetworkInterface()
            network.setup(testconn)
        except Exception, e:
            raise AssertionError, \
                "Network setup with no params failed, expected success." + \
                " Exception was: %s: %s" % (str(e), "".join(traceback.format_exc()))

    def testDistroInstaller(self):
        def exception_check(obj, paramname, paramvalue):
            if paramname == "location":
                # Skip NFS test as non-root
                if paramvalue[0:3] == "nfs" and os.geteuid() != 0:
                    return True

                # Don't pass a tuple location if installer has no conn
                if not obj.conn and type(paramvalue) == tuple:
                    return True

            return False

        label = 'distroinstaller'
        for conn in self._getInitConns(label):
            dinstall = virtinst.DistroInstaller(conn=conn)
            self._testArgs(dinstall, virtinst.DistroInstaller, 'installer',
                           exception_check)
            self._testArgs(dinstall, virtinst.DistroInstaller, label,
                           exception_check)

    def testLiveCDInstaller(self):
        def exception_check(obj, paramname, paramvalue):
            if paramname == 'location':
                # Don't pass a tuple location if installer has no conn
                if not obj.conn and type(paramvalue) == tuple:
                    return True

            return False

        label = 'livecdinstaller'
        for conn in self._getInitConns(label):
            dinstall = virtinst.LiveCDInstaller(conn=conn)
            self._testArgs(dinstall, virtinst.LiveCDInstaller, 'installer',
                           exception_check)
            self._testArgs(dinstall, virtinst.LiveCDInstaller, label,
                           exception_check)

    def testImageInstaller(self):
        label = 'imageinstaller'
        inst_obj = virtinst.ImageInstaller(image=virtimage,
                                           capabilities=testcaps)
        #self._testArgs(inst_obj, virtinst.ImageInstaller, 'installer')
        self._testArgs(inst_obj, virtinst.ImageInstaller, label)

    def testCloneManager(self):
        label = 'clonedesign'
        for conn in self._getInitConns(label):
            cman = virtinst.CloneManager.CloneDesign(conn)
            self._testArgs(cman, virtinst.CloneManager.CloneDesign, label)

    def testInputDev(self):
        label = 'inputdev'
        for conn in self._getInitConns(label):
            cman = virtinst.VirtualInputDevice(conn)
            self._testArgs(cman, virtinst.VirtualInputDevice, label)

    def testCharDev(self):
        label = 'chardev'
        paramdict = args[label]
        devs = []

        for conn in self._getInitConns(label):
            for dev in virtinst.VirtualCharDevice.dev_types:
                for char in virtinst.VirtualCharDevice.char_types:
                    devs.append(virtinst.VirtualCharDevice.get_dev_instance(conn, dev, char))

        for dev in devs:
            custom_dict = {}
            for key in paramdict.keys():
                if hasattr(dev, key):
                    custom_dict[key] = paramdict[key]
            self._testArgs(dev, virtinst.VirtualCharDevice, label,
                           manual_dict=custom_dict)

if __name__ == "__main__":
    unittest.main()
