# Konfigurasi PageSpeed Insights API (Opsional, Tidak Wajib)

Fitur PageSpeed dapat berjalan tanpa konfigurasi tambahan. Namun, Google menerapkan batas kuota per-IP yang sangat ketat untuk akses tanpa autentikasi, sehingga rentan terkena error HTTP 429 (Too Many Requests) saat pengujian.

Agar hasil pengujian stabil dan kuota meningkat hingga 25.000 request/hari, lakukan pengaturan berikut:

1. Buat Project di Google Cloud: Buka Google Cloud Console, lalu buat project baru (gratis dan tanpa perlu konfigurasi billing).
2. Aktifkan API: Masuk ke menu API Library, cari, lalu aktifkan PageSpeed Insights API.
3. Dapatkan API Key: Buka menu Credentials, lalu buat API key baru.
4. Simpan di File `.env`:
   * Buka file `C:\laragon\www\seo\.env` (salin dan buat dari `.env.example` jika belum ada).
   * Tambahkan baris berikut ke dalam file tersebut:

```
PAGESPEED_API_KEY=masukkan_api_key_anda_di_sini
```

5. Restart Server: Restart server web/Laragon agar perubahan konfigurasi mulai diterapkan.

Catatan jika langkah ini dilewatkan: Card PageSpeed & Core Web Vitals akan tetap muncul di antarmuka, namun kemungkinan besar hanya menampilkan pesan "kuota terlampaui" alih-alih data performa yang asli.
