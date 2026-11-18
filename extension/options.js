// Halaman Pengaturan: jadwal notifikasi (tersimpan di Chrome ini) dan info teks pesan dari CLI.
const $ = (id) => document.getElementById(id);
const jam = (ms) => new Date(ms).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }).replace(":", ".");

function kirimPesan(msg, ms = 8000) {
  return Promise.race([
    chrome.runtime.sendMessage(msg),
    new Promise((r) => setTimeout(() => r({ ok: false, tahap: "timeout", pesan: "Tidak ada jawaban (timeout)." }), ms)),
  ]);
}

function info(teks, kelas = "") {
  $("info").textContent = teks;
  $("info").className = "kecil " + kelas;
}

async function muatAturan() {
  const a = await kirimPesan({ cmd: "aturan" });
  if (!a || a.ok === false) return info("Pengaturan tidak terbaca: " + ((a && a.pesan) || "tidak ada jawaban"), "bahaya");
  $("aktif").checked = a.aktif;
  $("nyalaPagi").checked = a.pagi.nyala; $("jamPagi").value = a.pagi.jam;
  $("nyalaFokus").checked = a.fokus.nyala; $("jamFokus").value = a.fokus.jam;
  $("nyalaIngat").checked = a.ingat.nyala;
  for (let i = 0; i < 3; i++) $("ingat" + i).value = a.ingat.jam[i] || "";
  $("tunda").value = String(a.tunda);
}

async function muatTeks(paksa) {
  $("teksInfo").textContent = paksa ? "memuat…" : "";
  const t = await kirimPesan({ cmd: "teks", paksa }, 10000);
  if (!t || t.ok === false || !t.pesan) {
    $("nilai").textContent = "Teks belum termuat.";
    $("teksInfo").textContent = "Pastikan CLI tersambung (monev extension install).";
    return;
  }
  const n = t.nilai;
  $("nilai").textContent = n ? `Nilai: ${n.semboyan || "tanpa semboyan"} · ${n.poin.length} poin` : "Nilai perusahaan belum diisi ([profil.nilai]).";
  $("teksInfo").textContent = `dimuat ${jam(t.at)}`;
  $("asing").classList.toggle("hidden", !t.asing.length);
  $("asing").textContent = t.asing.length ? "Kunci tidak dikenal di config, diabaikan: " + t.asing.join(", ") : "";
}

$("simpan").addEventListener("click", async () => {
  const ingat = [0, 1, 2].map((i) => $("ingat" + i).value).filter(Boolean).sort();
  const r = await kirimPesan({ cmd: "simpanAturan", aturan: {
    aktif: $("aktif").checked,
    pagi: { nyala: $("nyalaPagi").checked, jam: $("jamPagi").value || "08:00" },
    fokus: { nyala: $("nyalaFokus").checked, jam: $("jamFokus").value || "09:00" },
    ingat: { nyala: $("nyalaIngat").checked, jam: ingat },
    tunda: Number($("tunda").value) || 30,
  } });
  if (r === true) { info("Tersimpan.", "ok"); muatAturan(); } else info("Gagal menyimpan: " + ((r && r.pesan) || "tidak ada jawaban"), "bahaya");
});

$("coba").addEventListener("click", async () => {
  info("Mengecek Monev…", "redup");
  const r = await kirimPesan({ cmd: "coba", jenis: $("jenisCoba").value }, 30000);
  if (r && r.ok) info(r.tahap === "libur" ? "Hari ini libur, tidak ada notifikasi." : "Notifikasi dikirim.", "ok");
  else info("Gagal: " + ((r && (r.pesan || r.tahap)) || "tidak ada jawaban"), "bahaya");
});

$("muatTeks").addEventListener("click", () => muatTeks(true));

muatAturan();
muatTeks(false);
