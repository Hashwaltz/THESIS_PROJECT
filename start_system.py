#!/usr/bin/env python3
"""
Startup script for Norzagaray HR & Payroll System
This script starts all components of the system
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

class SystemManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_process(self, name, command, cwd=None):
        """Start a process and track it"""
        try:
            print(f"🚀 Starting {name}...")
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append((name, process))
            print(f"✅ {name} started with PID {process.pid}")
            return True
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return False
    
    def stop_all_processes(self):
        """Stop all running processes"""
        print("\n🛑 Stopping all processes...")
        self.running = False
        
        for name, process in self.processes:
            try:
                print(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
                process.wait()
                print(f"✅ {name} force stopped")
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
        
        self.processes.clear()
    
    def monitor_processes(self):
        """Monitor running processes"""
        while self.running:
            for name, process in self.processes[:]:
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    self.processes.remove((name, process))
            time.sleep(1)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.stop_all_processes()
        sys.exit(0)

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not detected. It's recommended to use a virtual environment.")
    
    # Check if required directories exist
    required_dirs = ['main_app', 'hr_system', 'payroll_system']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            print(f"❌ Required directory '{dir_name}' not found")
            return False
    
    print("✅ Requirements check passed")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        # Install HR system dependencies
        print("Installing HR system dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'hr_system/requirements.txt'], 
                      check=True, capture_output=True)
        
        # Install Payroll system dependencies
        print("Installing Payroll system dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'payroll_system/requirements.txt'], 
                      check=True, capture_output=True)
        
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating necessary directories...")
    
    directories = [
        'main_app/templates',
        'hr_system/uploads',
        'payroll_system/uploads',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Directories created")

def main():
    """Main function"""
    print("🚀 Norzagaray HR & Payroll System Startup")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed. Please fix the issues and try again.")
        return 1
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed. Please check the error messages.")
        return 1
    
    # Create directories
    create_directories()
    
    # Initialize system manager
    manager = SystemManager()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    try:
        # Start HR System
        manager.start_process(
            "HR System",
            f"{sys.executable} run.py",
            cwd="hr_system"
        )
        
        # Wait a moment for HR system to start
        time.sleep(2)
        
        # Start Payroll System
        manager.start_process(
            "Payroll System", 
            f"{sys.executable} run.py",
            cwd="payroll_system"
        )
        
        # Wait a moment for Payroll system to start
        time.sleep(2)
        
        # Start Main Application
        manager.start_process(
            "Main Application",
            f"{sys.executable} run.py",
            cwd="main_app"
        )
        
        # Wait for main application to start
        time.sleep(3)
        
        print("\n" + "=" * 50)
        print("🎉 System started successfully!")
        print("\n📱 Access URLs:")
        print("   Main Dashboard: http://localhost:5000")
        print("   HR System:      http://localhost:5001")
        print("   Payroll System: http://localhost:5002")
        print("\n💡 Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Start monitoring
        monitor_thread = threading.Thread(target=manager.monitor_processes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Keep running until interrupted
        while manager.running:
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        manager.stop_all_processes()
    
    print("👋 System shutdown complete")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


