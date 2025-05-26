import paho.mqtt.client as mqtt
import time
import ssl # Diperlukan untuk TLS
import random # Untuk Client ID unik
import json
from queue import Queue
from threading import Lock

# --- Konfigurasi ---
BROKER_HOST = "public.cloud.shiftr.io"
BROKER_PORT = 8883  # Port untuk MQTT over TLS
# CA_CERT_PATH = None # Biasanya tidak diperlukan untuk shiftr.io karena menggunakan CA publik

CLIENT_ID_BASE = "python_publisher_shiftr"
CLIENT_ID = f"{CLIENT_ID_BASE}_{int(time.time())}{random.randint(0, 999)}" # Membuat Client ID unik
USERNAME = "public"
PASSWORD = "public"

# PENTING: Ganti YOUR_UNIQUE_PREFIX dengan sesuatu yang unik untuk Anda!
# Contoh: "myname_projectname"
YOUR_UNIQUE_TOPIC_PREFIX = "insis" 

TOPIC_QOS0 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos0"
TOPIC_QOS1 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos1"
TOPIC_QOS2 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos2"
TOPIC_RETAINED = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/status/retained"
LAST_WILL_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/client/{CLIENT_ID}/status" # LWT bisa spesifik per client
LAST_WILL_MESSAGE = f"Client {CLIENT_ID} disconnected unexpectedly!"

# Topik untuk request-response
REQUEST_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/request"
RESPONSE_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/response/{CLIENT_ID}"

# Konfigurasi Flow Control
MAX_QUEUE_SIZE = 1000  # Maksimum pesan dalam antrian
RATE_LIMIT = 100  # Maksimum pesan per detik
last_publish_time = 0
publish_lock = Lock()

# Queue untuk menyimpan pesan yang akan dikirim
message_queue = Queue(maxsize=MAX_QUEUE_SIZE)

# Dictionary untuk menyimpan request yang menunggu response
pending_requests = {}
request_lock = Lock()

# Callback ketika koneksi ke broker berhasil
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Publisher ({CLIENT_ID}): Terhubung ke broker MQTT ({BROKER_HOST}) dengan kode hasil: {rc}")
        # Subscribe ke topik response
        client.subscribe(RESPONSE_TOPIC, qos=1)
    else:
        print(f"Publisher ({CLIENT_ID}): Gagal terhubung, kode hasil: {rc}")
        if rc == 5: print("   -> Kode 5 sering berarti Bad Username/Password atau Client ID sudah digunakan.")
        # Kode rc lain:
        # 1: Connection refused - incorrect protocol version
        # 2: Connection refused - invalid client identifier
        # 3: Connection refused - server unavailable
        # 4: Connection refused - bad username or password

# Callback ketika pesan berhasil dipublikasikan (untuk QoS 1 dan 2)
def on_publish(client, userdata, mid):
    print(f"Publisher ({CLIENT_ID}): Pesan dengan MID {mid} telah dipublikasikan.")

# Callback untuk logging (opsional, berguna untuk debugging)
def on_log(client, userdata, level, buf):
    print(f"Publisher Log ({CLIENT_ID}): {buf}")

def on_message(client, userdata, msg):
    """Callback untuk menerima response"""
    if msg.topic == RESPONSE_TOPIC:
        try:
            response_data = json.loads(msg.payload.decode())
            request_id = response_data.get('request_id')
            with request_lock:
                if request_id in pending_requests:
                    pending_requests[request_id]['response'] = response_data
                    pending_requests[request_id]['event'].set()
        except Exception as e:
            print(f"Error processing response: {e}")

def send_message_with_flow_control(topic, payload, qos=0, retain=False, expiry=None):
    """Fungsi untuk mengirim pesan dengan flow control"""
    global last_publish_time
    
    with publish_lock:
        current_time = time.time()
        if current_time - last_publish_time < 1.0/RATE_LIMIT:
            time.sleep(1.0/RATE_LIMIT - (current_time - last_publish_time))
        
        try:
            # Tambahkan expiry jika disediakan
            if expiry:
                if isinstance(payload, str):
                    payload = json.loads(payload)
                payload['expiry'] = time.time() + expiry
                payload = json.dumps(payload)
            
            result = publisher_client.publish(topic, payload, qos=qos, retain=retain)
            last_publish_time = time.time()
            return result
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

def send_request(request_data, timeout=10):
    """Fungsi untuk mengirim request dan menunggu response"""
    request_id = str(random.randint(1000, 9999))
    request_data['request_id'] = request_id
    
    # Buat event untuk menunggu response
    import threading
    event = threading.Event()
    
    with request_lock:
        pending_requests[request_id] = {
            'event': event,
            'response': None
        }
    
    # Kirim request
    result = send_message_with_flow_control(
        REQUEST_TOPIC,
        json.dumps(request_data),
        qos=1
    )
    
    if not result:
        with request_lock:
            del pending_requests[request_id]
        return None
    
    # Tunggu response
    if event.wait(timeout):
        with request_lock:
            response = pending_requests[request_id]['response']
            del pending_requests[request_id]
            return response
    else:
        with request_lock:
            del pending_requests[request_id]
        return None

# Inisialisasi MQTT Client
# clean_session=False untuk shiftr.io jika ingin sesi persisten (hati-hati dengan LWT)
# clean_session=True lebih umum dan LWT bekerja lebih bisa diprediksi
publisher_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)


# --- Konfigurasi Fitur ---

# 1. Authentication
publisher_client.username_pw_set(USERNAME, PASSWORD)

# 2. MQTT Secure (TLS)
publisher_client.tls_set(
    ca_certs=None, # Mengandalkan system CA store. Jika gagal, Anda mungkin perlu menyediakan file CA.
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT, # Atau ssl.PROTOCOL_TLSv1_2
    ciphers=None
)
# Untuk debugging jika ada masalah SSL (JANGAN GUNAKAN DI PRODUKSI):
# publisher_client.tls_insecure_set(True)

# 3. Last Will and Testament (LWT)
publisher_client.will_set(
    LAST_WILL_TOPIC,
    payload=LAST_WILL_MESSAGE,
    qos=1,
    retain=False # LWT biasanya tidak di-retain, tapi bisa jika diperlukan
)

# --- Menghubungkan Callbacks ---
publisher_client.on_connect = on_connect
publisher_client.on_publish = on_publish
publisher_client.on_message = on_message
# publisher_client.on_log = on_log # Uncomment untuk debugging detail

# --- Koneksi ke Broker ---
print(f"Publisher ({CLIENT_ID}): Mencoba terhubung ke {BROKER_HOST}:{BROKER_PORT}...")
try:
    publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
except Exception as e:
    print(f"Publisher ({CLIENT_ID}): Gagal terhubung - {e}")
    exit()

publisher_client.loop_start()

time.sleep(2) # Tunggu koneksi stabil

if not publisher_client.is_connected():
    print(f"Publisher ({CLIENT_ID}): Tidak dapat terhubung ke broker. Keluar.")
    publisher_client.loop_stop()
    exit()

# --- Publikasi Pesan ---
try:
    payload_qos0 = f"Pesan QoS 0 dari {CLIENT_ID} pada {time.time()}"
    result_qos0 = publisher_client.publish(TOPIC_QOS0, payload_qos0, qos=0)
    print(f"Publisher: Mengirim ke '{TOPIC_QOS0}' (QoS 0) - Status: {result_qos0.rc}")

    time.sleep(0.5)

    payload_qos1 = f"Pesan QoS 1 dari {CLIENT_ID} pada {time.time()}"
    result_qos1 = publisher_client.publish(TOPIC_QOS1, payload_qos1, qos=1)
    print(f"Publisher: Mengirim ke '{TOPIC_QOS1}' (QoS 1) - Status: {result_qos1.rc}")

    time.sleep(0.5)

    payload_qos2 = f"Pesan QoS 2 dari {CLIENT_ID} pada {time.time()}"
    result_qos2 = publisher_client.publish(TOPIC_QOS2, payload_qos2, qos=2)
    print(f"Publisher: Mengirim ke '{TOPIC_QOS2}' (QoS 2) - Status: {result_qos2.rc}")

    time.sleep(0.5)

    payload_retained = f"Status terakhir perangkat ({CLIENT_ID}): ONLINE - {time.asctime()}"
    result_retained = publisher_client.publish(TOPIC_RETAINED, payload_retained, qos=1, retain=True)
    print(f"Publisher: Mengirim ke '{TOPIC_RETAINED}' (QoS 1, Retain=True) - Status: {result_retained.rc}")
    print("Publisher: Pesan Retained telah dikirim.")

    print(f"\nPublisher ({CLIENT_ID}): Semua pesan telah dikirim. Menunggu beberapa detik sebelum disconnect...")
    time.sleep(5)

    # Contoh penggunaan request-response
    request_data = {
        'action': 'get_status',
        'device_id': 'device123'
    }
    response = send_request(request_data)
    if response:
        print(f"Response received: {response}")
    else:
        print("No response received within timeout")
    
    # Contoh penggunaan expiry
    payload_with_expiry = {
        'message': 'This message will expire in 60 seconds',
        'timestamp': time.time()
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        json.dumps(payload_with_expiry),
        qos=1,
        expiry=60  # Expire dalam 60 detik
    )

except Exception as e:
    print(f"Publisher ({CLIENT_ID}): Error saat publish - {e}")

finally:
    print(f"Publisher ({CLIENT_ID}): Melakukan disconnect.")
    publisher_client.loop_stop()
    publisher_client.disconnect()
    print(f"Publisher ({CLIENT_ID}): Selesai.")