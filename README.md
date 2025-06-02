# Demonstrasi Fitur MQTT dengan Python Paho

Proyek ini mendemonstrasikan berbagai fitur protokol MQTT menggunakan library Paho MQTT untuk Python.

## Anggota

| Nama                  | NRP        |
| --------------------- | ---------- |
| Athalla Barka Fadhil  | 5027231018 |
| Maulana Ahmad Zahiri  | 5027231010 |
| Danendra Fidel Khansa | 5027231063 |

## Fitur yang Didemonstrasikan

1.  **MQTT & MQTTS (MQTT over TLS/SSL)**
2.  **Authentication (Username/Password)**
3.  **Quality of Service (QoS) Levels 0, 1, dan 2**
4.  **Retained Messages**
5.  **Message Expiry (MQTTv5 & Application-Level)**
6.  **Request-Response Pattern**
7.  **Flow Control (Rate Limiting)**
8.  **Ping-Pong (Keep-Alive Mechanism)**

## Prasyarat

- Python 3.7+
- Pip (Python package installer)
- Broker MQTT yang mendukung MQTTv5 (misalnya, EMQX, Mosquitto versi terbaru). Proyek ini dikonfigurasi untuk `broker.emqx.io`.

## Setup

1.  **Clone repository:**

    ```bash
    git clone https://github.com/yolookings/mqtt-integrasi-sistem
    cd mqtt-integrasi-sistem
    ```

2.  **Buat dan aktifkan virtual environment (direkomendasikan):**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependensi:**

    ```bash
    pip install paho-mqtt
    ```

4.  **Konfigurasi (jika perlu):**
    - **Broker:** `BROKER_HOST` dan `BROKER_PORT` di kedua skrip (`publisher.py`, `subscriber.py`).
    - **Topik Unik:** `YOUR_UNIQUE_TOPIC_PREFIX` di kedua skrip untuk menghindari konflik dengan pengguna lain di broker publik.
    - **Autentikasi:**
      - Di `publisher.py`: Isi `USERNAME` dan `PASSWORD` jika broker Anda memerlukannya.
      - Di `subscriber.py`: Hapus komentar dan isi `USERNAME` serta `PASSWORD` jika diperlukan.

### File Utama

- `publisher.py`: Skrip untuk mempublikasikan pesan MQTT dengan berbagai fitur
- `subscriber.py`: Skrip untuk berlangganan topik dan memproses pesan MQTT

### File Pengujian

- `test_expiry.py`: Mendemonstrasikan fitur Message Expiry
- `test_flow_control.py`: Mendemonstrasikan fitur Flow Control
- `test_request_response.py`: Mendemonstrasikan pola Request-Response

## Panduan Demonstrasi

Berikut adalah langkah-langkah untuk mendemonstrasikan setiap fitur:

**Terminal Setup:** Buka dua terminal. Satu untuk menjalankan `subscriber.py` dan satu lagi untuk menjalankan `publisher.py` atau skrip tes lainnya.

---

### 1. Koneksi Dasar & MQTTS

- **Tindakan:**
  1.  Jalankan subscriber:
      ```bash
      python subscriber.py
      ```
      Amati log koneksi yang menunjukkan koneksi MQTTS ke broker.
  2.  Jalankan publisher (blok `if __name__ == "__main__":` akan mengirim beberapa pesan dasar):
      ```bash
      python publisher.py
      ```
      Amati log koneksi di publisher dan pesan yang diterima di subscriber.
- **Observasi:**
  - Kedua klien berhasil terhubung menggunakan MQTTS (port 8883, TLS).
  - Subscriber menerima pesan yang dikirim oleh publisher.
- **(Opsional) Plain MQTT:**
  1.  Modifikasi `BROKER_PORT` menjadi `1883` dan komentari/hapus baris `client.tls_set(...)` di kedua skrip.
  2.  Ulangi langkah di atas. Klien akan terhubung menggunakan MQTT tanpa enkripsi.

---

### 2. Authentication

- **Tindakan (dengan broker yang memerlukan autentikasi):**
  1.  Pastikan `USERNAME` dan `PASSWORD` di `publisher.py` (dan `subscriber.py` jika perlu) sudah benar.
  2.  Jalankan subscriber, lalu publisher.
- **Observasi:**
  - Klien berhasil terhubung setelah memberikan kredensial yang valid.
  - Jika kredensial salah atau tidak diberikan (dan broker mewajibkannya), koneksi akan gagal (Reason Code untuk `CONNACK` akan menunjukkan error autentikasi).

---

### 3. Quality of Service (QoS) 0, 1, & 2

- **Tindakan:**
  1.  Pastikan subscriber berjalan.
  2.  Perhatikan `TOPICS_TO_SUBSCRIBE` di `subscriber.py` dan contoh pengiriman pesan di blok `if __name__ == "__main__":` pada `publisher.py` (mungkin perlu mengaktifkan kembali pengiriman QoS 2 jika dikomentari).
  3.  Jalankan `publisher.py`.
- **Observasi:**
  - **Subscriber:**
    - Log `on_message` menunjukkan QoS pesan yang diterima.
    - Log `on_subscribe` menunjukkan QoS yang disetujui oleh broker untuk setiap langganan.
  - **Publisher:**
    - Log `on_publish` (untuk QoS 1 & 2) menunjukkan bahwa pesan telah diakui oleh broker (MID). Untuk QoS 0, `on_publish` biasanya tidak dipicu setelah pengiriman selesai di sisi klien.
    - Pesan dengan QoS 0 dikirim "at most once".
    - Pesan dengan QoS 1 dikirim "at least once".
    - Pesan dengan QoS 2 dikirim "exactly once".

---

### 4. Retained Messages

- **Tindakan:**
  1.  Hentikan subscriber jika sedang berjalan.
  2.  Jalankan `publisher.py`. Ini akan mengirim pesan ke `TOPIC_RETAINED` dengan flag `retain=True`.
  3.  Setelah beberapa detik, jalankan `subscriber.py`.
- **Observasi:**
  - Segera setelah subscriber berlangganan ke `TOPIC_RETAINED`, ia akan menerima pesan terakhir yang di-retain di topik tersebut, meskipun pesan itu dipublikasikan sebelum subscriber terhubung.
  - Log `on_message` di subscriber akan menunjukkan `Retain: True` untuk pesan ini.
  - Untuk menghapus pesan retained, publisher dapat mengirim pesan kosong (payload `b""`) dengan `retain=True` ke topik yang sama.

---

### 5. Message Expiry

Ada dua jenis expiry yang didemonstrasikan:

- **A. MQTTv5 Message Expiry Interval (ditangani broker):**

  - **Tindakan:**
    1.  Pastikan subscriber berjalan.
    2.  Jalankan `test_expiry.py`:
        ```bash
        python test_expiry.py
        ```
        Skrip ini mengirim beberapa skenario:
        - Pesan dengan expiry MQTT pendek (misal 1 detik).
        - Pesan dengan expiry MQTT panjang (misal 10 detik).
  - **Observasi (di Subscriber):**
    - Pesan dengan expiry MQTT 1 detik _mungkin tidak sampai_ jika waktu pengiriman dan pemrosesan oleh broker melebihi 1 detik. Broker akan membuangnya.
    - Pesan dengan expiry MQTT 10 detik _seharusnya sampai_ dan diproses.
    - Subscriber tidak perlu logika khusus untuk ini; broker yang menanganinya.

- **B. Application-Level Expiry (ditangani subscriber):**
  - **Tindakan:**
    1.  `test_expiry.py` juga mengirimkan pesan yang payload JSON-nya berisi field `'expiry'` (sebuah timestamp UNIX).
  - **Observasi (di Subscriber):**
    - Subscriber `process_message` akan mendeteksi field `'expiry'`.
    - Ia akan menunda pemrosesan (`delay = 2.0 if 'expiry' in data else 0.1`).
    - Jika `time.time() > data['expiry']` setelah penundaan, subscriber akan mencatat "APPLICATION-LEVEL EXPIRY!" dan tidak memprosesnya lebih lanjut.

---

### 6. Request-Response Pattern

Fitur ini memungkinkan publisher mengirim permintaan ke subscriber dan menerima respons yang spesifik untuk permintaan tersebut. Ini dicapai menggunakan properti MQTTv5 `ResponseTopic` dan `CorrelationData`.

- **Cara Kerja:**

  1.  **Publisher:**
      - Membuat pesan permintaan.
      - Menetapkan `ResponseTopic` (topik unik tempat ia mengharapkan balasan) dan `CorrelationData` (ID unik untuk mencocokkan permintaan dengan respons) pada properti pesan.
      - Mempublikasikan permintaan ke topik umum (`REQUEST_TOPIC`).
      - Berlangganan ke `ResponseTopic` yang telah ditentukannya.
      - Menunggu respons yang memiliki `CorrelationData` yang cocok.
  2.  **Subscriber:**
      - Menerima permintaan di `REQUEST_TOPIC`.
      - Mengekstrak `ResponseTopic` dan `CorrelationData` dari properti pesan.
      - Memproses permintaan.
      - Membuat pesan respons.
      - Menetapkan `CorrelationData` yang sama pada properti pesan respons.
      - Mempublikasikan respons ke `ResponseTopic` yang diterima dari permintaan asli.

- **Skrip Pengujian:** `test_request_response.py`

- **Tindakan untuk Demonstrasi:**

  1.  Pastikan `subscriber.py` berjalan dan terhubung ke broker:
      ```bash
      python subscriber.py
      ```
      Amati log di subscriber, ia akan siap menerima permintaan di `YOUR_UNIQUE_TOPIC_PREFIX/request`.
  2.  Di terminal lain, jalankan skrip pengujian `test_request_response.py`:
      ```bash
      python test_request_response.py
      ```
      Skrip ini akan:
      - Menghubungkan publisher ke broker.
      - Mengirim serangkaian permintaan yang telah ditentukan (lihat `run_request_response_tests()` di dalam skrip) ke `REQUEST_TOPIC`. Setiap permintaan akan memiliki `ResponseTopic` dan `CorrelationData` unik.
      - Menunggu dan mencetak respons yang diterima.

- **Observasi:**
  - **Di Terminal `test_request_response.py` (Publisher):**
    - Anda akan melihat log untuk setiap permintaan yang dikirim.
    - Untuk setiap permintaan yang berhasil diproses oleh subscriber, Anda akan melihat log "Response received..." diikuti oleh payload JSON dari respons. Respons ini akan berisi `request_id` yang cocok dengan permintaan aslinya.
    - Jika subscriber tidak merespons dalam periode `timeout` yang ditentukan dalam fungsi `send_request()`, Anda akan melihat pesan "No response received within timeout...".
  - **Di Terminal `subscriber.py`:**
    - Anda akan melihat log "Message received!" ketika permintaan tiba di `REQUEST_TOPIC`.
    - Callback `handle_request` akan dipicu. Anda akan melihat log yang menunjukkan bahwa subscriber memproses permintaan dan mengirimkan balasan, misalnya: `Subscriber: Sent response to insisdemomqtt/response/python_publisher_emqx_xxxxxx for request_id yyyyyy-zzzz-zzzz-zzzz`.
    - `ResponseTopic` yang digunakan oleh subscriber diambil dari properti pesan permintaan. `CorrelationData` juga dicocokkan.

---

### 7. Flow Control (Rate Limiting)

- **Tindakan:**
  1.  Ubah `RATE_LIMIT` di `publisher.py` dan/atau `subscriber.py` ke nilai yang sangat rendah (misal, 1 atau 2 pesan per detik).
  2.  Modifikasi `publisher.py` untuk mengirim banyak pesan dalam loop cepat (misalnya, 10 pesan tanpa `time.sleep` antar publish di dalam loop).
  3.  Jalankan subscriber, lalu publisher yang dimodifikasi.
- **Observasi:**
  - **Publisher:** Meskipun loop mencoba mengirim dengan cepat, output aktual (dan timestamp di log `on_publish` atau log internal `send_message_with_flow_control`) akan menunjukkan bahwa pesan dikirim sesuai `RATE_LIMIT` karena adanya `time.sleep` dalam `publish_lock`.
  - **Subscriber:**
    - Jika pesan masuk lebih cepat dari `RATE_LIMIT` pemrosesan, `message_queue` akan terisi.
    - Log `process_message` akan menunjukkan bahwa pesan diproses sesuai `RATE_LIMIT` karena `time.sleep` dalam `process_lock`.
    - Jika antrean penuh (`MAX_QUEUE_SIZE`), pesan akan didrop dengan log "Message queue is full...".

---

### 8. Ping-Pong (Keep-Alive Mechanism)

- **Tindakan:**
  1.  Pastikan subscriber dan publisher terhubung ke broker. Parameter `keepalive=60` digunakan saat `connect()`.
  2.  Biarkan kedua klien berjalan tanpa aktivitas pengiriman pesan selama lebih dari 60 detik (misalnya 70-80 detik).
  3.  Untuk mengamati ini secara langsung, Anda memerlukan alat network sniffing (seperti Wireshark) yang memfilter paket MQTT antara klien dan broker, atau broker yang log-nya menunjukkan aktivitas PINGREQ/PINGRESP.
- **Observasi (dengan alat bantu atau log broker):**
  - Library Paho MQTT akan secara otomatis mengirim PINGREQ dari klien ke broker jika tidak ada pesan lain yang dikirim dalam interval `keepalive`.
  - Broker akan merespons dengan PINGRESP.
  - Ini menjaga koneksi tetap aktif dan mencegah broker atau firewall menutup koneksi karena tidak aktif.
  - Jika broker tidak menerima PINGREQ (atau data lain) dari klien dalam `keepalive * 1.5` detik, broker dapat memutuskan koneksi klien.
  - Jika klien tidak menerima PINGRESP (atau data lain) dari broker, ia juga akan menganggap koneksi terputus dan mencoba menyambung kembali (jika `loop_forever` atau `reconnect_delay_set` digunakan).

---

## Catatan Tambahan

- **Last Will and Testament (LWT):** `publisher.py` dikonfigurasi dengan LWT. Jika publisher terputus secara tidak normal (misalnya, proses dimatikan paksa), broker akan mempublikasikan pesan LWT ke `LAST_WILL_TOPIC`. Subscriber yang berlangganan ke topik wildcard seperti `insisdemomqtt/iot/client/#` akan menerima pesan ini.
  - **Demo LWT:** Jalankan subscriber. Jalankan publisher. Lalu, matikan proses publisher secara paksa (Ctrl+C mungkin tidak cukup, coba `kill -9 <PID>` di Linux/macOS atau tutup paksa dari Task Manager di Windows). Amati subscriber menerima pesan LWT.
