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
# CA_CERT_PATH = None # Biasanya tidak diperlukan untuk shiftr.io

CLIENT_ID_BASE = "python_subscriber_shiftr"
CLIENT_ID = f"{CLIENT_ID_BASE}_{int(time.time())}{random.randint(0, 999)}" # Membuat Client ID unik
USERNAME = "public"
PASSWORD = "public"

# PENTING: Ganti YOUR_UNIQUE_PREFIX dengan prefix yang SAMA seperti di publisher!
YOUR_UNIQUE_TOPIC_PREFIX = "insis"

# Topik untuk request-response
REQUEST_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/request"
RESPONSE_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/response/#"

# Topik yang akan di-subscribe
# Gunakan # untuk wildcard semua topik di bawah prefix Anda
# Atau list topik secara spesifik
TOPICS_TO_SUBSCRIBE = [
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos0", 0),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos1", 1),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos2", 2),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/status/retained", 1),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/client/#", 1),
    (REQUEST_TOPIC, 1),
    (RESPONSE_TOPIC, 1)
]
# Alternatif: (f"{YOUR_UNIQUE_TOPIC_PREFIX}/#", 2) # Subscribe semua di bawah prefix dengan QoS maks 2

# Konfigurasi Flow Control
MAX_QUEUE_SIZE = 1000
RATE_LIMIT = 100
last_process_time = 0
process_lock = Lock()

# Queue untuk menyimpan pesan yang akan diproses
message_queue = Queue(maxsize=MAX_QUEUE_SIZE)

# Callback ketika koneksi ke broker berhasil
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Subscriber ({CLIENT_ID}): Terhubung ke broker MQTT ({BROKER_HOST}) dengan kode hasil: {rc}")
        for topic, qos in TOPICS_TO_SUBSCRIBE:
            print(f"Subscriber: Subscribe ke topik '{topic}' dengan QoS {qos}")
            client.subscribe(topic, qos=qos)
    else:
        print(f"Subscriber ({CLIENT_ID}): Gagal terhubung, kode hasil: {rc}")
        if rc == 5: print("   -> Kode 5 sering berarti Bad Username/Password atau Client ID sudah digunakan.")

def process_message(msg):
    """Fungsi untuk memproses pesan dengan flow control"""
    global last_process_time
    
    with process_lock:
        current_time = time.time()
        if current_time - last_process_time < 1.0/RATE_LIMIT:
            time.sleep(1.0/RATE_LIMIT - (current_time - last_process_time))
        
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)
            
            # Cek expiry
            if 'expiry' in data:
                if time.time() > data['expiry']:
                    print(f"Message expired: {data}")
                    return
            
            # Proses pesan
            print(f"Processing message: {data}")
            last_process_time = time.time()
            
        except Exception as e:
            print(f"Error processing message: {e}")

def handle_request(client, msg):
    """Fungsi untuk menangani request dan mengirim response"""
    try:
        request_data = json.loads(msg.payload.decode())
        request_id = request_data.get('request_id')
        
        if not request_id:
            return
        
        # Proses request
        response_data = {
            'request_id': request_id,
            'status': 'success',
            'timestamp': time.time(),
            'data': {
                'message': 'Request processed successfully',
                'request_data': request_data
            }
        }
        
        # Kirim response
        response_topic = f"{YOUR_UNIQUE_TOPIC_PREFIX}/response/{request_data.get('client_id', 'unknown')}"
        client.publish(response_topic, json.dumps(response_data), qos=1)
        
    except Exception as e:
        print(f"Error handling request: {e}")

# Callback ketika pesan diterima dari broker
def on_message(client, userdata, msg):
    print(f"Subscriber ({CLIENT_ID}): Pesan diterima! Topik: '{msg.topic}', QoS: {msg.qos}, Retain: {msg.retain}")
    
    # Handle request-response
    if msg.topic == REQUEST_TOPIC:
        handle_request(client, msg)
        return
    
    # Handle pesan normal dengan flow control
    if not message_queue.full():
        message_queue.put(msg)
    else:
        print("Message queue is full, dropping message")
    
    # Proses pesan dari queue
    if not message_queue.empty():
        msg = message_queue.get()
        process_message(msg)
        message_queue.task_done()

# Callback ketika subscribe berhasil
def on_subscribe(client, userdata, mid, granted_qos):
    print(f"Subscriber ({CLIENT_ID}): Berhasil subscribe dengan MID {mid}, QoS yang di-grant: {granted_qos}")

# Callback ketika koneksi terputus
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Subscriber ({CLIENT_ID}): Koneksi terputus secara tidak terduga (rc: {rc}).")
    else:
        print(f"Subscriber ({CLIENT_ID}): Koneksi diputus secara normal.")

# Callback untuk logging (opsional, berguna untuk debugging)
def on_log(client, userdata, level, buf):
    print(f"Subscriber Log ({CLIENT_ID}): {buf}")

# Inisialisasi MQTT Client
subscriber_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)


# --- Konfigurasi Fitur ---
subscriber_client.username_pw_set(USERNAME, PASSWORD)
subscriber_client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)
# subscriber_client.tls_insecure_set(True) # JANGAN GUNAKAN DI PRODUKSI

# --- Menghubungkan Callbacks ---
subscriber_client.on_connect = on_connect
subscriber_client.on_message = on_message
subscriber_client.on_subscribe = on_subscribe
subscriber_client.on_disconnect = on_disconnect
# subscriber_client.on_log = on_log # Uncomment untuk debugging detail

# --- Koneksi ke Broker ---
print(f"Subscriber ({CLIENT_ID}): Mencoba terhubung ke {BROKER_HOST}:{BROKER_PORT}...")
try:
    subscriber_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
except Exception as e:
    print(f"Subscriber ({CLIENT_ID}): Gagal terhubung - {e}")
    exit()

try:
    print(f"Subscriber ({CLIENT_ID}): Memulai loop, tekan Ctrl+C untuk berhenti.")
    subscriber_client.loop_forever()
except KeyboardInterrupt:
    print(f"Subscriber ({CLIENT_ID}): Interupsi diterima, melakukan disconnect...")
except Exception as e:
    print(f"Subscriber ({CLIENT_ID}): Error pada loop - {e}")
finally:
    subscriber_client.disconnect()
    print(f"Subscriber ({CLIENT_ID}): Selesai.")