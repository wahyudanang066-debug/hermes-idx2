# IDX Shareholder Visualizer — Pemegang Saham 1% & 5%

Website statis untuk memvisualisasikan data kepemilikan saham emiten Indonesia:

- jumlah pemegang saham `>= 1%`
- jumlah pemegang saham `>= 5%`
- total persentase kepemilikan pada masing-masing threshold
- top holders per emiten
- ranking emiten berdasarkan jumlah pemegang saham besar
- komposisi lokal vs asing
- upload beberapa CSV snapshot agar terlihat pergerakan antar tanggal

## Sumber data default

Data default berasal dari snapshot `Pemegang Saham di Atas 1%` IDX/KSEI. Snapshot lokal saat ini berisi 4 tanggal data: 2026-02-27, 2026-06-30, 2026-07-31, dan 2026-08-31.

File default:

```text
data/ownership_above1_all.csv
```

File hasil export tambahan:

```text
data/ownership_above1_20260227.csv
data/ownership_above1_20260630.csv
data/ownership_above1_20260731.csv
data/ownership_above1_20260831.csv
data/ownership_releases.csv
```

## Cara menjalankan di VPS

Dari folder project:

```bash
python -m http.server 8080
```

Lalu buka:

```text
http://IP-VPS:8080
```

Kalau memakai domain/subdomain Hostinger, arahkan reverse proxy/web server ke folder ini atau upload isi folder ke public web root.

## Cara update data

### Opsi 1 — upload CSV lewat website

Klik input `Tambah snapshot CSV`, lalu pilih satu atau beberapa CSV. Syarat minimal kolom:

```text
date,share_code,issuer_name,investor_name,total_holding_shares,percentage
```

Kolom opsional yang akan dipakai jika ada:

```text
investor_type,local_foreign,nationality,domicile
```

Kalau CSV berisi tanggal berbeda, grafik akan otomatis menampilkan pergerakan jumlah pemegang saham `>=1%` dan `>=5%`.

### Opsi 2 — ganti file default

Ganti file CSV di folder `data/`, lalu ubah konstanta `DATA_URL` di `app.js` bila nama file berubah.

## Interpretasi singkat

- `>=1%`: lebih sensitif untuk melihat investor besar/menengah yang masuk-keluar.
- `>=5%`: lebih fokus ke pemegang kendali besar.
- Penurunan jumlah holder besar tidak selalu buruk; bisa berarti kepemilikan makin terkonsentrasi.
- Kenaikan jumlah holder besar tidak selalu bagus; perlu dicek apakah ada aksi korporasi, lock-up, distribusi, atau perubahan free float.

## Disclaimer

Website ini untuk edukasi dan analisis data publik, bukan rekomendasi beli/jual saham. Selalu verifikasi ke sumber resmi IDX/KSEI dan sesuaikan dengan profil risiko.
