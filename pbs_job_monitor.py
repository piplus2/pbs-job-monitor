#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBS Job Monitor - A GUI application to check PBS job states
Features:
- Login with frontend IP/hostname, username, and password
- Encrypt credentials locally for secure storage
- Display list of jobs with their states
- Filter jobs by state (Running, Completed, Held, etc.)
- View full details of any selected job
"""

import tkinter as tk
from tkinter import messagebox, ttk
from cryptography.fernet import Fernet
import subprocess
import json
from datetime import datetime


class PBSJobMonitor:
    def __init__(self):
        self.master = tk.Tk()
        self.master.title("PBS Job Monitor")
        self.master.geometry("800x600")
        
        # Generate encryption key for credentials
        try:
            with open('credentials.enc', 'rb') as f:
                self.key = Fernet(f.read())
        except FileNotFoundError:
            self.key = Fernet(Fernet.generate_key())
            with open('credentials.enc', 'wb') as f:
                pass  # Placeholder, will be overwritten on login
        
        self.credentials_file = 'credentials.enc'
        
        self.show_login_screen()
    
    def save_credentials(self, ip, user, password):
        """Save encrypted credentials to local file"""
        credential_data = f"{ip}|{user}|{password}"
        encrypted = self.key.encrypt(credential_data.encode())
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted)
    
    def load_credentials(self):
        """Load encrypted credentials from local file"""
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted = f.read()
                decrypted = self.key.decrypt(encrypted).decode()
                parts = decrypted.split('|')
                return {
                    'ip': parts[0].strip(),
                    'user': parts[1].strip(),
                    'password': parts[2] if len(parts) > 2 else None
                }
        except FileNotFoundError:
            messagebox.showinfo("Credentials", "No saved credentials found. Please log in.")
            return None
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def show_login_screen(self):
        """Display the login screen"""
        for widget in self.master.winfo_children():
            widget.destroy()
        
        login_frame = tk.Frame(self.master, bg='#f0f0f0')
        login_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        title_label = tk.Label(login_frame, text="PBS Job Monitor", 
                              font=('Arial', 18, 'bold'), bg='#f0f0f0')
        title_label.pack(pady=10)
        
        self.ip_entry = tk.Entry(login_frame, width=30)
        self.ip_entry.pack(pady=5)
        ip_label = tk.Label(login_frame, text="Frontend IP/Hostname:", anchor='w', width=20)
        ip_label.pack(anchor='w')
        
        self.user_entry = tk.Entry(login_frame, width=30)
        self.user_entry.pack(pady=5)
        user_label = tk.Label(login_frame, text="Username:", anchor='w', width=20)
        user_label.pack(anchor='w')
        
        self.password_entry = tk.Entry(login_frame, width=30, show='*')
        self.password_entry.pack(pady=5)
        password_label = tk.Label(login_frame, text="Password:", anchor='w', width=20)
        password_label.pack(anchor='w')
        
        save_button = tk.Button(login_frame, text="Save & Login", 
                               command=self.save_and_login, bg='#4CAF50', fg='white', font=('Arial', 12))
        save_button.pack(pady=10)
        
        load_btn = tk.Button(login_frame, text="Load Saved Credentials", 
                            command=self.load_saved_credentials, bg='#2196F3', fg='white', font=('Arial', 12))
        load_btn.pack(pady=5)
    
    def save_and_login(self):
        """Save credentials and proceed to job list"""
        ip = self.ip_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not all([ip, user, password]):
            messagebox.showwarning("Input Required", "Please fill in all fields.")
            return
        
        try:
            self.save_credentials(ip, user, password)
            messagebox.showinfo("Success", "Credentials saved securely!")
            self.show_job_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {e}")
    
    def load_saved_credentials(self):
        """Load previously saved credentials"""
        creds = self.load_credentials()
        if creds:
            self.ip_entry.delete(0, tk.END)
            self.user_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            
            self.ip_entry.insert(0, creds['ip'])
            self.user_entry.insert(0, creds['user'])
            if creds['password']:
                self.password_entry.insert(0, creds['password'])
            
            messagebox.showinfo("Loaded", "Credentials loaded successfully!")
        else:
            messagebox.showinfo("Info", "No saved credentials found.")
    
    def fetch_job_list(self):
        """Fetch list of PBS jobs for the user"""
        ip = self.ip_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        
        try:
            result = subprocess.run(
                f'ssh {user}@{ip} "qstat -u {user}"',
                shell=True, capture_output=True, text=True, timeout=30,
                env={**subprocess.os.environ}
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error_msg = result.stderr if result.stderr else "SSH command failed"
                print(f"Error fetching job list: {error_msg}")
                return None
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Command timed out. Please check your network connection.")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch job list: {str(e)}")
            return None
    
    def parse_job_list(self, output):
        """Parse qstat output into structured job data"""
        jobs = []
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split()
            # Expected format: JobID State TJobRun QTime  Start Time  End Time  User Host Account Memory ElapsedTime Command
            if len(parts) >= 3:
                job_id = f"{parts[0]} ({parts[1]})" if len(parts) > 1 else parts[0]
                state = parts[2]
                
                jobs.append({
                    'id': parts[0],
                    'state': state,
                    'full_info': line
                })
        
        return jobs
    
    def filter_jobs(self, jobs):
        """Filter jobs by state"""
        if not self.jobs:
            messagebox.showwarning("No Jobs", "No jobs found to filter.")
            return
        
        # Get selected state from dropdown or default to all
        filter_by = self.state_combo.get() if hasattr(self, 'state_combo') and self.state_combo else 'All'
        
        if filter_by == 'All':
            messagebox.showinfo("Display", f"Showing {len(jobs)} jobs")
        else:
            count = sum(1 for j in jobs if j['state'].startswith(filter_by))
            messagebox.showinfo(f"Filter by {filter_by}", f"Showing {count} jobs with state '{filter_by}'")
    
    def show_job_list(self):
        """Display the list of PBS jobs"""
        self.jobs = self.parse_job_list(self.fetch_job_list())
        
        if not self.jobs:
            messagebox.showinfo("No Jobs", "No jobs found or SSH connection failed. \n\n"
                           "Make sure:\n"
                           "1. The frontend IP is correct\n"
                           "2. Username and password are valid\n"
                           "3. PBS queue is accessible via SSH")
            return
        
        # Create job list window
        job_window = tk.Toplevel(self.master)
        job_window.title("PBS Jobs - Click to view details")
        job_window.geometry("900x500")
        job_window.resizable(True, True)
        
        # Scrollable frame for job list
        canvas = tk.Canvas(job_window)
        scrollbar = ttk.Scrollbar(canvas, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Header label
        header_frame = tk.Frame(job_window)
        header_frame.pack(fill='x', padx=5, pady=5)
        
        title_label = tk.Label(header_frame, text="PBS Job List", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(side='left')
        
        # Add filter dropdown
        frame_row = header_frame
        filter_frame = ttk.Frame(frame_row)
        filter_frame.pack(side='right', padx=5)
        
        self.state_combo = ttk.Combobox(filter_frame, values=[
            'All', 'Running (R)', 'Completed (C)', 'Held (H)', 
            'Exited (E)', 'Suspending (S)', 'Terminating (T)', 'Pending (P)'
        ], state='readonly')
        self.state_combo.current(0)
        self.state_combo.pack(side='left', padx=5)
        
        # Filter button
        filter_btn = tk.Button(filter_frame, text="Filter", command=self.filter_jobs)
        filter_btn.pack(side='left')
        
        canvas.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', padx=5)
        
        # Job list with clickable items
        self.job_list_frame = ttk.Frame(scrollable_frame)
        self.job_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        for job in self.jobs:
            state_color = {
                'R': 'green',
                'C': 'gray',
                'H': 'red',
                'E': 'blue',
                'S': 'orange',
                'T': 'purple',
                'P': 'yellow'
            }.get(job['state'][0], 'black')
            
            job_label = tk.Label(
                self.job_list_frame,
                text=f"Job {job['id']}: {job['state']}",
                font=('Arial', 12),
                fg=state_color,
                cursor='hand2'
            )
            job_label.pack(anchor='w')
            
            # Bind click event to show details
            def on_click(event=None):
                self.show_job_details(job)
            
            job_label.bind('<Button-1>', on_click)
    
    def show_job_details(self, job):
        """Display full details of a selected job"""
        ip = self.ip_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        
        try:
            # Fetch detailed job information
            detail_cmd = f'ssh {user}@{ip} "qstat -f {job["id"]}"'
            result = subprocess.run(
                detail_cmd, shell=True, capture_output=True, text=True, timeout=30,
                env={**subprocess.os.environ}
            )
            
            if result.returncode == 0:
                details = result.stdout.strip()
                
                # Create details window
                detail_window = tk.Toplevel(self.master)
                detail_window.title(f"Job Details: {job['id']}")
                detail_window.geometry("650x500")
                
                text_widget = tk.Text(detail_window, font=('Courier', 10), wrap='word')
                scrollbar = ttk.Scrollbar(text_widget, orient="vertical")
                text_widget.configure(yscrollcommand=scrollbar.set)
                scrollbar.configure(command=text_widget.yview)
                
                text_widget.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                text_widget.insert("1.0", details)
                text_widget.mark_set("insert", "1.0")
                
                # Add close button
                close_btn = tk.Button(detail_window, text="Close", command=detail_window.destroy)
                close_btn.pack(pady=5)
            else:
                messagebox.showerror("Error", f"Failed to fetch job details:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Fetching job details timed out.")
        except Exception as e:
            messagebox.showerror("Error", f"Error fetching job details: {str(e)}")
    
    def run(self):
        """Start the application main loop"""
        self.master.mainloop()


def main():
    """Main entry point"""
    app = PBSJobMonitor()
    app.run()


if __name__ == "__main__":
    main()
