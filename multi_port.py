#!/usr/bin/python3

import threading
import queue
import time
import socket

def worker():
    while True:
        port = q.get()
        scan_port(target, port)
        q.task_done()

def scan_port(target, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((target, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        with thread_lock:
            open_ports.append(port)  # Add the open port to the list
    except Exception as e:  # Catch all exceptions to log specific errors
        with thread_lock:
            print(f'[-] Port {port} on {target} could not be opened due to {e}')
    finally:
        s.close()

# Device to scan
target = '192.168.1.14'

# Define a print lock
thread_lock = threading.Lock()

# List to hold open ports
open_ports = []

# Create our queue
q = queue.Queue()

# Define number of threads
for r in range(100):
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

# Start timer before sending tasks to the queue
start_time = time.time()

print('Creating a task request for each port\n')

# Create a task request for each possible port to the worker
for port in range(1, 65535):
    q.put(port)

# Block until all tasks are done
q.join()

# Print all open ports
print(f"\nAll workers completed their tasks after {round(time.time() - start_time, 2)} seconds")
print("Open Ports:")
for port in sorted(open_ports):
    print(f'[+] Port {port} on {target} is OPEN')
