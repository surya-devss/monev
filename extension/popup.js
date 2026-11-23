// Popup: status hari ini, progres kiriman dari CLI, pengiriman terakhir, dan kesehatan koneksi.
// Semua tampil dari data tersimpan dulu, lalu diperbarui di latar belakang dengan batas waktu (uji #29: popup
// pernah menggantung saat menunggu status).
const $ = (id) => document.getElementById(id);
const BATAS = "23.59";
const HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const tglPendek = (iso) => { const [, m, d] = iso.split("-").map(Number); return `${d} ${BULAN[m - 1]}`; };
const tglHari = (iso) => `${HARI[new Date(iso + "T00:00:00").getDay()]}, ${tglPendek(iso)}`;
const jam = (ms) => new Date(ms).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }).replace(":", ".");
const JENIS = { hadir: "Laporan hadir", izin: "Izin", revisi: "Perbaikan laporan", ping: "Cek koneksi" };
const MENTOR = { SUBMITTED: "menunggu persetujuan", APPROVED: "sudah disetujui", REJECTED: "ditolak" };
const UMUR_STATUS = 5 * 60 * 1000;   // status lebih tua dari ini diperbarui otomatis saat popup dibuka

let bantu = false, memuat = false;

function kirimPesan(msg, ms = 8000) {
  return Promise.race([
    chrome.runtime.sendMessage(msg),
    new Promise((r) => setTimeout(() => r({ ok: false, tahap: "timeout", pesan: "Tidak ada jawaban (timeout)." }), ms)),
  ]);
}

// Pembuat elemen kecil; teks selalu lewat textContent (data Monev tidak pernah jadi HTML).
function el(tag, attr = {}, ...anak) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attr)) {
    if (k === "on") e.addEventListener("click", v);
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v);
  }
  for (const a of anak.flat()) if (a !== null && a !== undefined && a !== false) e.append(a);
  return e;
}
const titik = (kelas, besar) => el("span", { class: `titik ${kelas}${besar ? " besar" : ""}`, "aria-hidden": "true" });
const kode = (t) => el("code", {}, t);

// ---------------------------------------------------------------- tampilan

function viewAwal(d) {
  const cli = d.host && d.host.ok, login = d.sesi && d.sesi.ok;
  const siap = cli && login;
  const langkah = [
    [true, "Extension terpasang di Chrome", null],
    [cli, "Sambungkan ke CLI", el("div", { class: "redup" }, "Jalankan di terminal ", kode("monev extension install"))],
    [login, "Login Monev di Chrome ini", el("div", {}, el("button", { class: "kedua", on: () => buka("/dashboard") }, "Buka Monev"))],
    [siap, "Cek koneksi", el("div", { class: "redup" }, kode("monev kirim --ping"))],
  ];
  let perluDitandai = false;
  const items = langkah.map(([ok, judul, rinci], i) => {
    const kelas = ok ? "selesai" : !perluDitandai ? "perlu" : "";
    if (!ok) perluDitandai = true;
    return el("li", {}, el("span", { class: `bulat ${kelas}`, "aria-hidden": "true" }, ok ? "✓" : String(i + 1)),
      el("div", {}, el("div", { style: ok ? "" : "font-weight:600" }, judul), rinci && !ok ? rinci : null));
  });
  return el("section", {},
    el("div", { class: "judul" }, siap ? "Cara pakai" : "Belum siap dipakai"),
    el("div", { class: "redup", style: "line-height:1.5" },
      "Tulis draft lewat ", kode("/monev"), " atau ", kode("monev draft"),
      ". Setelah kamu menyetujuinya di chat atau terminal, extension ini mengisi form Monev di Chrome kamu dan mengirimnya, supaya lokasi yang terkirim asli."),
    el("ol", { class: "langkah" }, items),
    el("div", { class: "redup kecil" }, "Panduan lengkap ada di ", kode("docs/panduan/pasang.md"), " di repo monev."));
}

function viewBerjalan(b) {
  const urutan = b.jenis === "hadir"
    ? [["buka", "Membuka form Monev"], ["isi", "Mengisi 3 kolom"], ["lokasi", "Mengecek lokasi asli"], ["kirim", "Centang pernyataan dan kirim"], ["verifikasi", "Memastikan laporan masuk"]]
    : [["buka", b.jenis === "revisi" ? "Membuka panel Perbaiki laporan" : "Membuka form Monev"],
       ["isi", b.jenis === "izin" ? "Mengisi alasan izin" : "Mengisi 3 kolom"], ["kirim", "Centang pernyataan dan kirim"], ["verifikasi", "Memastikan laporan masuk"]];
  const daftar = b.mode === "uji" ? urutan.filter(([k]) => k !== "kirim" && k !== "verifikasi") : urutan;
  const posisi = Math.max(0, daftar.findIndex(([k]) => k === b.langkah));
  return el("section", {},
    el("div", { class: "baris-atas" }, el("span", { class: "label" }, b.mode === "uji" ? "Mode uji" : "Sedang mengirim"),
      el("span", { class: "redup kecil" }, `dari CLI · ${jam(b.mulai)}`)),
    el("div", { class: "judul" }, `${JENIS[b.jenis] || "Laporan"}, ${tglHari(b.tanggal)}`),
    el("ol", { class: "langkah" }, daftar.map(([, teks], i) =>
      el("li", { class: i === posisi ? "aktif" : i > posisi ? "nanti" : "" },
        el("span", { class: `bulat ${i < posisi ? "selesai" : i === posisi ? "jalan" : ""}`, "aria-hidden": "true" }, i < posisi ? "✓" : ""),
        teks))),
    el("div", { class: "catatan redup kecil" },
      b.mode === "uji" ? "Mode uji, form diisi tapi tidak dikirim. " : "", "Jangan tutup tab Monev sampai selesai. Hasilnya juga muncul di terminal."));
}

function jamBerikut(a) {
  if (!a || !a.aktif || !a.ingat || !a.ingat.nyala) return "mati";
  const kini = new Date().toTimeString().slice(0, 5);
  const j = (a.ingat.jam || []).filter((x) => /^\d\d:\d\d$/.test(x)).sort().find((x) => x > kini);
  return j ? j.replace(":", ".") : "tidak ada lagi hari ini";
}

function viewStatus(d) {
  const r = d.ringkas;
  const bagian = [];
  if (!r) {
    bagian.push(el("section", {},
      el("div", { class: "judul" }, titik("", true), "Status belum terbaca"),
      el("div", { class: "redup" }, memuat ? "Membaca status dari Monev…" : "Buka Monev sekali di Chrome ini, lalu tekan muat ulang."),
      el("div", { class: "tombol" }, el("button", { class: "utama", on: () => buka("/dashboard") }, "Buka Monev"))));
    return bagian;
  }
  const kepala = el("div", { class: "baris-atas" }, el("span", { class: "label" }, "Hari ini"),
    el("span", { class: "redup kecil" }, `${tglHari(r.tanggal)} · ${r.libur ? "libur" : "hari kerja"}`));
  const kaki = el("div", { class: "redup kecil" }, memuat ? "Memperbarui…" : `Diperbarui ${jam(r.at)}`);
  const k = r.kehadiran || {};
  if (!r.aktif) {
    bagian.push(el("section", {}, kepala, el("div", { class: "judul" }, titik("", true), "Magang tidak aktif"), kaki));
  } else if (r.libur) {
    bagian.push(el("section", {}, kepala, el("div", { class: "judul" }, titik("ok", true), "Hari ini libur"),
      el("div", { class: "redup" }, "Tidak wajib mengisi laporan."), kaki));
  } else if (r.sudah_isi) {
    const hadir = { PRESENT: "hadir", ON_LEAVE: "izin" }[k.status] || k.status || "-";
    bagian.push(el("section", {}, kepala, el("div", { class: "judul" }, titik("ok", true), "Laporan sudah terkirim"),
      el("div", { class: "rincian" },
        el("div", {}, "Kehadiran"), el("div", {}, k.status === "PRESENT" ? `${hadir}, ${k.ada_lokasi ? "lokasi ikut terkirim" : "lokasi tidak ikut"}` : hadir),
        el("div", {}, "Mentor"), el("div", {}, MENTOR[k.persetujuan] || "belum terbaca")),
      kaki));
  } else {
    const sisa = Math.max(1, 24 - new Date().getHours());
    const rev = r.perlu_revisi ? (r.perlu_revisi.length ? r.perlu_revisi.map((x) => tglPendek(x.date)).join(", ") : "tidak ada") : "belum terbaca";
    bagian.push(el("section", {}, kepala, el("div", { class: "judul" }, titik("waspada", true), "Laporan belum diisi"),
      el("div", { class: "rincian" },
        el("div", {}, "Batas kirim"), el("div", {}, `${BATAS} WIB (sisa ${sisa} jam)`),
        el("div", {}, "Revisi mentor"), el("div", {}, rev),
        el("div", {}, "Pengingat berikut"), el("div", {}, jamBerikut(d.aturan))),
      el("div", { class: "tombol" }, el("button", { class: "utama", on: () => buka("/dashboard/riwayat?action=today") }, "Buka form Monev")),
      el("div", { class: "redup kecil" }, "Tulis draft lewat ", kode("/monev"), " atau ", kode("monev draft"), ". Extension mengirim setelah kamu setuju."),
      kaki));
  }
  const revisi = (r.perlu_revisi || [])[0];
  if (revisi) {
    const lain = r.perlu_revisi.length - 1;
    bagian.push(el("section", { class: "revisi" },
      el("div", { class: "judul" }, "Mentor minta revisi laporan " + tglPendek(revisi.date) + (lain > 0 ? ` (+${lain} lagi)` : "")),
      el("blockquote", {}, revisi.catatan_mentor || "Tanpa catatan."),
      el("div", { class: "waspada kecil" }, "Perbaiki dari laptop dengan ", kode("/monev revisi"), "."),
      el("div", { style: "display:flex;justify-content:flex-end" },
        el("button", { class: "kedua", on: () => buka(`/dashboard/riwayat?action=revision&date=${encodeURIComponent(revisi.date)}`) }, "Lihat di Riwayat"))));
  }
  return bagian;
}

function viewTerakhir(t) {
  if (!t || t.jenis === "ping" || !t.tanggal) return null;
  const h = t.hasil || {};
  const [kelas, teks] = h.tahap === "terkirim" ? ["ok", "terkirim"] : h.tahap === "siap_centang" ? ["redup", "uji, tidak dikirim"]
    : h.tahap === "tidak_pasti" ? ["waspada", "belum pasti masuk"] : ["bahaya", "gagal"];
  return el("section", { style: "gap:6px;border-bottom:0" },
    el("span", { class: "label" }, "Pengiriman terakhir"),
    el("div", { class: "baris-atas" }, el("span", {}, `${tglHari(t.tanggal)} · ${(JENIS[t.jenis] || "").toLowerCase()}`),
      el("span", { class: kelas }, `${teks} · ${jam(t.at)}`)),
    !h.ok && h.pesan ? el("div", { class: "redup kecil" }, h.pesan) : null);
}

function viewSehat(d) {
  const cli = !d.host ? ["", "CLI belum dicek"] : d.host.ok ? ["ok", "CLI terhubung"] : ["bahaya", "CLI tidak terhubung"];
  const sisa = d.sesi && d.sesi.sampai ? Math.floor((d.sesi.sampai - Date.now()) / 86400000) : null;
  const sampai = d.sesi && d.sesi.sampai ? ` s.d. ${new Date(d.sesi.sampai).getDate()} ${BULAN[new Date(d.sesi.sampai).getMonth()]}` : "";
  const sesi = !d.sesi ? ["", "Login Monev belum dicek"] : !d.sesi.ok ? ["bahaya", "Belum login Monev"]
    : sisa !== null && sisa <= 3 ? ["waspada", `Login Monev${sampai}`] : ["ok", `Login Monev${sampai}`];
  const a = d.aturan;
  const n = a && a.aktif ? (a.pagi.nyala ? 1 : 0) + (a.fokus.nyala ? 1 : 0) + (a.ingat.nyala ? (a.ingat.jam || []).filter(Boolean).length : 0) : 0;
  const ingat = !a ? ["", "Pengingat belum dicek"] : n ? ["ok", `Pengingat ${n} jadwal`] : ["", "Pengingat mati"];
  return [cli, sesi, ingat].map(([k, t]) => el("span", {}, titik(k), t));
}

// ---------------------------------------------------------------- muat & gambar

async function data() {
  const [lok, ses] = await Promise.all([
    chrome.storage.local.get(["ringkas", "host", "sesi", "terakhir"]),
    chrome.storage.session.get("berjalan"),
  ]);
  return { ...lok, ...ses, aturan: gambar.aturan };
}

async function gambar() {
  const d = await data();
  const r = d.ringkas;
  $("nama").textContent = (r && r.nama) || "Monev Kirim";
  $("posisi").textContent = r ? [r.posisi, r.perusahaan].filter(Boolean).join(" · ") : "Pengantar laporan dari CLI monev";
  const belumSiap = !d.host || !d.host.ok;
  const isi = bantu || (belumSiap && !d.berjalan) ? [viewAwal(d)]
    : d.berjalan ? [viewBerjalan(d.berjalan)]
    : [...viewStatus(d), viewTerakhir(d.terakhir)];
  $("isi").replaceChildren(...isi.filter(Boolean));
  $("sehat").replaceChildren(...viewSehat(d));
  $("bSegar").disabled = memuat;
  $("bBantu").setAttribute("aria-pressed", String(bantu));
}

async function buka(path) {
  await kirimPesan({ cmd: "buka", path });
  window.close();
}

async function segarkan(bolehBuka) {
  memuat = true;
  await gambar();
  await kirimPesan({ cmd: "segarkan", bolehBuka }, 20000);
  memuat = false;
  await gambar();
}

$("bSegar").addEventListener("click", () => segarkan(true));
$("bBantu").addEventListener("click", () => { bantu = !bantu; gambar(); });
$("bAtur").addEventListener("click", () => chrome.runtime.openOptionsPage());
chrome.storage.onChanged.addListener(() => gambar());

(async () => {
  await gambar();
  const a = await kirimPesan({ cmd: "aturan" });
  if (a && a.ok !== false) { gambar.aturan = a; await gambar(); }
  kirimPesan({ cmd: "cek" });   // ambil kiriman dari CLI sekarang, tanpa menunggu 30 dtk
  const { ringkas } = await chrome.storage.local.get("ringkas");
  segarkan(!ringkas || Date.now() - ringkas.at > UMUR_STATUS);
})();
