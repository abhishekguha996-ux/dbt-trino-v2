import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from archive_utils import safe_extract
from lab_control import validate
from driver_smoke import CASES


class ArchiveTests(unittest.TestCase):
    def archive(self, root, entries):
        archive = root / "fixture.tar.gz"
        with tarfile.open(archive,"w:gz") as tar:
            for name, kind, content in entries:
                item = tarfile.TarInfo(name)
                if kind == "link":
                    item.type = tarfile.SYMTYPE
                    item.linkname = content
                    tar.addfile(item)
                else:
                    data = content.encode()
                    item.size = len(data)
                    tar.addfile(item,io.BytesIO(data))
        return archive

    def test_regular_and_internal_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=self.archive(root,[("src/file","file","hello"),("src/sub/link","link","../file")])
            safe_extract(archive,root/"out")
            self.assertEqual((root/"out/src/sub/link").read_text(),"hello")

    def test_unsafe_archives_rejected_before_writing(self):
        cases=[[("../escape","file","x")],[("/escape","file","x")],
               [("src/link","link","../../escape")],[("src/link","link","/escape")],
               [("src/link","link","other"),("src/link/child","file","x")],
               [("a","file","x"),("a","file","y")],
               [("a","link","b"),("b","link","a")]]
        for entries in cases:
            with self.subTest(entries=entries),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                archive=self.archive(root,entries)
                with self.assertRaises(ValueError): safe_extract(archive,root/"out")
                self.assertFalse((root/"out").exists())

    def test_budget_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=self.archive(root,[("file","file","abc")])
            with self.assertRaises(ValueError): safe_extract(archive,root/"out",max_bytes=2)
            (root/"out").mkdir()
            with self.assertRaises(ValueError): safe_extract(archive,root/"out")


class ConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/"reports/sandbox-review.json").read_text())["configuration"]

    def test_current_configuration(self):
        validate(self.config)

    def test_reject_unsafe_runtime_changes(self):
        changes=[("ports",["8080:8080"]),("privileged",True),("user","0:0"),
                 ("read_only",False),("cap_add",["SYS_ADMIN"]),("network_mode","host"),
                 ("mem_limit","17179869184"),("environment",{"AWS_PROFILE":"default"}),
                 ("volumes",[{"type":"bind","source":"/Users","target":"/workspace"}])]
        for key,value in changes:
            with self.subTest(setting=key):
                config=copy.deepcopy(self.config)
                config["services"]["runner"][key]=value
                with self.assertRaises(ValueError): validate(config)

    def test_reject_external_network_and_bind_volume(self):
        config=copy.deepcopy(self.config)
        config["networks"]["test"]["driver_opts"]={}
        with self.assertRaises(ValueError): validate(config)
        config=copy.deepcopy(self.config)
        config["volumes"]["work"]["driver_opts"]={"device":"/Users","o":"bind","type":"none"}
        with self.assertRaises(ValueError): validate(config)


class FixtureTests(unittest.TestCase):
    def test_independent_join_oracle(self):
        left=[(1,10),(2,20),(2,30),(None,40),(4,None)]
        right=[(2,3),(2,4),(3,5),(None,6)]
        pairs=[(a,b) for a in left for b in right if a[0] is not None and a[0]==b[0]]
        missing_left=[(a,None) for a in left if not any(a==x for x,_ in pairs)]
        missing_right=[(None,b) for b in right if not any(b==y for _,y in pairs)]
        expected={name:rows for name,_,rows in CASES}
        for name,rows in [("inner_duplicate_keys",pairs),("left_unmatched_and_nulls",pairs+missing_left),
                          ("right_unmatched_and_nulls",pairs+missing_right),("full_outer",pairs+missing_left+missing_right)]:
            actual=(len(rows),sum(a[1] for a,_ in rows if a and a[1] is not None),
                    sum(b[1] for _,b in rows if b and b[1] is not None))
            self.assertEqual([actual],expected[name])


if __name__ == "__main__":
    unittest.main()
