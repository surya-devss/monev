// Dijalankan di halaman Monev (world MAIN) lewat chrome.scripting.executeScript.
// Langkah: docs/teknis/situs-monev.md bagian "Langkah mengisi form", tanpa AI.
// Tidak pernah mengembalikan token, cookie, kontak, atau koordinat.

// Ringkasan hari ini untuk popup dan pengingat: tanggal, sudah isi, libur, kehadiran, revisi mentor, identitas.
// Read-only; tanpa kontak dan tanpa koordinat (lokasi hanya ada/tidak). Bentuknya mengikuti collect_status di
// monev/portal/api.py.
async function monevRingkas() {
  if (location.host.includes("account.kemnaker.go.id")) return { ok: false, tahap: "login" };
  const token = sessionStorage.getItem("monev_access_token");
  if (!token) return { ok: false, tahap: "login" };
  const get = async (p) => {
    const r = await fetch("https://monev-api.maganghub.kemnaker.go.id/api/v1" + p,
      { credentials: "include", headers: { Authorization: "Bearer " + token } });
    if (!r.ok) throw new Error(p.split("?")[0] + " → HTTP " + r.status);
    return (await r.json()).data || {};
  };
  try {
    const [home, me] = await Promise.all([get("/users/me/home"), get("/users/me")]);
    const D = home.date, pid = me.id, mulai = (me.internship_start_date || "").slice(0, 10);
    const [att, logs] = await Promise.all([
      get(`/attendances?participant_id=${pid}&start_date=${D}&end_date=${D}`).catch(() => []),
      mulai ? get(`/daily-logs?participant_id=${pid}&start_date=${mulai}&end_date=${D}&limit=100`).catch(() => null) : null,
    ]);
    const a = (Array.isArray(att) && att[0]) || null;
    return {
      ok: true, tanggal: D, sudah_isi: !!home.has_attendance, aktif: !!home.active_internship,
      libur: !!(home.is_holiday || home.is_scheduled_off_day),
      kehadiran: a ? { status: a.status, persetujuan: a.approval_status, ada_lokasi: a.latitude != null } : null,
      perlu_revisi: Array.isArray(logs)
        ? logs.filter((l) => l.state === "NEEDS_REVISION").map((l) => ({ date: (l.date || "").slice(0, 10), catatan_mentor: l.reviewer_notes || "" }))
        : null,
      nama: (me.name || "").toLowerCase().replace(/(^|\s)\S/g, (c) => c.toUpperCase()), posisi: me.job_role || "", perusahaan: me.internship_company || "",
    };
  } catch (e) {
    return { ok: false, tahap: "api", pesan: String(e) };
  }
}

async function monevJalankan(job) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const API = "https://monev-api.maganghub.kemnaker.go.id/api/v1";
  const teks = (el) => (el && (el.innerText || el.textContent) || "").trim();
  const semua = (sel) => Array.from(document.querySelectorAll(sel));
  const tombol = (cocok) => semua("button, [role=button], a").find((b) => cocok(teks(b)));
  const tunggu = async (fn, ms, jeda = 300) => {
    const akhir = Date.now() + ms;
    while (Date.now() < akhir) {
      const v = fn();
      if (v) return v;
      await sleep(jeda);
    }
    return null;
  };
  const hasil = (ok, tahap, pesan, extra = {}) => ({ ok, tahap, pesan, ...extra });
  // Progres untuk popup: background membaca atribut ini dari DOM selagi fungsi ini berjalan.
  const langkah = (t) => { document.documentElement.dataset.monevLangkah = t; };
  langkah("buka");

  // executeScript hanya membawa isi fungsi ini ke halaman; semua fungsi bantu harus di dalamnya.
  // ---------------------------------------------------------------- bersama: izin & revisi

  // Isi textarea Vue/Vuetify: setter asli + event, tanpa event form menganggap kosong (uji #7).
  function monevIsi(el, nilai) {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    el.focus();
    setter.call(el, nilai);
    for (const ev of ["input", "change", "blur"]) el.dispatchEvent(new Event(ev, { bubbles: true }));
  }

  // Centang pernyataan → Simpan dan Kirim. Mengembalikan null bila berhasil diklik, atau objek hasil gagal.
  async function monevCentangKirim(u, extra) {
    const { semua, teks, tombol, tunggu, hasil, status } = u;
    const label = semua("label").find((l) => teks(l).startsWith("Saya menyatakan telah meninjau"));
    if (!label) return hasil(false, "centang", "Kotak pernyataan tidak ditemukan.", { status, ...extra });
    const cb = label.control || document.getElementById(label.htmlFor);
    u.langkah("kirim");
    if (!cb || !cb.checked) label.click();
    const kirim = await tunggu(() => {
      const b = tombol((t) => t.includes("Simpan dan Kirim"));
      return b && !b.disabled && b.getAttribute("aria-disabled") !== "true" ? b : null;
    }, 5000);
    if (!kirim) return hasil(false, "centang", "Tombol 'Simpan dan Kirim' tidak aktif.", { status, ...extra });
    kirim.click();
    u.langkah("verifikasi");
    return null;
  }

  async function monevGet(u, path) {
    const r = await fetch(u.API + path, { credentials: "include", headers: { Authorization: "Bearer " + u.token } });
    if (!r.ok) throw new Error(path.split("?")[0] + " → HTTP " + r.status);
    return (await r.json()).data;
  }

  // ---------------------------------------------------------------- izin (Tidak Hadir Dengan Keterangan)
  // Sumber bentuk form: bundle Monev (halaman riwayat): pilihan Kehadiran berupa v-select, alasan di textarea
  // "Tulis alasan tidak hadir…", izin tidak mengirim lokasi. Hanya untuk hari ini.

  async function monevIzin(job, home, u) {
    const { sleep, teks, semua, tombol, tunggu, hasil, status, langkah } = u;
    const IZIN = "Tidak Hadir Dengan Keterangan";
    if (home.date !== job.draft.date) {
      return hasil(false, "tanggal", `Izin hanya untuk hari ini. Draft ${job.draft.date}, Monev hari ini ${home.date}.`, { status });
    }
    if (home.has_attendance) return hasil(false, "sudah_isi", "Kehadiran hari ini sudah tercatat.", { status });
    if (status.libur) return hasil(false, "libur", "Hari ini libur; tidak perlu izin.", { status });

    const nanti = tombol((t) => t === "Nanti saja");
    if (nanti) { nanti.click(); await sleep(500); }

    // Buka form
    const kehadiran = () => semua(".v-select").find((el) => teks(el).includes("Kehadiran"));
    if (!kehadiran()) {
      const isi = tombol((t) => t.includes("Isi Laporan Hari Ini"));
      if (isi) isi.click();
    }
    const sel = await tunggu(kehadiran, 10000);
    if (!sel) return hasil(false, "form", "Pilihan Kehadiran tidak ditemukan (tampilan Monev mungkin berubah).", { status });

    // Pilih "Tidak Hadir Dengan Keterangan" lalu isi alasan. Di tab yang baru dimuat, Monev bisa mengatur ulang form
    // ke Hadir saat datanya selesai dimuat; karena itu diulang sampai 3 kali dan hasil akhirnya diperiksa.
    const ALASAN = "Tulis alasan tidak hadir";
    const pilihIzin = async () => {
      const k = kehadiran();
      if (!k) return false;
      if (teks(k).includes(IZIN)) return true;
      const bidang = k.querySelector(".v-field") || k;
      bidang.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      bidang.click();
      const opsi = await tunggu(() => semua(".v-overlay .v-list-item, [role=option]").find((o) => teks(o) === IZIN), 5000);
      if (!opsi) return false;
      opsi.click();
      await sleep(1000);
      return teks(kehadiran() || document.body).includes(IZIN);
    };
    const cekIzin = (el) => {
      const k = teks(kehadiran());
      if (!k.includes(IZIN) || k.includes("Tanpa Keterangan")) return "Kehadiran bukan izin";
      if (!el.isConnected) return "kolom alasan diganti halaman";
      if (el.value !== job.draft.leave_reason) return "isi alasan tidak sama dengan draft";
      // Baca status validasi dari class Vuetify, bukan teks pesan: di tab yang tidak terlihat, animasi hilangnya pesan
      // tertahan sehingga teks "Minimal 100 karakter" bisa tertinggal walau isian sudah valid.
      const input = el.closest(".v-input");
      return input && input.classList.contains("v-input--error") ? "form menolak alasan (kurang dari 100 karakter?)" : "";
    };
    langkah("isi");
    await sleep(2000);   // beri waktu data hari ini termuat sebelum form diubah
    let alasan = null, masalah = "belum dicoba";
    for (let coba = 0; coba < 3 && masalah; coba++) {
      if (!(await pilihIzin())) { masalah = `pilihan '${IZIN}' tidak bisa dipilih`; continue; }
      alasan = await tunggu(() => semua("textarea").find((t) => (t.placeholder || "").startsWith(ALASAN)), 5000);
      if (!alasan) { masalah = "kolom 'Alasan tidak hadir' tidak muncul"; continue; }
      monevIsi(alasan, job.draft.leave_reason);
      await sleep(1500);
      masalah = cekIzin(alasan);
    }
    if (masalah) return hasil(false, "isi", "Form izin belum siap (" + masalah + "). Tidak dikirim.", { status });
    const panjang = [alasan.value.length];

    if (job.mode === "uji") {
      return hasil(true, "siap_centang", "Form izin terisi. Mode uji: tidak dicentang, tidak dikirim.", { status, panjang });
    }
    const gagal = await monevCentangKirim(u, { panjang });
    if (gagal) return gagal;

    // Verifikasi lewat API: kehadiran hari ini tercatat ON_LEAVE. Jangan klik ulang.
    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      try {
        const h = await monevGet(u, "/users/me/home");
        if (h && h.has_attendance) return hasil(true, "terkirim", "Izin terkirim, menunggu persetujuan mentor.", { status, panjang });
      } catch (_) { /* coba lagi */ }
    }
    return hasil(false, "tidak_pasti", "Belum ada tanda terkirim setelah 30 detik. JANGAN kirim ulang; cek dengan `monev status`.",
      { status, panjang });
  }

  // ---------------------------------------------------------------- perbaikan laporan (revisi dari mentor)
  // Halaman /dashboard/riwayat?action=revision&date=D membuka panel "Perbaiki laporan" (Kehadiran terkunci, tiga
  // kolom berisi isi lama). Simpan dan Kirim → PUT /daily-logs/{id} dengan state REVISION_SUBMITTED. Tanpa lokasi.

  async function monevRevisi(job, u) {
    const { sleep, teks, semua, tunggu, hasil, status, langkah } = u;
    const D = job.draft.date;
    let me, log;
    try {
      me = await monevGet(u, "/users/me");
      const logs = await monevGet(u, `/daily-logs?participant_id=${me.id}&date=${D}&limit=10`);
      log = (logs || []).find((l) => (l.date || "").slice(0, 10) === D);
    } catch (e) {
      return hasil(false, "api", "Gagal membaca laporan " + D + ": " + e, { status });
    }
    if (!log) return hasil(false, "revisi", `Tidak ada laporan tanggal ${D}.`, { status });
    if (log.state !== "NEEDS_REVISION") {
      return hasil(false, "revisi", `Laporan ${D} tidak sedang diminta revisi (status ${log.state}).`, { status });
    }

    const PH = { activity_log: "Tulis uraian aktivitas", lesson_learned: "Tulis ilmu/pembelajaran", obstacles: "Tulis kendala/hambatan" };
    const cari = () => {
      if (!document.body.innerText.includes("Perbaiki laporan")) return null;
      const ta = semua("textarea"), out = {};
      for (const [k, ph] of Object.entries(PH)) out[k] = ta.find((t) => (t.placeholder || "").startsWith(ph));
      return Object.values(out).every(Boolean) ? out : null;
    };
    const ta = await tunggu(cari, 15000);
    if (!ta) return hasil(false, "form", "Panel 'Perbaiki laporan' tidak terbuka (tampilan Monev mungkin berubah).", { status });

    langkah("isi");
    for (const [k, el] of Object.entries(ta)) monevIsi(el, job.draft[k]);
    await sleep(800);
    const beda = Object.keys(PH).filter((k) => ta[k].value !== job.draft[k]);
    if (beda.length) return hasil(false, "isi", "Isi kolom tidak sama dengan draft: " + beda.join(", "), { status });
    const ditolak = Object.keys(PH).filter((k) => (ta[k].closest(".v-input") || document.body).classList.contains("v-input--error"));
    if (ditolak.length) return hasil(false, "validasi", "Form menolak kolom: " + ditolak.join(", "), { status });
    const panjang = Object.keys(PH).map((k) => ta[k].value.length);

    if (job.mode === "uji") {
      return hasil(true, "siap_centang", "Perbaikan terisi. Mode uji: tidak dicentang, tidak dikirim.", { status, panjang });
    }
    const gagal = await monevCentangKirim(u, { panjang });
    if (gagal) return gagal;

    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      try {
        const logs = await monevGet(u, `/daily-logs?participant_id=${me.id}&date=${D}&limit=10`);
        const l = (logs || []).find((x) => x.id === log.id);
        if (l && l.state === "REVISION_SUBMITTED") {
          return hasil(true, "terkirim", `Perbaikan laporan ${D} terkirim, menunggu persetujuan mentor.`, { status, panjang });
        }
      } catch (_) { /* coba lagi */ }
    }
    return hasil(false, "tidak_pasti", "Belum ada tanda terkirim setelah 30 detik. JANGAN kirim ulang; cek Riwayat di Monev.",
      { status, panjang });
  }

  // 1. Sesi
  if (location.host.includes("account.kemnaker.go.id")) {
    return hasil(false, "login", "Chrome ini belum login Monev. Login dulu di tab Monev, lalu ulangi.");
  }
  const token = sessionStorage.getItem("monev_access_token");
  if (!token) return hasil(false, "login", "Token sesi tidak ada. Buka Monev dan login dulu.");
  let home;
  try {
    const r = await fetch(API + "/users/me/home", {
      credentials: "include",
      headers: { Authorization: "Bearer " + token },
    });
    home = (await r.json()).data || {};
  } catch (e) {
    return hasil(false, "api", "Gagal membaca status Monev: " + e);
  }
  const status = {
    tanggal: home.date, sudah_isi: !!home.has_attendance,
    libur: !!(home.is_holiday || home.is_scheduled_off_day), magang_aktif: !!home.active_internship,
  };
  if (job.type === "ping") return hasil(true, "ping", "Terhubung ke Monev.", { status });
  if (job.draft.revisi) return monevRevisi(job, { API, token, sleep, teks, semua, tombol, tunggu, hasil, status, langkah });
  if (job.draft.status === "ON_LEAVE") return monevIzin(job, home, { API, token, sleep, teks, semua, tombol, tunggu, hasil, status, langkah });

  // 2. Syarat sebelum mengisi (laporan hadir)
  if (home.date !== job.draft.date) {
    return hasil(false, "tanggal", `Draft untuk ${job.draft.date}, Monev hari ini ${home.date}.`, { status });
  }
  if (home.has_attendance) return hasil(false, "sudah_isi", "Laporan hari ini sudah terkirim.", { status });
  if (status.libur) return hasil(false, "libur", "Hari ini libur; tidak diisi.", { status });

  // 3. Pop-up notifikasi
  const nanti = tombol((t) => t === "Nanti saja");
  if (nanti) { nanti.click(); await sleep(500); }

  // 4. Buka form
  const PH = {
    activity_log: "Tulis uraian aktivitas",
    lesson_learned: "Tulis ilmu/pembelajaran",
    obstacles: "Tulis kendala/hambatan",
  };
  const cariTextarea = () => {
    const ta = semua("textarea");
    const out = {};
    for (const [k, ph] of Object.entries(PH)) out[k] = ta.find((t) => (t.placeholder || "").startsWith(ph));
    return Object.values(out).every(Boolean) ? out : null;
  };
  let ta = cariTextarea();
  if (!ta) {
    const isi = tombol((t) => t.includes("Isi Laporan Hari Ini"));
    if (isi) isi.click();
    ta = await tunggu(cariTextarea, 10000);
  }
  if (!ta) return hasil(false, "form", "Form laporan tidak ditemukan (tampilan Monev mungkin berubah).", { status });

  // 5. Kehadiran = Hadir (teks persis "Hadir", bukan "Tidak Hadir …")
  const labelHadir = semua("label").find((l) => teks(l) === "Hadir");
  if (labelHadir) {
    const input = labelHadir.control || document.getElementById(labelHadir.htmlFor);
    if (!input || !input.checked) { labelHadir.click(); await sleep(300); }
  }

  langkah("isi");
  // 6. Isi + picu event (tanpa event, form menganggap kosong; uji #7)
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  for (const [k, el] of Object.entries(ta)) {
    el.focus();
    setter.call(el, job.draft[k]);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }
  await sleep(800);

  // 7. Periksa isi == draft, tidak ada pesan validasi
  const beda = Object.keys(PH).filter((k) => ta[k].value !== job.draft[k]);
  if (beda.length) return hasil(false, "isi", "Isi kolom tidak sama dengan draft: " + beda.join(", "), { status });
  const pesanValidasi = semua(".v-messages__message").map(teks).filter(Boolean);
  if (pesanValidasi.length) return hasil(false, "validasi", "Form menolak: " + pesanValidasi.join("; "), { status });
  const panjang = Object.keys(PH).map((k) => ta[k].value.length);

  langkah("lokasi");
  // 8. Lokasi asli dari Chrome ini
  const adaLokasi = () => document.body.innerText.includes("Koordinat ditemukan");
  if (!adaLokasi()) {
    const tambah = tombol((t) => t.includes("Tambahkan lokasi"));
    if (tambah) tambah.click();
  }
  if (!(await tunggu(adaLokasi, 20000, 500))) {
    return hasil(false, "lokasi",
      "Lokasi belum didapat. Klik 'Izinkan' pada pop-up lokasi Chrome (sekali), lalu ulangi. Tidak dikirim.",
      { status, panjang });
  }

  if (job.mode === "uji") {
    return hasil(true, "siap_centang", "Form terisi dan lokasi ada. Mode uji: tidak dicentang, tidak dikirim.",
      { status, panjang });
  }

  langkah("kirim");
  // 9. Centang pernyataan → Simpan dan Kirim
  const labelNyatakan = semua("label").find((l) => teks(l).startsWith("Saya menyatakan telah meninjau"));
  if (!labelNyatakan) return hasil(false, "centang", "Kotak pernyataan tidak ditemukan.", { status, panjang });
  const cb = labelNyatakan.control || document.getElementById(labelNyatakan.htmlFor);
  if (!cb || !cb.checked) labelNyatakan.click();
  const kirim = await tunggu(() => {
    const b = tombol((t) => t.includes("Simpan dan Kirim"));
    return b && !b.disabled && b.getAttribute("aria-disabled") !== "true" ? b : null;
  }, 5000);
  if (!kirim) return hasil(false, "centang", "Tombol 'Simpan dan Kirim' tidak aktif.", { status, panjang });
  kirim.click();

  langkah("verifikasi");
  // 10. Tunggu; jangan klik ulang (uji #9)
  const terkirim = await tunggu(() => document.body.innerText.includes("Menunggu Persetujuan"), 30000, 1000);
  return terkirim
    ? hasil(true, "terkirim", "Laporan terkirim, menunggu persetujuan mentor.", { status, panjang })
    : hasil(false, "tidak_pasti",
      "Belum ada tanda terkirim setelah 30 detik. JANGAN kirim ulang; cek dengan `monev status`.",
      { status, panjang });
}
