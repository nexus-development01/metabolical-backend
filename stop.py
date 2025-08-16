#!/usr/bin/env python3
"""
Stop script for Metabolical Backend API
Gracefully stops all server processes
"""

import subprocess
import sys
import os

def stop_server():
    """Stop all backend server processes"""
    
    print("Stopping Metabolical Backend API...")
    
    try:
        # Method 1: Find and kill processes on port 8000
        result = subprocess.run(
            ["netstat", "-ano"], 
            capture_output=True, 
            text=True, 
            shell=True
        )
        
        lines = result.stdout.split('\n')
        pids = []
        
        for line in lines:
            if ':8000' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.append(pid)
        
        if pids:
            for pid in pids:
                try:
                    subprocess.run(["taskkill", "/PID", pid, "/F"], check=True)
                    print(f"Stopped process {pid}")
                except subprocess.CalledProcessError:
                    print(f"Failed to stop process {pid}")
        else:
            print("No server processes found on port 8000")
            
    except Exception as e:
        print(f"Error stopping server: {e}")
        print("Try manually stopping with Ctrl+C in the server terminal")
        return 1
    
    print("Backend server stopped successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(stop_server())
