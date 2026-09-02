#!/usr/bin/env python
"""RAID output parsers. Run: python -m diskreporter.tests"""
from __future__ import print_function

from diskreporter.raid import parse_arcconf, parse_mdstat

ARCCONF_OK = """
Controllers found: 1
Logical device number 0
   Logical device name                      : Data
   RAID level                               : 5
   Status of logical device                 : Optimal
   Size                                     : 3814697 MB
"""

ARCCONF_BAD = """
Logical device number 0
   Logical device name                      : Data
   RAID level                               : 5
   Status of logical device                 : Degraded
   Size                                     : 3814697 MB
Logical device number 1
   Logical device name                      : Spare
   RAID level                               : 1
   Status of logical device                 : Optimal
   Size                                     : 100 GB
"""

MDSTAT_OK = """Personalities : [raid1]
md0 : active raid1 sda1[0] sdb1[1]
      123456 blocks super 1.2 [2/2] [UU]
unused devices: <none>
"""

MDSTAT_BAD = """Personalities : [raid1]
md0 : active raid1 sda1[0] sdb1[2](F)
      123456 blocks super 1.2 [2/1] [U_]
      [====>....]  recovery = 40.0%
unused devices: <none>
"""


def main():
    ok = parse_arcconf(ARCCONF_OK)
    assert ok["ok"] and ok["status"] == "Optimal" and len(ok["arrays"]) == 1, ok
    bad = parse_arcconf(ARCCONF_BAD)
    assert (not bad["ok"]) and ("Degraded" in bad["status"]) and len(bad["arrays"]) == 2, bad
    mdok = parse_mdstat(MDSTAT_OK)
    assert mdok["ok"], mdok
    mdbad = parse_mdstat(MDSTAT_BAD)
    assert not mdbad["ok"], mdbad
    print("raid parser tests ok")


if __name__ == "__main__":
    main()
