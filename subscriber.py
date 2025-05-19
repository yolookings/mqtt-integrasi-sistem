import paho.mqtt.client as mqtt
import random

# Konfigurasi Broker MQTT
broker_address = "broker.hivemq.com"
port = 1883
topic = "kelas/presentasi/iot"

# Callback ketika koneksi ke broker berhasil
def on_connect(client, userdata, flags, rc, properties=None): # Tambahkan properties untuk kompatibilitas v2 jika perlu
    if rc == 0:
        print(f"Terhubung ke Broker MQTT! ({broker_address})")
        client.subscribe(topic)
        print(f"Berlangganan topik: {topic}")
    else:
        print(f"Gagal terhubung, return code {rc}")

# Callback ketika pesan diterima dari broker
def on_message(client, userdata, msg):
    print(f"Pesan diterima! Topik: {msg.topic}, Isi Pesan: {msg.payload.decode()}")

# Inisialisasi MQTT Client
client_id = f'python-mqtt-subscriber-{random.randint(0, 1000)}'
# PERUBAHAN DI SINI: Tambahkan callback_api_version
client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)

client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(broker_address, port=port, keepalive=60)
except Exception as e:
    print(f"Tidak bisa terhubung ke broker: {e}")
    exit()

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Subscriber dihentikan.")
finally:
    client.disconnect()
    print("Koneksi diputus.")