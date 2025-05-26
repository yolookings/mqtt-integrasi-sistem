import time
import json
from publisher import send_message_with_flow_control, TOPIC_QOS1

def test_expiry():
    print("\n=== Testing Message Expiry ===")
    
    # Test 1: Pesan dengan expiry 5 detik
    print("\nTest 1: Mengirim pesan yang akan expired dalam 5 detik")
    payload = {
        'message': 'Test expiry 5 detik',
        'timestamp': time.time()
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        json.dumps(payload),
        qos=1,
        expiry=5
    )
    
    # Test 2: Pesan dengan expiry 10 detik
    print("\nTest 2: Mengirim pesan yang akan expired dalam 10 detik")
    payload = {
        'message': 'Test expiry 10 detik',
        'timestamp': time.time()
    }
    send_message_with_flow_control(
        TOPIC_QOS1,
        json.dumps(payload),
        qos=1,
        expiry=10
    )
    
    print("\nPesan telah dikirim. Subscriber akan mengabaikan pesan setelah waktu expiry.")

if __name__ == "__main__":
    test_expiry() 