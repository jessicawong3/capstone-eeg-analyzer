import socket
import numpy as np

stop_receiver = False

def receive_array(host='0.0.0.0', port=9999, callback=None, on_connect=None):
    global stop_receiver
    stop_receiver = False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(1)
        s.settimeout(1.0)

        print(f"Listening on {host}:{port}...")

        while not stop_receiver:
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            print(f"Connected by {addr}")
            
            # Call the on_connect callback if provided
            if on_connect:
                on_connect(addr)

            try:
                with conn:
                    # conn.settimeout(5.0)

                    while not stop_receiver:
                        # Receive EEG data
                        array_bytes = _recv_exact(conn, 7 * 960 * 4)
                        if not array_bytes:
                            break

                        array = np.frombuffer(array_bytes, dtype=np.float32).reshape(7, 960)

                        # Receive result
                        result_bytes = _recv_exact(conn, 1 * 6 * 4)
                        if not result_bytes:
                            break

                        result = np.frombuffer(result_bytes, dtype=np.float32).reshape(1, 6)

                        print(f"Received array {array.shape} and result {result.shape}")

                        # # Send ACK
                        # conn.sendall(b'ACK')

                        if callback:
                            callback(array, result)

            except (ConnectionError, socket.timeout) as e:
                print(f"Connection lost: {e}")

            print("Client disconnected\n")

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
