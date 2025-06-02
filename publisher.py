import paho.mqtt.client as mqtt
import time
import ssl
import random
import json
from queue import Queue
from threading import Lock, Event
import uuid

# --- Configuration ---
BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 8883
CLIENT_ID_BASE = "python_publisher_emqx"
CLIENT_ID = f"{CLIENT_ID_BASE}_{int(time.time())}{random.randint(0, 999)}"
# Authentication (uncomment for brokers requiring credentials)
USERNAME = "fidelanata"
PASSWORD = "insisez"

YOUR_UNIQUE_TOPIC_PREFIX = "insisdemomqtt"
TOPIC_QOS0 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos0"
TOPIC_QOS1 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos1"
TOPIC_QOS2 = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/data/qos2"
TOPIC_RETAINED = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/status/retained"
LAST_WILL_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/iot/client/{CLIENT_ID}/status"
LAST_WILL_MESSAGE = f"Client {CLIENT_ID} disconnected unexpectedly!"
REQUEST_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/request"
RESPONSE_TOPIC = f"{YOUR_UNIQUE_TOPIC_PREFIX}/response/{CLIENT_ID}"

# Flow Control Configuration
MAX_QUEUE_SIZE = 1000
RATE_LIMIT = 100
last_publish_time = 0
publish_lock = Lock()
message_queue = Queue(maxsize=MAX_QUEUE_SIZE)
pending_requests = {}
request_lock = Lock()

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"Publisher ({CLIENT_ID}): Connected to MQTT broker ({BROKER_HOST}) with result code: {reason_code}")
        client.subscribe(RESPONSE_TOPIC, qos=1)
    else:
        print(f"Publisher ({CLIENT_ID}): Failed to connect, result code: {reason_code}")

def on_publish(client, userdata, mid, reason_code=0, properties=None):
    print(f"Publisher ({CLIENT_ID}): Message with MID {mid} published.")

def on_message(client, userdata, msg):
    try:
        properties = msg.properties
        correlation_data = properties.CorrelationData.decode() if properties and properties.CorrelationData else None
        if not correlation_data:
            return
        
        with request_lock:
            if correlation_data in pending_requests:
                response_data = json.loads(msg.payload.decode())
                pending_requests[correlation_data]['response'] = response_data
                pending_requests[correlation_data]['event'].set()
    except Exception as e:
        print(f"Error processing response: {e}")

def send_message_with_flow_control(topic, payload, qos=0, retain=False, expiry=None, properties=None):
    global last_publish_time
    with publish_lock:
        current_time = time.time()
        if current_time - last_publish_time < 1.0/RATE_LIMIT:
            time.sleep(1.0/RATE_LIMIT - (current_time - last_publish_time))
        
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            
            result = publisher_client.publish(topic, payload, qos=qos, retain=retain, properties=properties)
            last_publish_time = time.time()
            return result
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

def send_request(request_data, timeout=20):
    correlation_id = str(uuid.uuid4())
    request_data['request_id'] = correlation_id
    
    event = Event()
    with request_lock:
        pending_requests[correlation_id] = {
            'event': event,
            'response': None
        }
    
    properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
    properties.ResponseTopic = RESPONSE_TOPIC
    properties.CorrelationData = correlation_id.encode()
    
    result = send_message_with_flow_control(
        REQUEST_TOPIC,
        request_data,
        qos=1,
        properties=properties
    )
    
    if not result or result.rc != mqtt.MQTT_ERR_SUCCESS:
        with request_lock:
            del pending_requests[correlation_id]
        return None
    
    if event.wait(timeout):
        with request_lock:
            response = pending_requests[correlation_id]['response']
            del pending_requests[correlation_id]
            return response
    else:
        with request_lock:
            del pending_requests[correlation_id]
        return None

# Initialize MQTT Client with MQTT 5.0 and updated callback API
publisher_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

# Configure TLS for MQTTS
publisher_client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=None,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

# Configure LWT
publisher_client.will_set(
    LAST_WILL_TOPIC,
    payload=LAST_WILL_MESSAGE,
    qos=1,
    retain=False
)

# Connect Callbacks
publisher_client.on_connect = on_connect
publisher_client.on_publish = on_publish
publisher_client.on_message = on_message

if __name__ == "__main__":
    print(f"Publisher ({CLIENT_ID}): Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    try:
        publisher_client.username_pw_set(USERNAME, PASSWORD)
        publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"Publisher ({CLIENT_ID}): Connection failed - {e}")
        exit()

    publisher_client.loop_start()
    time.sleep(2) # Beri waktu untuk koneksi

    if not publisher_client.is_connected():
        print(f"Publisher ({CLIENT_ID}): Failed to connect to broker. Exiting.")
        publisher_client.loop_stop()
        exit()

    # Publish Messages with different QoS (contoh publish jika dijalankan langsung)
    try:
        print("Publisher main block: Example publish sequence started.")
        payload_qos0 = {"message": f"QoS 0 message from {CLIENT_ID} at {time.time()}"}
        result_qos0 = send_message_with_flow_control(TOPIC_QOS0, payload_qos0, qos=0)
        # print(f"Publisher: Sent to '{TOPIC_QOS0}' (QoS 0) - Status: {result_qos0.rc if result_qos0 else 'Fail'}")

        time.sleep(0.5)

        payload_qos1 = {"message": f"QoS 1 message from {CLIENT_ID} at {time.time()}"}
        result_qos1 = send_message_with_flow_control(TOPIC_QOS1, payload_qos1, qos=1)
        # print(f"Publisher: Sent to '{TOPIC_QOS1}' (QoS 1) - Status: {result_qos1.rc if result_qos1 else 'Fail'}")

        time.sleep(0.5)

        payload_retained = {"message": f"Device status ({CLIENT_ID}): ONLINE - {time.asctime()}"}
        result_retained = send_message_with_flow_control(TOPIC_RETAINED, payload_retained, qos=1, retain=True)
        # print(f"Publisher: Sent to '{TOPIC_RETAINED}' (QoS 1, Retain=True) - Status: {result_retained.rc if result_retained else 'Fail'}")
        
        print("Publisher main block: Example publish sequence finished.")

    except Exception as e:
        print(f"Publisher ({CLIENT_ID}): Error during publish - {e}")
    finally:
        print(f"Publisher ({CLIENT_ID}): Disconnecting from main block.")
        publisher_client.loop_stop()
        publisher_client.disconnect()
        print(f"Publisher ({CLIENT_ID}): Done (from main block).")