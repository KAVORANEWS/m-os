"""Unit tests for mos.sysinfo parsers (no Qt, no root required)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "applications" / "python"))

from mos import sysinfo  # noqa: E402


class OsReleaseTest(unittest.TestCase):
    def test_parse_quotes_and_comments(self):
        text = '# comment\nNAME="M OS"\nID=mos\nPRETTY_NAME=\'M OS 0.1\'\n\nBAD LINE\n'
        data = sysinfo.parse_os_release(text)
        self.assertEqual(data["NAME"], "M OS")
        self.assertEqual(data["ID"], "mos")
        self.assertEqual(data["PRETTY_NAME"], "M OS 0.1")
        self.assertNotIn("BAD LINE", data)

    def test_shipped_os_release_is_valid(self):
        path = Path(__file__).resolve().parents[2] / "packages/mos-branding/files/usr/lib/os-release"
        data = sysinfo.parse_os_release(path.read_text())
        for key in ("NAME", "ID", "ID_LIKE", "VERSION_ID", "PRETTY_NAME", "HOME_URL"):
            self.assertIn(key, data)
        self.assertEqual(data["ID_LIKE"], "debian")


class MemoryTest(unittest.TestCase):
    SAMPLE = "MemTotal:        8000000 kB\nMemFree:  1000000 kB\nMemAvailable:    6000000 kB\n" \
             "SwapTotal: 4000000 kB\nSwapFree: 3000000 kB\nHugePages_Total: 0\n"

    def test_parse_and_state(self):
        info = sysinfo.parse_meminfo(self.SAMPLE)
        self.assertEqual(info["MemTotal"], 8000000 * 1024)
        self.assertEqual(info["HugePages_Total"], 0)
        state = sysinfo.memory_state(info)
        self.assertAlmostEqual(state.percent, 25.0)
        self.assertEqual(state.swap_used, 1000000 * 1024)


class CpuTest(unittest.TestCase):
    def test_proc_stat_and_percent(self):
        a = sysinfo.parse_proc_stat("cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0 0 0\nintr 1\n")
        b = sysinfo.parse_proc_stat("cpu  150 0 150 900 0 0 0 0 0 0\ncpu0 75 0 75 450 0 0 0 0 0 0\n")
        self.assertEqual(set(a), {"cpu", "cpu0"})
        self.assertAlmostEqual(sysinfo.cpu_percent(a["cpu"], b["cpu"]), 50.0)
        self.assertEqual(sysinfo.cpu_percent(a["cpu"], a["cpu"]), 0.0)

    def test_cpuinfo_i5_6500(self):
        block = ("processor : {n}\nmodel name : Intel(R) Core(TM) i5-6500 CPU @ 3.20GHz\n"
                 "physical id : 0\ncpu cores : 4\n\n")
        info = sysinfo.parse_cpuinfo("".join(block.format(n=i) for i in range(4)))
        self.assertEqual(info.model, "Intel(R) Core(TM) i5-6500 CPU @ 3.20GHz")
        self.assertEqual((info.sockets, info.cores, info.threads), (1, 4, 4))


class NetworkStorageTest(unittest.TestCase):
    def test_net_dev(self):
        text = ("Inter-|   Receive |  Transmit\n face |bytes packets errs drop fifo frame compressed multicast|bytes\n"
                "    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0\n"
                "  eth0: 2000 10 0 0 0 0 0 0 3000 12 0 0 0 0 0 0\n")
        self.assertEqual(sysinfo.parse_net_dev(text), {"eth0": (2000, 3000)})

    def test_mounts_filters_virtual(self):
        text = ("proc /proc proc rw 0 0\n/dev/sda2 / ext4 rw 0 0\n/dev/sda1 /boot/efi vfat rw 0 0\n"
                "tmpfs /run tmpfs rw 0 0\n/dev/sda2 /var/snap ext4 rw 0 0\n/dev/sdb1 /media/My\\040Disk ntfs3 rw 0 0\n")
        mounts = sysinfo.parse_mounts(text)
        self.assertEqual([m[1] for m in mounts], ["/", "/boot/efi", "/media/My Disk"])

    def test_lsblk(self):
        text = ('{"blockdevices":[{"name":"sda","size":256060514304,"model":"Samsung SSD 860 ","type":"disk",'
                '"rota":false,"tran":"sata","rm":false},{"name":"sr0","size":1073741312,"model":"DVD",'
                '"type":"rom","rota":true,"tran":"sata","rm":true}]}')
        devs = sysinfo.parse_lsblk_json(text)
        self.assertEqual(len(devs), 1)
        self.assertEqual(devs[0].model, "Samsung SSD 860")
        self.assertFalse(devs[0].rotational)
        self.assertEqual(sysinfo.parse_lsblk_json("not json"), [])

    def test_lspci(self):
        text = ('00:02.0 "VGA compatible controller" "Intel Corporation" "HD Graphics 530" -r06 "Dell" "Device 06b9"\n'
                '00:1f.3 "Audio device" "Intel Corporation" "100 Series HD Audio" "Dell" "x"\n'
                '01:00.0 "3D controller" "NVIDIA Corporation" "GP107M" "x" "y"\n')
        self.assertEqual(sysinfo.parse_lspci_mm(text),
                         ["Intel Corporation HD Graphics 530", "NVIDIA Corporation GP107M"])


class ProcessTest(unittest.TestCase):
    def test_pid_stat_with_spaces_in_name(self):
        text = "1234 (Web Content (x)) S 1 1234 1234 0 -1 4194560 100 0 0 0 250 50 0 0 20 0 30 0 100 1000 200"
        comm, state, ticks = sysinfo.parse_proc_pid_stat(text)
        self.assertEqual(comm, "Web Content (x)")
        self.assertEqual(state, "S")
        self.assertEqual(ticks, 300)

    def test_list_processes_includes_self(self):
        import os
        procs = sysinfo.list_processes()
        self.assertIn(os.getpid(), [p.pid for p in procs])


class HumanBytesTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(sysinfo.human_bytes(512), "512 B")
        self.assertEqual(sysinfo.human_bytes(8 * 1024 ** 3), "8.0 GiB")
        self.assertEqual(sysinfo.human_bytes(256_000_000_000, binary=False), "256.0 GB")
        self.assertEqual(sysinfo.human_bytes(None), "—")


if __name__ == "__main__":
    unittest.main()
