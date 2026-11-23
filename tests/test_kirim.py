import io
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from monev.kirim import antrian, host


class TestProtokol(unittest.TestCase):
    def test_bolak_balik(self):
        buf = io.BytesIO()
        host.tulis_pesan(buf, {"type": "ambil", "teks": "uji ✓"})
        buf.seek(0)
        self.assertEqual(host.baca_pesan(buf), {"type": "ambil", "teks": "uji ✓"})

    def test_stream_kosong(self):
        self.assertIsNone(host.baca_pesan(io.BytesIO(b"")))


class TestAntrian(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"MONEV_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_ambil_sekali_saja(self):
        job = antrian.buat_job("isi", {"date": "2026-11-17"}, "uji")
        self.assertEqual(antrian.ambil_job()["id"], job["id"])
        self.assertIsNone(antrian.ambil_job())

    def test_hasil_sampai_ke_cli(self):
        job = antrian.buat_job("ping")
        antrian.ambil_job()
        antrian.tulis_hasil(job["id"], {"ok": True, "tahap": "ping"})
        self.assertEqual(antrian.tunggu_hasil(job["id"], 2)["tahap"], "ping")

    def test_kedaluwarsa_tidak_diambil(self):
        job = antrian.buat_job("isi", {"date": "2026-11-17"})
        self.assertIsNone(antrian.ambil_job(sekarang=time.time() + antrian.KEDALUWARSA_DTK + 1))
        self.assertEqual(antrian.tunggu_hasil(job["id"], 1)["tahap"], "kedaluwarsa")

    def test_batalkan_hanya_sebelum_diambil(self):
        a = antrian.buat_job("ping")
        self.assertTrue(antrian.batalkan(a["id"]))
        b = antrian.buat_job("ping")
        antrian.ambil_job()
        self.assertFalse(antrian.batalkan(b["id"]))

    def test_host_main(self):
        job = antrian.buat_job("ping")
        inp = io.BytesIO()
        host.tulis_pesan(inp, {"type": "ambil"})
        inp.seek(0)
        out = io.BytesIO()
        with mock.patch("sys.stdin", mock.Mock(buffer=inp)), mock.patch("sys.stdout", mock.Mock(buffer=out)):
            host.host_main()
        out.seek(0)
        self.assertEqual(host.baca_pesan(out)["job"]["id"], job["id"])

    def test_host_nilai_dari_config(self):
        def tanya(cfg_isi):
            f = os.path.join(self.tmp_nilai.name, "config.toml")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(cfg_isi)
            inp, out = io.BytesIO(), io.BytesIO()
            host.tulis_pesan(inp, {"type": "nilai"})
            inp.seek(0)
            with mock.patch.dict(os.environ, {"MONEV_CONFIG": f}), \
                    mock.patch("sys.stdin", mock.Mock(buffer=inp)), mock.patch("sys.stdout", mock.Mock(buffer=out)):
                host.host_main()
            out.seek(0)
            return host.baca_pesan(out)

        self.tmp_nilai = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_nilai.cleanup)
        r = tanya('[profil.nilai]\nsemboyan = "S"\npoin = ["Satu: terap satu", "Dua"]\n')
        self.assertEqual(r, {"ok": True, "nilai": {"semboyan": "S", "poin": [["Satu", "terap satu"], ["Dua", ""]]}})
        self.assertEqual(tanya("[profil]\n"), {"ok": True, "nilai": None})

    def test_host_pesan_bawaan_ditimpa_config(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        f = os.path.join(tmp.name, "config.toml")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write('[pesan.ingat.pertama]\njudul = "Jangan lupa laporan."\nsalah = "x"\n')
        inp, out = io.BytesIO(), io.BytesIO()
        host.tulis_pesan(inp, {"type": "pesan"})
        inp.seek(0)
        with mock.patch.dict(os.environ, {"MONEV_CONFIG": f}), \
                mock.patch("sys.stdin", mock.Mock(buffer=inp)), mock.patch("sys.stdout", mock.Mock(buffer=out)):
            host.host_main()
        out.seek(0)
        r = host.baca_pesan(out)
        self.assertTrue(r["ok"])
        self.assertEqual(r["pesan"]["ingat"]["pertama"]["judul"], "Jangan lupa laporan.")
        self.assertIn("{batas}", r["pesan"]["ingat"]["pertama"]["isi"])   # yang tidak ditimpa tetap bawaan
        self.assertEqual(r["asing"], ["pesan.ingat.pertama.salah"])

    def test_manifest_host(self):
        m = host.manifest_host("/x/monev-native-host")
        self.assertEqual(m["allowed_origins"], [f"chrome-extension://{host.EXTENSION_ID}/"])
        self.assertEqual(m["name"], host.HOST_NAME)


class TestDiagnosa(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prof = os.path.join(self.tmp.name, "google-chrome", "Default")
        os.makedirs(self.prof)
        with open(os.path.join(self.prof, "Preferences"), "w") as f:
            f.write("{}")
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.tmp.name})
        self.env.start()
        self.plat = mock.patch.object(host.sys, "platform", "linux")
        self.plat.start()
        self.jalan = mock.patch.object(host, "chrome_berjalan", return_value=True)
        self.jalan.start()

    def tearDown(self):
        for p in (self.jalan, self.plat, self.env):
            p.stop()
        self.tmp.cleanup()

    def test_belum_apa_apa(self):
        m = host.diagnosa()
        self.assertTrue(any("monev extension install" in x for x in m))
        self.assertTrue(any("Load unpacked" in x for x in m))

    def test_sisa_entri_kosong_setelah_remove(self):
        with open(os.path.join(self.prof, "Preferences"), "w") as f:
            f.write('{"extensions":{"settings":{"%s":{}}}}' % host.EXTENSION_ID)
        self.assertFalse(host.extension_terpasang())

    def test_siap(self):
        with open(os.path.join(self.prof, "Secure Preferences"), "w") as f:
            f.write('{"extensions":{"settings":{"%s":{"path":"/x/extension","location":4}}}}' % host.EXTENSION_ID)
        folder = os.path.join(self.tmp.name, "google-chrome", "NativeMessagingHosts")
        os.makedirs(folder)
        open(os.path.join(folder, host.HOST_NAME + ".json"), "w").close()
        self.assertEqual(host.diagnosa(), [])


class TestManifestExtension(unittest.TestCase):
    def test_id_cocok_dengan_key(self):
        import base64
        import hashlib

        man = json.loads((host.extension_dir() / "manifest.json").read_text())
        der = base64.b64decode(man["key"])
        ext_id = "".join("abcdefghijklmnop"[int(c, 16)] for c in hashlib.sha256(der).hexdigest()[:32])
        self.assertEqual(ext_id, host.EXTENSION_ID)
        # Host API hanya untuk chrome.cookies membaca tanggal habis sesi; panggilan API tetap dari dalam halaman Monev.
        self.assertEqual(man["host_permissions"], ["https://monev.maganghub.kemnaker.go.id/*",
                                                   "https://monev-api.maganghub.kemnaker.go.id/*"])
        self.assertIn("cookies", man["permissions"])


if __name__ == "__main__":
    unittest.main()
