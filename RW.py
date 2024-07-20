#!/usr/bin/python3

import threading
import queue
import socket
import subprocess
import time
import ipaddress
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def get_local_network():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return str(ipaddress.ip_network(IP + '/24', strict=False))

def reader_ping(thread_id):
    while True:
        target = q_ping.get()
        if target is None:
            break
        send_ping(target, thread_id)
        q_ping.task_done()

def send_ping(target, thread_id):
    icmp = subprocess.Popen(['ping', '-c', '1', '-W', '1', str(target)], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    result = "UP" if "1 received" in icmp[0].decode('utf-8') else "DOWN"
    with data_lock:
        if result == "UP":
            active_hosts.append(target)
        print(f"Thread-{thread_id} pinging {target} is {result}")
        thread_status[thread_id] = f"Pinging {target} is {result}"

def writer_port(thread_id):
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
            with data_lock:
                open_ports.append((target, port))
                print(f"Thread-{thread_id} scanned Port {port} on {target} - OPEN")
                thread_status[thread_id] = f"Scanning Port {port} on {target} - OPEN"
            break
        except socket.timeout:
            with data_lock:
                print(f"Thread-{thread_id} retrying Port {port} on {target} - TIMEOUT")
                thread_status[thread_id] = f"Retrying Port {port} on {target} - TIMEOUT"
        except socket.error as e:
            with data_lock:
                print(f"Thread-{thread_id} scanned Port {port} on {target} - FAILED ({e})")
                thread_status[thread_id] = f"Scanning Port {port} on {target} - FAILED ({e})"
            break
        finally:
            s.close()

def update_plot(frame):
    ax.clear()
    ax.barh(range(len(thread_status)), [1]*len(thread_status), tick_label=thread_status)
    ax.set_xlim(0, 1.5)
    ax.set_title('Thread Activity')

# Define a lock for thread-safe access to shared data
data_lock = threading.Lock()

# Discover local network
local_network = get_local_network()
all_hosts = list(ipaddress.ip_network(local_network).hosts())

# Network data
active_hosts = []
open_ports = []

# Queues for tasks
q_ping = queue.Queue()
q_port = queue.Queue()

# Define the number of threads
num_threads = 10

# Initialize thread status list
thread_status = ["Idle"] * num_threads

# Set up plot for animation
fig, ax = plt.subplots(figsize=(10, 6))
ani = animation.FuncAnimation(fig, update_plot, interval=1000)

# Start timer
start_time = time.time()

def run_tasks():
    # Create and start reader threads for pinging
    ping_threads = []
    for i in range(num_threads):
        t = threading.Thread(target=reader_ping, args=(i,))
        t.daemon = True
        t.start()
        ping_threads.append(t)

    # Add ping tasks to the queue
    for host in all_hosts:
        q_ping.put(str(host))  # Convert to string here

    # Wait for all ping tasks to be done
    for _ in range(num_threads):
        q_ping.put(None)
    for t in ping_threads:
        t.join()

    print("Pinging completed.")
    print(f"Active hosts: {active_hosts}")

    if not active_hosts:
        print("No active hosts found. Exiting...")
        return

    # Create and start writer threads for port scanning
    port_threads = []
    for i in range(num_threads):
        t = threading.Thread(target=writer_port, args=(i,))
        t.daemon = True
        t.start()
        port_threads.append(t)

    # Add port scan tasks to the queue
    for host in active_hosts:
        for port in range(1, 1025):  # Scanning common ports for demonstration
            q_port.put((str(host), port))  # Ensure host is string when passed to port scanning

    # Wait for all port scan tasks to be done
    for _ in range(num_threads):
        q_port.put(None)
    for t in port_threads:
        t.join()

    # Calculate total time
    total_time = round(time.time() - start_time, 2)
    print(f"All tasks completed after {total_time} seconds")
    print("Open Ports:")
    for host, port in sorted(open_ports):
        print(f'[+] Port {port} on {host} is OPEN')

# Run tasks in a separate thread to keep the main thread free for plt.show()
task_thread = threading.Thread(target=run_tasks)
task_thread.start()

plt.show()
task_thread.join()
