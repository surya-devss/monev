// Monev Kirim, service worker.
// 1. Antrian dari CLI `monev kirim` lewat Native Messaging (tiap 30 dtk atau saat popup dibuka). Draft sudah
//    disetujui di chat/terminal, extension langsung menjalankannya dan melaporkan progres ke popup.
// 2. Status hari ini dibaca dari tab Monev dan disimpan, supaya popup langsung tampil tanpa menunggu.
// 3. Notifikasi desktop pada jam yang diatur di halaman Pengaturan. Teksnya dari CLI (monev/teks/bawaan.toml +
//    [pesan] di config.toml), tidak ditulis di sini.
importScripts("isi-form.js");

const HOST = "monev.maganghub.kirim";
const WEB = "https://monev.maganghub.kemnaker.go.id";
const BATAS = "23.59";   // batas kirim harian Monev (aturan situs)
const HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
let sibuk = false;

const tglPendek = (iso) => { const [, m, d] = iso.split("-").map(Number); return `${d} ${BULAN[m - 1]}`; };
const tglHari = (iso) => `${HARI[new Date(iso + "T00:00:00").getDay()]}, ${tglPendek(iso)}`;

// ---------------------------------------------------------------- tab Monev

function tungguTab(tabId, ms = 30000) {
  return new Promise((resolve) => {
    const selesai = (ok) => { chrome.tabs.onUpdated.removeListener(dengar); clearTimeout(t); resolve(ok); };
    const dengar = (id, info) => { if (id === tabId && info.status === "complete") selesai(true); };
    const t = setTimeout(() => selesai(false), ms);
    chrome.tabs.onUpdated.addListener(dengar);
  });
}

async function tabMonev() {
  const [ada] = await chrome.tabs.query({ url: WEB + "/*" });
  return ada || null;
}

async function bukaTabMonev(path, aktif) {
  const url = WEB + path;
  const ada = await tabMonev();
  let tab;
  if (ada) {
    tab = await chrome.tabs.update(ada.id, { url, active: aktif });
    if (aktif) await chrome.windows.update(ada.windowId, { focused: true });
  } else {
    tab = await chrome.tabs.create({ url, active: aktif });
  }
  await tungguTab(tab.id);
  await new Promise((r) => setTimeout(r, 3000)); // pengalihan SSO lewat JS (uji #3)
  return chrome.tabs.get(tab.id);
}

async function diTab(tabId, func, args = []) {
  const [res] = await chrome.scripting.executeScript({ target: { tabId }, world: "MAIN", func, args });
  return res && res.result ? res.result : { ok: false, tahap: "script", pesan: "Script tidak mengembalikan hasil." };
}

// ---------------------------------------------------------------- teks notifikasi dari CLI

async function ambilTeks(paksa = false) {
  const { teks } = await chrome.storage.local.get("teks");
  if (teks && !paksa && Date.now() - teks.at < 6 * 3600 * 1000) return teks;
  try {
    const r = await chrome.runtime.sendNativeMessage(HOST, { type: "pesan" });
    if (r && r.ok) {
      const baru = { pesan: r.pesan, nilai: r.nilai || null, asing: r.asing || [], at: Date.now() };
      await chrome.storage.local.set({ teks: baru });
      return baru;
    }
  } catch (_) { /* host tidak terjangkau: pakai simpanan terakhir */ }
  return teks || null;
}

// "{nama}" diganti nilainya; placeholder kosong dibuang bersama ", " di depannya ("Selamat pagi, {nama}." → "Selamat pagi.").
function isi(t, data) {
  return String(t || "").replace(/(, )?\{(\w+)\}/g, (_, koma, k) => (data[k] ? (koma || "") + data[k] : ""))
    .replace(/`([^`]+)`/g, "$1");   // `kode` hanya berarti di Telegram
}

// Bila CLI belum pernah terjangkau, belum ada teks sama sekali: satu kalimat netral saja.
const DARURAT = { judul: "Monev Kirim", isi: "Buka popup Monev Kirim untuk melihat status laporan hari ini." };

// Nilai perusahaan hari ini; giliran sama dengan bot (date.toordinal() Python).
function nilaiHariIni(nilai, tanggal) {
  const daftar = (nilai && nilai.poin) || [];
  if (!daftar.length) return null;
  const [y, m, d] = tanggal.split("-").map(Number);
  const ordinal = Date.UTC(y, m - 1, d) / 86400000 + 719163;
  return [nilai.semboyan || "", ...daftar[ordinal % daftar.length]];
}

function notif(id, judul, isiTeks, opsi = {}) {
  chrome.notifications.create(id, {
    type: "basic", iconUrl: "ikon/ikon-128.png", title: judul, message: isiTeks, priority: opsi.tetap ? 2 : 1,
    requireInteraction: !!opsi.tetap, ...(opsi.tombol ? { buttons: opsi.tombol.map((title) => ({ title })) } : {}),
  });
}

// ---------------------------------------------------------------- status hari ini

// Baca ringkasan dari tab Monev. Tanpa tab: buka di latar belakang lalu tutup lagi (hanya bila bolehBuka).
async function ringkasHariIni(bolehBuka = true) {
  let tab = await tabMonev(), dibuka = false;
  if (!tab) {
    if (!bolehBuka) return { ok: false, tahap: "tab" };
    tab = await chrome.tabs.create({ url: WEB + "/dashboard", active: false });
    dibuka = true;
    await tungguTab(tab.id);
    await new Promise((r) => setTimeout(r, 3000));
    tab = await chrome.tabs.get(tab.id);
  }
  try {
    if ((tab.url || "").includes("account.kemnaker.go.id")) return { ok: false, tahap: "login" };
    return await diTab(tab.id, monevRingkas);
  } finally {
    if (dibuka) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

async function segarkanStatus(bolehBuka = true) {
  const r = await ringkasHariIni(bolehBuka);
  if (r.ok) await chrome.storage.local.set({ ringkas: { ...r, at: Date.now() }, sesi: { ok: true, at: Date.now() } });
  else if (r.tahap === "login") await chrome.storage.local.set({ sesi: { ok: false, at: Date.now() } });
  return r;
}

// ---------------------------------------------------------------- antrian dari CLI

const jenisDraft = (d) => !d ? "ping" : d.revisi ? "revisi" : d.status === "ON_LEAVE" ? "izin" : "hadir";

async function cek() {
  if (sibuk) return;
  sibuk = true;
  try {
    const ambil = await chrome.runtime.sendNativeMessage(HOST, { type: "ambil" });
    await chrome.storage.local.set({ host: { ok: true, at: Date.now() } });
    const job = ambil && ambil.job;
    if (!job) return;
    if (job.type === "coba") {   // `monev extension coba <jenis>`: tampilkan notifikasi sekarang
      const hasil = await jalankanPengingat(job.draft.jenis, { uji: true }).catch((e) => ({ ok: false, tahap: "extension", pesan: String(e) }));
      const pesan = hasil.ok ? (hasil.tahap === "libur" ? "Hari ini libur, notifikasi tidak ditampilkan." : "Notifikasi ditampilkan.")
        : (hasil.pesan || hasil.tahap);
      await chrome.runtime.sendNativeMessage(HOST, { type: "hasil", id: job.id, hasil: { ...hasil, tahap: "coba", pesan } });
      return;
    }
    await selesaikan(job);
  } catch (e) {
    await chrome.storage.local.set({ host: { ok: false, at: Date.now(), pesan: String(e) } });
  } finally {
    sibuk = false;
  }
}

async function jalankan(job, info) {
  const path = job.type === "ping" ? "/dashboard"
    : job.draft && job.draft.revisi ? `/dashboard/riwayat?action=revision&date=${encodeURIComponent(job.draft.date)}`
    : "/dashboard/riwayat?action=today";
  const tab = await bukaTabMonev(path, job.type !== "ping");
  if ((tab.url || "").includes("account.kemnaker.go.id")) {
    return { ok: false, tahap: "login", pesan: "Chrome ini belum login Monev. Login di tab yang terbuka, lalu ulangi." };
  }
  // Progres: isi-form.js menulis langkahnya ke atribut DOM, dibaca dari sini tiap detik.
  const pantau = info && setInterval(async () => {
    try {
      const [r] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => document.documentElement.dataset.monevLangkah || "" });
      if (r && r.result && r.result !== info.langkah) {
        info.langkah = r.result;
        await chrome.storage.session.set({ berjalan: info });
      }
    } catch (_) { /* halaman sedang berpindah */ }
  }, 1000);
  try {
    return await diTab(tab.id, monevJalankan, [job]);
  } finally {
    if (pantau) clearInterval(pantau);
  }
}

async function selesaikan(job) {
  const jenis = jenisDraft(job.draft);
  const info = job.type === "ping" ? null
    : { id: job.id, jenis, mode: job.mode, tanggal: job.draft.date, langkah: "buka", mulai: Date.now() };
  if (info) {
    await chrome.storage.session.set({ berjalan: info });
    await chrome.action.setBadgeText({ text: "…" });
  }
  let hasil;
  try {
    hasil = await jalankan(job, info);
  } catch (e) {
    hasil = { ok: false, tahap: "extension", pesan: String(e) };
  } finally {
    await chrome.storage.session.remove("berjalan");
    await chrome.action.setBadgeText({ text: "" });
  }
  if (job.id) await chrome.runtime.sendNativeMessage(HOST, { type: "hasil", id: job.id, hasil });
  await chrome.storage.local.set({
    terakhir: { at: Date.now(), jenis, mode: job.mode, tanggal: job.draft && job.draft.date,
                hasil: { ok: hasil.ok, tahap: hasil.tahap, pesan: hasil.pesan } },
    sesi: { ok: hasil.tahap !== "login", at: Date.now() },
  });
  if (info) {
    await notifHasil(job, hasil);
    segarkanStatus(false).catch(() => {});
  }
  return hasil;
}

async function notifHasil(job, hasil) {
  const T = (await ambilTeks()) || {};
  const kunci = { terkirim: "terkirim", siap_centang: "uji", tidak_pasti: "tidak_pasti" }[hasil.tahap] || "gagal";
  const t = (T.pesan && T.pesan.hasil && T.pesan.hasil[kunci]) || DARURAT;
  const data = { tanggal: tglPendek(job.draft.date), alasan: hasil.pesan || hasil.tahap };
  notif("hasil", isi(t.judul, data), isi(t.isi, data), { tetap: kunci === "tidak_pasti" || kunci === "gagal" });
}

// ---------------------------------------------------------------- pengingat di Chrome
// Hanya hari kerja; pengingat hanya bila laporan belum diisi. Butuh Chrome terbuka; jadwal yang terlewat lebih
// dari 30 menit dilewati (sama dengan bot).

const BAWAAN = { aktif: true, pagi: { nyala: true, jam: "08:00" }, fokus: { nyala: true, jam: "09:00" },
                 ingat: { nyala: true, jam: ["15:00", "16:30", "20:00"] }, tunda: 30 };

async function aturan() {
  let { pengingat: p } = await chrome.storage.local.get("pengingat");
  if (p && "jamSapaan" in p) {   // bentuk lama (popup versi sebelumnya)
    p = { aktif: p.aktif, pagi: { nyala: p.sapaan, jam: p.jamSapaan }, fokus: { nyala: p.sapaan && !!p.jamFokus, jam: p.jamFokus || "09:00" },
          ingat: { nyala: true, jam: p.jam || [] } };
  }
  p = p || {};
  return { ...BAWAAN, ...p, pagi: { ...BAWAAN.pagi, ...p.pagi }, fokus: { ...BAWAAN.fokus, ...p.fokus },
           ingat: { ...BAWAAN.ingat, ...p.ingat } };
}

const jamSah = (j) => /^\d\d:\d\d$/.test(j || "");
const daftarIngat = (a) => [...new Set(a.ingat.jam.filter(jamSah))].sort();

function urutanIngat(jam, daftar) {
  const i = daftar.indexOf(jam);
  if (i <= 0) return "pertama";
  return i === daftar.length - 1 ? "terakhir" : "kedua";
}

function berikutnya(jam) {
  const [h, m] = jam.split(":").map(Number);
  const t = new Date();
  t.setHours(h, m, 0, 0);
  if (t.getTime() <= Date.now()) t.setDate(t.getDate() + 1);
  return t.getTime();
}

async function jadwalUlang() {
  for (const a of await chrome.alarms.getAll()) {
    if (a.name.startsWith("ingat:") || a.name === "pagi" || a.name === "fokus") await chrome.alarms.clear(a.name);
  }
  const a = await aturan();
  if (!a.aktif) return;
  if (a.pagi.nyala && jamSah(a.pagi.jam)) chrome.alarms.create("pagi", { when: berikutnya(a.pagi.jam), periodInMinutes: 1440 });
  if (a.fokus.nyala && jamSah(a.fokus.jam)) chrome.alarms.create("fokus", { when: berikutnya(a.fokus.jam), periodInMinutes: 1440 });
  if (a.ingat.nyala) for (const j of daftarIngat(a)) chrome.alarms.create("ingat:" + j, { when: berikutnya(j), periodInMinutes: 1440 });
}

async function jalankanPengingat(nama, { uji = false, urutan = "pertama" } = {}) {
  const r = await segarkanStatus(true);
  const T = (await ambilTeks()) || {};
  const P = T.pesan || null;
  if (!r.ok) {
    if (r.tahap === "login") notif("login", P ? P.login.judul : DARURAT.judul, P ? P.login.isi : DARURAT.isi, { tombol: ["Buka Monev"] });
    return r;
  }
  if (!r.aktif || r.libur) return { ok: true, tahap: "libur" };
  if (!P) { notif(nama, DARURAT.judul, DARURAT.isi); return { ok: true, tahap: "dikirim" }; }

  const data = { nama: r.nama, hari: tglHari(r.tanggal), tanggal: tglPendek(r.tanggal), batas: BATAS,
                 sisa: String(Math.max(1, 24 - new Date().getHours())) };
  if (nama === "pagi") {
    const rev = (r.perlu_revisi || []).map((x) => tglPendek(x.date)).join(", ");
    const baris = [[r.posisi, r.perusahaan].filter(Boolean).join(" di "), `${data.hari}, hari kerja`,
      r.sudah_isi ? P.pagi.sudah : P.pagi.belum, rev && P.pagi.revisi.replace("{tanggal}", rev)];
    notif("pagi", isi(P.pagi.judul, data), baris.filter(Boolean).map((x) => isi(x, data)).join("\n"));
  } else if (nama === "fokus") {
    const hari = new Date(r.tanggal + "T00:00:00").getDay();
    const n = nilaiHariIni(T.nilai, r.tanggal);
    const poin = [hari === 1 && P.fokus.senin, hari === 5 && P.fokus.jumat, ...P.fokus.poin, n && (n[2] ? `${n[1]}, ${n[2]}` : n[1])]
      .filter(Boolean).map((x) => "• " + isi(x, data));
    notif("fokus", isi(P.fokus.judul, data), [...poin, n && n[0]].filter(Boolean).join("\n"));
  } else {
    if (r.sudah_isi && !uji) return { ok: true, tahap: "sudah_isi" };
    const a = await aturan();
    const t = P.ingat[urutan] || P.ingat.pertama;
    await chrome.storage.session.set({ urutanTunda: urutan });
    notif("ingat", isi(t.judul, data), isi(t.isi, data),
      { tombol: ["Buka form", `Ingatkan ${a.tunda} menit lagi`], tetap: urutan === "terakhir" });
  }
  return { ok: true, tahap: "dikirim" };
}

const bukaForm = () => bukaTabMonev("/dashboard/riwayat?action=today", true);

chrome.notifications.onClicked.addListener(async (id) => {
  chrome.notifications.clear(id);
  if (id === "ingat" || id === "login") await bukaForm();
  else if (id === "hasil") await bukaTabMonev("/dashboard/riwayat", true);
  else await bukaTabMonev("/dashboard", true);
});

chrome.notifications.onButtonClicked.addListener(async (id, i) => {
  chrome.notifications.clear(id);
  if (id === "login" || (id === "ingat" && i === 0)) return bukaForm();
  if (id === "ingat" && i === 1) chrome.alarms.create("tunda", { delayInMinutes: (await aturan()).tunda });
});

// ---------------------------------------------------------------- perintah dari popup dan halaman Pengaturan

const PERINTAH = {
  cek: async () => { await cek(); return true; },
  segarkan: (m) => segarkanStatus(m.bolehBuka !== false),
  buka: async (m) => { await bukaTabMonev(m.path || "/dashboard", true); return true; },
  aturan: () => aturan(),
  simpanAturan: async (m) => { await chrome.storage.local.set({ pengingat: m.aturan }); await jadwalUlang(); return true; },
  coba: (m) => jalankanPengingat(m.jenis || "ingat", { uji: true }),
  teks: (m) => ambilTeks(!!m.paksa),
};

chrome.runtime.onMessage.addListener((msg, _s, reply) => {
  const f = PERINTAH[msg && msg.cmd];
  if (!f) return false;
  f(msg).then(reply, (e) => reply({ ok: false, tahap: "extension", pesan: String(e) }));
  return true;
});

chrome.alarms.create("cek", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(async (a) => {
  if (a.name === "cek") return cek();
  if (a.name === "tunda") {
    const { urutanTunda } = await chrome.storage.session.get("urutanTunda");
    return jalankanPengingat("ingat", { urutan: urutanTunda || "pertama" }).catch(() => {});
  }
  if (a.name === "pagi" || a.name === "fokus" || a.name.startsWith("ingat:")) {
    if (Date.now() - a.scheduledTime > 30 * 60 * 1000) return;   // Chrome baru dibuka jauh setelah jadwal
    if (a.name.startsWith("ingat:")) {
      const jam = a.name.slice(6);
      return jalankanPengingat("ingat", { urutan: urutanIngat(jam, daftarIngat(await aturan())) }).catch(() => {});
    }
    jalankanPengingat(a.name).catch(() => {});
  }
});
chrome.runtime.onStartup.addListener(() => { cek(); jadwalUlang(); ambilTeks(); });
chrome.runtime.onInstalled.addListener(() => { cek(); jadwalUlang(); ambilTeks(true); chrome.action.setBadgeText({ text: "" }); });
