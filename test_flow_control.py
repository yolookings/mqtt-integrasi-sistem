import time
import json
from publisher import send_message_with_flow_control, TOPIC_QOS1

def test_flow_control():
    print("\n=== Testing Flow Control ===")
    
    # Test 1: Rate limiting
    print("\nTest 1: Mengirim 150 pesan (melebihi rate limit 100 pesan/detik)")
    start_time = time.time()
    for i in range(150):
        payload = {
            'message': f'Test rate limiting {i}',
            'timestamp': time.time()
        }
        send_message_with_flow_control(
            TOPIC_QOS1,
            json.dumps(payload),
            qos=1
        )
    end_time = time.time()
    print(f"Waktu yang dibutuhkan: {end_time - start_time:.2f} detik")
    print(f"Rate aktual: {150/(end_time - start_time):.2f} pesan/detik")
    
    # Test 2: Queue overflow
    print("\nTest 2: Mengirim pesan dengan interval sangat pendek")
    for i in range(5):
        payload = {
            'message': f'Test queue overflow {i}',
            'timestamp': time.time()
        }
        send_message_with_flow_control(
            TOPIC_QOS1,
            json.dumps(payload),
            qos=1
        )
        time.sleep(0.001)  # Interval sangat pendek
    
    # Test 3: Concurrent messages
    print("\nTest 3: Mengirim pesan concurrent")
    payloads = [
        {'message': f'Concurrent message {i}', 'timestamp': time.time()}
        for i in range(10)
    ]
    
    start_time = time.time()
    for payload in payloads:
        send_message_with_flow_control(
            TOPIC_QOS1,
            json.dumps(payload),
            qos=1
        )
    end_time = time.time()
    
    print(f"Waktu pengiriman 10 pesan concurrent: {end_time - start_time:.2f} detik")
    print(f"Rate aktual: {10/(end_time - start_time):.2f} pesan/detik")

if __name__ == "__main__":
    test_flow_control() 