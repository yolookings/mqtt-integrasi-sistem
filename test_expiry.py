import time
import json
# Impor publisher_client dan fungsi/konstanta yang diperlukan dari publisher.py
from publisher import (
    send_message_with_flow_control,
    TOPIC_QOS1,
    publisher_client, # Client object
    BROKER_HOST,
    BROKER_PORT,
    USERNAME,         # Jika menggunakan otentikasi
    PASSWORD          # Jika menggunakan otentikasi
)
import ssl # Untuk TLS
import paho.mqtt.client as mqtt # Untuk properties

def test_expiry_scenario():
    print("\n=== Testing Message Expiry Scenarios ===")

    # Skenario 1: Pesan dengan MQTT Expiry Interval pendek (misal 1 detik)
    # Broker akan membuang pesan ini jika tidak bisa dikirim ke subscriber dalam 1 detik.
    print("\nTest 1: Sending message with MQTT Expiry = 1 second (Broker might drop it)")
    payload1 = {
        'message_id': 'expiry_test_1',
        'info': 'This message has a 1-second MQTT expiry interval.',
        'sent_at': time.time()
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        payload1, # Fungsi akan meng-encode ke JSON
        qos=1,
        expiry=1  # MQTT MessageExpiryInterval = 1 detik
    )
    print(f"Sent payload1 to {TOPIC_QOS1} with 1s MQTT expiry.")
    # Kita tidak menambahkan 'expiry' field di payload JSON ini, jadi subscriber tidak akan melakukan app-level expiry check.

    time.sleep(3) # Beri waktu agar pesan (jika sampai) diproses atau kedaluwarsa di broker

    # Skenario 2: Pesan dengan MQTT Expiry Interval lebih panjang (misal 10 detik)
    # Seharusnya pesan ini sampai ke subscriber.
    print("\nTest 2: Sending message with MQTT Expiry = 10 seconds (Should arrive)")
    payload2 = {
        'message_id': 'expiry_test_2',
        'info': 'This message has a 10-second MQTT expiry interval.',
        'sent_at': time.time()
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        payload2,
        qos=1,
        expiry=10 # MQTT MessageExpiryInterval = 10 detik
    )
    print(f"Sent payload2 to {TOPIC_QOS1} with 10s MQTT expiry.")

    time.sleep(3)

    # Skenario 3: Pesan dengan Application-Level Expiry (MQTT Expiry panjang)
    # Subscriber akan memeriksa field 'expiry' di payload JSON.
    print("\nTest 3: Sending message for Application-Level Expiry check (MQTT Expiry = 10s)")
    current_ts = time.time()
    payload3 = {
        'message_id': 'expiry_test_3',
        'info': 'This message has an application-level expiry in its payload (2s from now).',
        'sent_at': current_ts,
        'expiry': current_ts + 2 # Application-level expiry: 2 detik dari sekarang
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        payload3,
        qos=1,
        expiry=10 # MQTT Expiry Interval cukup panjang agar broker tidak membuangnya
    )
    print(f"Sent payload3 to {TOPIC_QOS1} with application-level expiry field.")
    # Subscriber akan sleep 2 detik karena ada field 'expiry' di payload, lalu mengeceknya.

    print("\nWaiting a bit more to observe subscriber logs...")
    time.sleep(5)
    print("\nTest scenarios sent. Check subscriber logs.")

if __name__ == "__main__":
    # Setup publisher_client di sini karena kita tidak menjalankan blok __main__ dari publisher.py
    print(f"Test Script: Connecting publisher client ({publisher_client._client_id.decode()})...")
    try:
        # Konfigurasi TLS dan otentikasi jika belum diatur di level global publisher_client
        # (Biasanya sudah, tapi bisa eksplisit di sini jika perlu)
        # publisher_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        publisher_client.username_pw_set(USERNAME, PASSWORD) # Pastikan USERNAME dan PASSWORD diimpor
        publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        publisher_client.loop_start() # Penting untuk memproses callback publish dan on_message (jika publisher juga subscribe)
        
        # Tunggu koneksi berhasil
        connect_timeout = 5
        start_time = time.time()
        while not publisher_client.is_connected() and (time.time() - start_time < connect_timeout):
            time.sleep(0.1)

        if not publisher_client.is_connected():
            print("Test Script: Publisher client failed to connect. Exiting.")
            publisher_client.loop_stop()
            exit()
        
        print("Test Script: Publisher client connected.")
        test_expiry_scenario()

    except Exception as e:
        print(f"Test Script: Error during setup or execution - {e}")
    finally:
        print("Test Script: Disconnecting publisher client.")
        if publisher_client.is_connected():
            publisher_client.loop_stop()
            publisher_client.disconnect()
        print("Test Script: Done.")