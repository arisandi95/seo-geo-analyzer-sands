# Setup Tombol "Buy Me a Coffee"

Tombol dukungan/donasi ☕ di navbar dan footer. Secara default **tersembunyi** — tombol baru muncul setelah username diisi, jadi tidak ada link mati selama belum di-setup.

## Langkah Setup

1. **Buat akun Buy Me a Coffee**
   - Daftar gratis di https://buymeacoffee.com/
   - Pilih username — page kamu jadi `https://buymeacoffee.com/<username>`

2. **Setup pembayaran/payout di dashboard BMC**
   - Buy Me a Coffee memproses pembayaran via **Stripe**.
   - ⚠️ **Catatan penting untuk Indonesia**: Stripe belum mendukung payout ke rekening Indonesia, sehingga dana di BMC sulit dicairkan langsung. Alternatif platform lokal dengan konsep sama:
     - **Trakteer** — https://trakteer.id (payout bank lokal/e-wallet)
     - **Saweria** — https://saweria.co (payout bank lokal/e-wallet)
   - Kalau pakai platform lokal, cukup ganti URL `https://buymeacoffee.com/{{ bmc_username }}` di `app/templates/base.html` dengan link page Trakteer/Saweria kamu.

3. **Isi username di template**
   - Buka `app/templates/base.html`, cari baris di bagian atas `<body>`:
     ```jinja
     {% set bmc_username = "" %}
     ```
   - Isi dengan username kamu, contoh:
     ```jinja
     {% set bmc_username = "dwika" %}
     ```

4. **Restart server** (atau cukup refresh — template auto-reload saat file berubah).

## Perilaku

- `bmc_username` kosong → tombol tidak dirender sama sekali (navbar & footer).
- `bmc_username` terisi → tombol kuning "☕ Buy me a coffee" muncul di navbar + link "☕ Dukung project ini" di footer, membuka page BMC di tab baru.

## Kenapa bukan widget resmi BMC?

Widget resmi (`cdnjs.buymeacoffee.com/widget/...js`) memuat script pihak ketiga yang cukup berat dan floating button yang menutupi konten. Tombol link statis lebih ringan, tanpa JavaScript eksternal, dan hasilnya sama: pengunjung sampai ke page donasi.
