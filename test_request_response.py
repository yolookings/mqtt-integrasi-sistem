from publisher import send_request
import time

def test_request_response():
    print("\n=== Testing Request-Response Pattern ===")
    
    # Test 1: Request normal
    print("\nTest 1: Mengirim request normal")
    request_data = {
        'action': 'get_status',
        'device_id': 'device123',
        'timestamp': time.time()
    }
    response = send_request(request_data, timeout=5)
    if response:
        print(f"Response received: {response}")
    else:
        print("No response received within timeout")
    
    # Test 2: Request dengan timeout
    print("\nTest 2: Mengirim request dengan timeout pendek")
    request_data = {
        'action': 'slow_operation',
        'device_id': 'device456',
        'timestamp': time.time()
    }
    response = send_request(request_data, timeout=1)  # Timeout 1 detik
    if response:
        print(f"Response received: {response}")
    else:
        print("No response received within timeout (expected)")
    
    # Test 3: Multiple requests
    print("\nTest 3: Mengirim multiple requests")
    for i in range(3):
        request_data = {
            'action': f'operation_{i}',
            'device_id': f'device_{i}',
            'timestamp': time.time()
        }
        response = send_request(request_data, timeout=5)
        if response:
            print(f"Response {i} received: {response}")
        else:
            print(f"No response received for request {i}")

if __name__ == "__main__":
    test_request_response() 