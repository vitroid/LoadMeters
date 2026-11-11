#!/usr/bin/env python
"""RAID output parsers. Run: python -m diskreporter.tests"""
from __future__ import print_function

from diskreporter.raid import (
    merge_arcconf_health,
    parse_arcconf,
    parse_arcconf_ad,
    parse_arcconf_pd,
    parse_mdstat,
)

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

ARCCONF_PD = """Controllers found: 1
----------------------------------------------------------------------
Physical Device information
----------------------------------------------------------------------
      Device #0
         Device is a Hard drive
         State                              : Online
         Reported Location                  : Enclosure 0, Slot 0(Connector 0:CN0)
         Vendor                             : HGST
         Model                              : HUH721010AL5200
         Serial number                      : 7JJAAAA
         Total Size                         : 9537536 MB
         S.M.A.R.T.                         : No
         S.M.A.R.T. warnings                : 0
         Temperature                        : 38 C/ 100 F
      ----------------------------------------------------------------
      Device Phy Information
      ----------------------------------------------------------------
         Phy #0
            Negotiated Physical Link Rate   : 12 Gbps
      ----------------------------------------------------------------
      Runtime Error Counters
      ----------------------------------------------------------------
         Hardware Error Count               : 0
         Medium Error Count                 : 3
      Device #1
         Device is a Hard drive
         State                              : Failed
         Reported Location                  : Connector 1, Device 2
         Model                              : ST10000NM0016
         S.M.A.R.T.                         : Yes
         S.M.A.R.T. warnings                : 2
         Temperature                        : 45 C/ 113 F
      Device #2
         Device is an Enclosure services device
         Reported Location                  : Enclosure 0
"""

ARCCONF_AD = """Controllers found: 1
----------------------------------------------------------------------
Controller information
----------------------------------------------------------------------
   Controller Status                        : Optimal
   Controller Model                         : Adaptec ASR8805
   Temperature                              : 52 C/ 125 F (Normal)
   Defunct disk drive count                 : 0
   --------------------------------------------------------
   Controller ZMM Information
   --------------------------------------------------------
   Status                                   : ZMM Optimal
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

    disks = parse_arcconf_pd(ARCCONF_PD)
    assert len(disks) == 2, disks
    assert disks[0]["slot"] == "0" and disks[0]["ok"] and disks[0]["temperature"] == 38, disks[0]
    assert disks[0]["errors"] == {"Medium Error": 3} and not disks[0]["warnings"], disks[0]
    assert disks[1]["slot"] == "1:2" and not disks[1]["ok"] and len(disks[1]["warnings"]) == 2, disks[1]
    ctrl = parse_arcconf_ad(ARCCONF_AD)
    assert ctrl["ok"] and ctrl["temperature"] == 52 and ctrl["backup"] == "ZMM Optimal", ctrl
    assert ctrl["defunct"] == 0 and not ctrl["temperature_abnormal"], ctrl
    merged = merge_arcconf_health(parse_arcconf(ARCCONF_OK), disks, ctrl)
    assert (not merged["ok"]) and "slot 1:2 Failed" in merged["status"], merged
    assert len(merged["warnings"]) == 2, merged
    healthy = merge_arcconf_health(parse_arcconf(ARCCONF_OK), disks[:1], ctrl)
    assert healthy["ok"] and healthy["status"] == "Optimal", healthy
    assert parse_arcconf_ad("") is None
    print("raid parser tests ok")


if __name__ == "__main__":
    main()
