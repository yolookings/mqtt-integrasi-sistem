import paho.mqtt.client as mqtt
import time
import random

# Konfigurasi Broker MQTT
broker_address = "broker.hivemq.com"
port = 1883
topic = "kelas/presentasi/iot"

# Callback ketika koneksi ke broker berhasil
def on_connect(client, userdata, flags, rc, properties=None): # Tambahkan properties untuk kompatibilitas v2 jika perlu
    if rc == 0:
        print(f"Terhubung ke Broker MQTT! ({broker_address})")
    else:
        print(f"Gagal terhubung, return code {rc}")

# Inisialisasi MQTT Client
client_id = f'python-mqtt-publisher-{random.randint(0, 1000)}'
# PERUBAHAN DI SINI: Tambahkan callback_api_version
client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect

# Mencoba terhubung ke broker
try:
    client.connect(broker_address, port=port, keepalive=60)
except Exception as e:
    print(f"Tidak bisa terhubung ke broker: {e}")
    exit()

client.loop_start()

try:
    count = 0
    while True:
        count += 1
        message = f"Pesan dari Publisher Python #{count}"
        result = client.publish(topic, message)
        status = result[0]
        if status == 0:
            print(f"Kirim `{message}` ke topik `{topic}`")
        else:
            print(f"Gagal mengirim pesan ke topik `{topic}`")
        time.sleep(2)

except KeyboardInterrupt:
    print("Publisher dihentikan.")
finally:
    client.loop_stop()
    client.disconnect()
    print("Koneksi diputus.")