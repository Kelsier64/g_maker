import sys
import time
import threading
from datetime import datetime

class ProgressBar:
    def __init__(self, total, description="Progress", width=50):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
        
    def update(self, progress=1):
        self.current += progress
        self._draw()
        
    def set_progress(self, current):
        self.current = current
        self._draw()
        
    def _draw(self):
        if self.total == 0:
            percent = 100
        else:
            percent = min(100, (self.current / self.total) * 100)
        
        filled_width = int(self.width * percent / 100)
        bar = "█" * filled_width + "░" * (self.width - filled_width)
        
        sys.stdout.write(f"\r{self.description}: |{bar}| {percent:.1f}%")
        sys.stdout.flush()
        
    def finish(self):
        self.current = self.total
        self._draw()
        print()

def print_status(message, status="INFO", timestamp=True):
    """Print a status message with timestamp and formatting"""
    if timestamp:
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{ts}]"
    else:
        prefix = ""
    
    if status == "INFO":
        color = "\033[36m"  # Cyan
        symbol = "ℹ"
    elif status == "SUCCESS":
        color = "\033[32m"  # Green
        symbol = "✓"
    elif status == "WARNING":
        color = "\033[33m"  # Yellow
        symbol = "⚠"
    elif status == "ERROR":
        color = "\033[31m"  # Red
        symbol = "✗"
    elif status == "PROCESSING":
        color = "\033[35m"  # Magenta
        symbol = "⚡"
    else:
        color = "\033[0m"   # Reset
        symbol = "•"
    
    reset = "\033[0m"
    print(f"{color}{prefix} {symbol} {message}{reset}")

def print_separator(title=None):
    """Print a separator line with optional title"""
    line = "=" * 60
    if title:
        title_len = len(title)
        if title_len < 56:
            padding = (56 - title_len) // 2
            line = "=" * padding + f" {title} " + "=" * (56 - padding - title_len - 2)
    print(f"\033[34m{line}\033[0m")  # Blue

class SpinnerThread:
    def __init__(self, message):
        self.message = message
        self.running = False
        self.thread = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()
        
    def _spin(self):
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while self.running:
            sys.stdout.write(f"\r\033[36m{spinner_chars[i]} {self.message}\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(spinner_chars)

def get_user_input(prompt, default=None, required=True):
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        user_input = input(f"\033[36m{full_prompt}\033[0m").strip()
        
        if user_input:
            return user_input
        elif default:
            return default
        elif not required:
            return ""
        else:
            print_status("This field is required. Please enter a value.", "WARNING")

def confirm_action(prompt, default_yes=False):
    """Ask user for yes/no confirmation."""
    if default_yes:
        options = "[Y/n]"
        default = "y"
    else:
        options = "[y/N]"
        default = "n"
    
    while True:
        response = input(f"\033[33m{prompt} {options}: \033[0m").strip().lower()
        
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response == "":
            return default == "y"
        else:
            print_status("Please enter 'y' for yes or 'n' for no.", "WARNING")
