import time
import json
import uuid # Untuk request_id jika diperlukan di sini, meskipun send_request sudah menanganinya
from publisher import (
    send_request,       # Fungsi utama untuk mengirim request
    publisher_client,   # Client object
    BROKER_HOST,
    BROKER_PORT,
    USERNAME,           # Jika menggunakan otentikasi
    PASSWORD,           # Jika menggunakan otentikasi
    YOUR_UNIQUE_TOPIC_PREFIX # Untuk memastikan konsistensi jika diperlukan
)
# import ssl # Tidak perlu di sini karena sudah dihandle di publisher.py
# import paho.mqtt.client as mqtt # Tidak perlu di sini karena sudah dihandle di publisher.py

def run_request_response_tests():
    print("\n=== Testing Request-Response Pattern ===")

    # Test Case 1: Permintaan standar
    print("\nTest Case 1: Sending a standard request...")
    request_data_1 = {
        'action': 'get_device_status',
        'device_id': 'temp_sensor_001',
        'location': 'living_room'
    }
    response_1 = send_request(request_data_1, timeout=10) # Timeout 10 detik
    if response_1:
        print(f"Publisher: Response received for Test Case 1: {json.dumps(response_1, indent=2)}")
        # Verifikasi sederhana (bisa lebih detail)
        if response_1.get('status') == 'success' and response_1.get('request_id') == request_data_1.get('request_id'):
            print("Publisher: Test Case 1 - Response content looks good.")
        else:
            print("Publisher: Test Case 1 - Response content mismatch or error.")
    else:
        print("Publisher: Test Case 1 - No response received within timeout or publish failed.")

    time.sleep(1) # Jeda singkat antar tes

    # Test Case 2: Permintaan dengan data berbeda
    print("\nTest Case 2: Sending another request with different data...")
    request_data_2 = {
        'action': 'set_target_temperature',
        'device_id': 'thermostat_002',
        'value': 22.5
    }
    response_2 = send_request(request_data_2, timeout=10)
    if response_2:
        print(f"Publisher: Response received for Test Case 2: {json.dumps(response_2, indent=2)}")
        if response_2.get('status') == 'success' and response_2.get('request_id') == request_data_2.get('request_id'):
            print("Publisher: Test Case 2 - Response content looks good.")
        else:
            print("Publisher: Test Case 2 - Response content mismatch or error.")
    else:
        print("Publisher: Test Case 2 - No response received within timeout or publish failed.")

    time.sleep(1)

    # Test Case 3: Simulasi permintaan yang mungkin tidak memiliki handler di subscriber (opsional)
    # Atau permintaan yang subscribernya sengaja dibuat untuk merespons dengan error
    # Ini lebih untuk menguji bagaimana subscriber menangani permintaan yang "salah"
    # dan bagaimana publisher menangani respons error atau timeout.
    print("\nTest Case 3: Sending a request that might be 'unknown' to subscriber...")
    request_data_3 = {
        'action': 'unknown_action_test',
        'param': 'some_value'
    }
    # Jika subscriber tidak mengenali 'unknown_action_test', ia mungkin tidak merespons,
    # atau Anda bisa memodifikasi subscriber untuk merespons dengan status 'error'.
    response_3 = send_request(request_data_3, timeout=5) # Timeout lebih pendek
    if response_3:
        print(f"Publisher: Response received for Test Case 3: {json.dumps(response_3, indent=2)}")
        if response_3.get('status') == 'error': # Asumsi subscriber merespons error
             print("Publisher: Test Case 3 - Received expected error response.")
        elif response_3.get('status') == 'success':
             print("Publisher: Test Case 3 - Received success (unexpected for this test).")
        else:
            print("Publisher: Test Case 3 - Response format unclear.")
    else:
        print("Publisher: Test Case 3 - No response, as might be expected if action is unhandled or timeout occurred.")

    print("\nRequest-Response tests completed. Check subscriber logs for processing details.")

if __name__ == "__main__":
    # Setup publisher_client di sini karena kita tidak menjalankan blok __main__ dari publisher.py
    print(f"Test Script: Connecting publisher client ({publisher_client._client_id.decode()})...")
    try:
        # Konfigurasi TLS dan otentikasi jika belum diatur di level global publisher_client
        publisher_client.username_pw_set(USERNAME, PASSWORD)
        publisher_client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        publisher_client.loop_start() # Penting untuk memproses callback on_message untuk respons

        # Tunggu koneksi berhasil
        connect_timeout = 10 # Tambah timeout koneksi
        start_time = time.time()
        while not publisher_client.is_connected() and (time.time() - start_time < connect_timeout):
            time.sleep(0.1)

        if not publisher_client.is_connected():
            print("Test Script: Publisher client failed to connect. Exiting.")
            if publisher_client.loop_started: # Cek apakah loop sudah start sebelum stop
                 publisher_client.loop_stop()
            exit()

        print("Test Script: Publisher client connected.")
        run_request_response_tests()

    except Exception as e:
        print(f"Test Script: Error during setup or execution - {e}")
    finally:
        print("Test Script: Disconnecting publisher client.")
        if publisher_client.is_connected():
            publisher_client.loop_stop()
            publisher_client.disconnect()
        print("Test Script: Done.")