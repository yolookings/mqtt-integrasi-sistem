import paho.mqtt.client as mqtt
import time
import ssl
import random
import json
from queue import Queue, Empty # Tambahkan Empty
from threading import Lock, Thread # Tambahkan Thread

# --- Configuration --- (tetap sama)
BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 8883
CLIENT_ID_BASE = "python_subscriber_emqx"
CLIENT_ID = f"{CLIENT_ID_BASE}_{int(time.time())}{random.randint(0, 999)}"
# Authentication (uncomment for brokers requiring credentials)
USERNAME = "fidelanata"
PASSWORD = "insisez"
YOUR_UNIQUE_TOPIC_PREFIX = "insisdemomqtt"
REQUEST_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/request"
RESPONSE_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/response/#"
TOPICS_TO_SUBSCRIBE = [
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos0", 0),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos1", 1),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos2", 2),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/status/retained", 1),
    (f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/client/#", 1),
    (REQUEST_TOPIC, 1),
    (RESPONSE_TOPIC, 1)
]

# Flow Control Configuration
MAX_QUEUE_SIZE = 2000
RATE_LIMIT = 100 # Pesan per detik yang bisa diproses
last_process_time = 0
process_lock = Lock()
message_queue = Queue(maxsize=MAX_QUEUE_SIZE)
stop_processing_thread = False # Flag untuk menghentikan thread

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"Subscriber ({CLIENT_ID}): Connected to MQTT broker ({BROKER_HOST}) with result code: {reason_code}")
        for topic, qos in TOPICS_TO_SUBSCRIBE:
            print(f"Subscriber: Subscribing to topic '{topic}' with QoS {qos}")
            client.subscribe(topic, qos=qos)
    else:
        print(f"Subscriber ({CLIENT_ID}): Failed to connect, result code: {reason_code}")

def process_message(msg):
    global last_process_time
    with process_lock: # Lock untuk sinkronisasi rate limit, jika diperlukan antar thread (meski di sini hanya 1 worker)
        current_time = time.time()
        # Pastikan tidak melebihi RATE_LIMIT
        time_since_last_process = current_time - last_process_time
        required_delay = 1.0 / RATE_LIMIT
        if time_since_last_process < required_delay:
            time.sleep(required_delay - time_since_last_process)

        payload_str = msg.payload.decode(errors='ignore')
        try:
            data = json.loads(payload_str)

            # Cek application-level expiry (jika ada field 'expiry' dalam payload JSON)
            application_level_expiry_ts = data.get('expiry') # Ambil nilai 'expiry' dari payload JSON
            processing_delay = 0.1 # Default delay pendek

            if application_level_expiry_ts is not None:
                processing_delay = 2.0 # Delay lebih lama jika ada field 'expiry' di payload
                print(f"Subscriber: Message from {msg.topic} has application-level expiry field. Timestamp: {data.get('timestamp')}, App Expiry: {application_level_expiry_ts}, Current Time: {time.time()}")
                if time.time() > application_level_expiry_ts:
                    print(f"Subscriber: APPLICATION-LEVEL EXPIRY! Message from {msg.topic} expired: {data}")
                    last_process_time = time.time()
                    return # Jangan proses lebih lanjut

            time.sleep(processing_delay) # Terapkan delay pemrosesan

            # Jika sampai sini, berarti pesan belum kedaluwarsa (baik MQTT-level maupun application-level)
            print(f"Subscriber: Processing message from topic '{msg.topic}': {data}")
            last_process_time = time.time()

        except json.JSONDecodeError:
            print(f"Subscriber: Non-JSON message received on topic {msg.topic}: {payload_str}")
            last_process_time = time.time()
        except Exception as e:
            print(f"Subscriber: Error processing message from topic {msg.topic}: {e}, Payload: {payload_str}")
            last_process_time = time.time()


def handle_request(client, msg):
    try:
        properties = msg.properties
        response_topic = properties.ResponseTopic if properties and hasattr(properties, 'ResponseTopic') else None
        correlation_data = properties.CorrelationData if properties and hasattr(properties, 'CorrelationData') else None

        if not response_topic or not correlation_data:
            print("Subscriber: Missing ResponseTopic or CorrelationData in request")
            return

        request_data = json.loads(msg.payload.decode())
        request_id_from_payload = request_data.get('request_id') # request_id dari payload

        if not request_id_from_payload:
            print("Subscriber: Missing request_id in request payload")
            return

        response_data = {
            'request_id': request_id_from_payload, # Gunakan request_id dari payload
            'status': 'success',
            'timestamp': time.time(),
            'data': {
                'message': 'Request processed successfully by subscriber',
                'request_data': request_data
            }
        }

        response_properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
        response_properties.CorrelationData = correlation_data # Echo back correlation data

        client.publish(
            response_topic,
            json.dumps(response_data),
            qos=1,
            properties=response_properties
        )
        print(f"Subscriber: Sent response to {response_topic} for request_id {request_id_from_payload}")
    except Exception as e:
        print(f"Subscriber: Error handling request: {e}")

def on_message(client, userdata, msg):
    # Pesan MQTT yang kedaluwarsa (MessageExpiryInterval) seharusnya sudah dibuang oleh broker
    # dan tidak akan sampai ke callback on_message ini.
    print(f"Subscriber ({CLIENT_ID}): Message received! Topic: '{msg.topic}', QoS: {msg.qos}, Retain: {msg.retain}")

    if msg.topic == REQUEST_TOPIC:
        handle_request(client, msg)
        return

    if not message_queue.full():
        message_queue.put(msg)
        # print(f"Subscriber ({CLIENT_ID}): Queued message from '{msg.topic}', queue size: {message_queue.qsize()}")
    else:
        print(f"Subscriber ({CLIENT_ID}): Message queue is full, dropping message from topic {msg.topic}")

# --- Thread untuk memproses antrean ---
def message_processor_worker():
    print(f"Subscriber ({CLIENT_ID}): Message processor thread started.")
    while not stop_processing_thread:
        try:
            msg = message_queue.get(timeout=1) # Tunggu pesan dengan timeout
            process_message(msg)
            message_queue.task_done()
        except Empty:
            continue # Kembali ke awal loop jika antrean kosong
        except Exception as e:
            print(f"Subscriber ({CLIENT_ID}): Error in message_processor_worker: {e}")
    print(f"Subscriber ({CLIENT_ID}): Message processor thread stopped.")


def on_subscribe(client, userdata, mid, reason_codes, properties=None):
    granted_qos_str = [str(rc.value) for rc in reason_codes] # Ubah reason_codes menjadi list string angka
    print(f"Subscriber ({CLIENT_ID}): Subscribed with MID {mid}, Granted QoS: {granted_qos_str}")


def on_disconnect(client, userdata, reason_code, properties=None):
    if reason_code != 0:
        print(f"Subscriber ({CLIENT_ID}): Unexpected disconnection (reason: {reason_code}).")
    else:
        print(f"Subscriber ({CLIENT_ID}): Disconnected normally.")

# Initialize MQTT Client
subscriber_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
subscriber_client.tls_set(cert_reqs=None, tls_version=ssl.PROTOCOL_TLS_CLIENT)

subscriber_client.on_connect = on_connect
subscriber_client.on_message = on_message
subscriber_client.on_subscribe = on_subscribe
subscriber_client.on_disconnect = on_disconnect

print(f"Subscriber ({CLIENT_ID}): Connecting to {BROKER_HOST}:{BROKER_PORT}...")
try:
    subscriber_client.username_pw_set(USERNAME, PASSWORD) 
    subscriber_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
except Exception as e:
    print(f"Subscriber ({CLIENT_ID}): Connection failed - {e}")
    exit()

# --- Mulai thread pemroses pesan ---
processor_thread = Thread(target=message_processor_worker, daemon=True)
processor_thread.start()

try:
    print(f"Subscriber ({CLIENT_ID}): Starting MQTT loop, press Ctrl+C to stop.")
    subscriber_client.loop_forever()
except KeyboardInterrupt:
    print(f"Subscriber ({CLIENT_ID}): Interrupt received, disconnecting...")
except Exception as e:
    print(f"Subscriber ({CLIENT_ID}): Error in loop - {e}")
finally:
    stop_processing_thread = True # Signal thread untuk berhenti
    if processor_thread.is_alive():
        processor_thread.join(timeout=5) # Tunggu thread selesai
    subscriber_client.disconnect()
    print(f"Subscriber ({CLIENT_ID}): Done.")