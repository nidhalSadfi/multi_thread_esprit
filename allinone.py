#!/usr/bin/python3

import threading
import queue
import socket
import subprocess
import time
import ipaddress

def get_local_network():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return str(ipaddress.ip_network(IP + '/24', strict=False))

def worker_ping(thread_id):
    while True:
        target = q_ping.get()
        if target is None:
            break
        send_ping(target, thread_id)
        q_ping.task_done()

def send_ping(target, thread_id):
    icmp = subprocess.Popen(['ping', '-c', '1', str(target)], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    result = "UP" if "1 received" in icmp[0].decode('utf-8') else "DOWN"
    with thread_lock:
        if result == "UP":
            active_hosts.append(target)
        print(f"Thread-{thread_id} pinging {target} is {result}")

def worker_port(thread_id):
    while True:
        task = q_port.get()
        if task is None:
            break
        target, port = task
        scan_port(target, port, thread_id)
        q_port.task_done()

def scan_port(target, port, thread_id):
    for _ in range(3):  # Retry logic
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((str(target), int(port)))  # Ensure target is a string
            s.shutdown(socket.SHUT_RDWR)
            with thread_lock:
                open_ports.append((target, port))
                print(f"Thread-{thread_id} scanned Port {port} on {target} - OPEN")
            break
        except socket.timeout:
            with thread_lock:
                print(f"Thread-{thread_id} retrying Port {port} on {target} - TIMEOUT")
        except socket.error as e:
            with thread_lock:
                print(f"Thread-{thread_id} scanned Port {port} on {target} - FAILED ({e})")
            break
        finally:
            s.close()

# Define a print lock
thread_lock = threading.Lock()

# Discover local network
local_network = get_local_network()
all_hosts = list(ipaddress.ip_network(local_network).hosts())

# Network data
active_hosts = []
open_ports = []

# Queues
q_ping = queue.Queue()
q_port = queue.Queue()

# Create and start threads for pinging
num_ping_threads = 10
ping_threads = []
for i in range(num_ping_threads):
    t = threading.Thread(target=worker_ping, args=(i+1,))
    t.daemon = True
    t.start()
    ping_threads.append(t)

# Create and start threads for port scanning
num_port_threads = 10
port_threads = []
for i in range(num_ping_threads, num_ping_threads + num_port_threads):
    t = threading.Thread(target=worker_port, args=(i+1,))
    t.daemon = True
    t.start()
    port_threads.append(t)

# Start timer
start_time = time.time()

# Task requests for ping
for host in all_hosts:
    q_ping.put(str(host))  # Convert to string here

# Wait for all ping tasks to be done
for _ in range(num_ping_threads):
    q_ping.put(None)
for t in ping_threads:
    t.join()

# Task requests for port scan on active hosts
for host in active_hosts:
    for port in range(1, 1025):  # Scanning common ports for demonstration
        q_port.put((str(host), port))  # Ensure host is string when passed to port scanning

# Wait for all port scan tasks to be done
for _ in range(num_port_threads):
    q_port.put(None)
for t in port_threads:
    t.join()

print(f"All tasks completed after {round(time.time() - start_time, 2)} seconds")
print("Open Ports:")
for host, port in sorted(open_ports):
    print(f'[+] Port {port} on {host} is OPEN')
