import time
import json
from publisher import send_message_with_flow_control, TOPIC_QOS1, publisher_client, BROKER_HOST, BROKER_PORT
from threading import Thread
import paho.mqtt.client as mqtt

def test_flow_control():
    print("\n=== Testing Flow Control ===")
    
    # Ensure publisher is connected
    if not publisher_client.is_connected():
        print("Publisher not connected, attempting to connect...")
        publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        publisher_client.loop_start()
        time.sleep(2)
        if not publisher_client.is_connected():
            print("Failed to connect publisher")
            return
    
    # Test 1: Sending 10 messages
    print("\nTest 1: Sending 10 messages (within rate limit)")
    start_time = time.time()
    for i in range(10):
        payload = {
            'message': f'Flow control test message {i}',
            'timestamp': time.time()
        }
        result = send_message_with_flow_control(TOPIC_QOS1, payload, qos=1)
        if result and result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Message {i} sent successfully")
        else:
            print(f"Failed to send message {i}, result: {result.rc if result else 'None'}")
    elapsed_time = time.time() - start_time
    rate = 10 / elapsed_time
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Actual rate: {rate:.2f} messages/second")
    
    # Test 2: Sending messages with very short interval
    print("\nTest 2: Sending messages with very short interval")
    start_time = time.time()
    for i in range(5):
        payload = {
            'message': f'Short interval test message {i}',
            'timestamp': time.time()
        }
        result = send_message_with_flow_control(TOPIC_QOS1, payload, qos=1)
        if result and result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Message {i} sent successfully")
        else:
            print(f"Failed to send message {i}, result: {result.rc if result else 'None'}")
        time.sleep(0.01)
    elapsed_time = time.time() - start_time
    rate = 5 / elapsed_time
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Actual rate: {rate:.2f} messages/second")
    
    # Test 3: Sending concurrent messages
    print("\nTest 3: Sending concurrent messages")
    def send_concurrent_message(index):
        payload = {
            'message': f'Concurrent test message {index}',
            'timestamp': time.time()
        }
        result = send_message_with_flow_control(TOPIC_QOS1, payload, qos=1)
        if result and result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Concurrent message {index} sent successfully")
        else:
            print(f"Failed to send concurrent message {index}, result: {result.rc if result else 'None'}")
    
    start_time = time.time()
    threads = []
    for i in range(5):
        thread = Thread(target=send_concurrent_message, args=(i,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    elapsed_time = time.time() - start_time
    rate = 5 / elapsed_time
    print(f"Time to send 5 concurrent messages: {elapsed_time:.2f} seconds")
    print(f"Actual rate: {rate:.2f} messages/second")

if __name__ == "__main__":
    test_flow_control()