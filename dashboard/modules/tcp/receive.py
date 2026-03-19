import socket
import numpy as np
import threading

# Global flag to stop the receiver
stop_receiver = False

def receive_array(host='100.67.219.58', port=9999, callback=None):
    global stop_receiver
    stop_receiver = False  # reset flag on start

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1.0)  # timeout so loop can check stop flag periodically
        s.bind((host, port))
        s.listen(1)
        print(f"Listening on {host}:{port}...")

        while not stop_receiver:
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue  # no connection yet, check stop flag again
            except OSError:
                break     # socket was closed externally

            with conn:
                print(f"Connected by {addr}")

                try:
                    # Receive EEG (7*960*4 = 26880 bytes)
                    array_bytes = _recv_exact(conn, 7 * 960 * 4)
                    array = np.frombuffer(array_bytes, dtype=np.float32).reshape(7, 960)

                    # Receive result (1*6*4 = 24 bytes)
                    result_bytes = _recv_exact(conn, 1 * 6 * 4)
                    result = np.frombuffer(result_bytes, dtype=np.float32).reshape(1, 6)

                    print(f"Received array {array.shape} and result {result.shape}")

                    # ACK sender
                    # conn.sendall(b'ACK')
                    # print("ACK sent — connection closed\n")

                    if callback:
                        callback(array, result)

                except ConnectionError as e:
                    print(f"Connection error: {e}")
                    continue

        print("Receiver stopped.")


def stop():
    global stop_receiver
    stop_receiver = True
    print("Stop signal sent.")


def _recv_exact(conn, num_bytes):
    buf = b''
    while len(buf) < num_bytes:
        chunk = conn.recv(num_bytes - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed before all data received")
        buf += chunk
    return buf

import time

def process(array):
    print(f"Processing array: {array.shape}")

# Run receiver in background thread
t = threading.Thread(target=receive_array, kwargs={
    'host': '0.0.0.0',
    'port': 9999,
    'callback': process
})
t.start()

# Stop after 30 seconds (or whenever you want)
time.sleep(5)
stop()       # ← sets stop_receiver = True
t.join()     # ← waits for thread to finish cleanly