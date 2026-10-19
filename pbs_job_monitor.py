#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBS Job Monitor - A GUI application to check PBS job states
Features:
- Single window: connection bar at the top, job list and details below
- Bookmarks for multiple sites/logins, stored encrypted locally
- Color-coded job list with per-state counters, search and sortable columns
- Full details of the selected job (qstat -f), optional auto-refresh
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import tkinter.font as tkfont
from cryptography.fernet import Fernet
from datetime import datetime
import json
import os
import queue
import shlex
import threading
import paramiko

KEY_FILE = os.path.expanduser('~/.pbs_job_monitor.key')
BOOKMARKS_FILE = os.path.expanduser('~/.pbs_job_monitor.bookmarks')
LEGACY_CREDENTIALS_FILE = 'credentials.enc'
QSTAT = '/opt/pbs/bin/qstat'
AUTO_REFRESH_DEFAULT_S = 30
AUTO_REFRESH_MIN_S, AUTO_REFRESH_MAX_S = 5, 3600

# State letter -> (label, foreground, background)
STATES = {
    'R': ('Running', '#137333', '#e6f4ea'),
    'Q': ('Queued', '#b06000', '#fef7e0'),
    'H': ('Held', '#c5221f', '#fce8e6'),
    'W': ('Waiting', '#b06000', '#fef7e0'),
    'B': ('Array', '#8430ce', '#f3e8fd'),
    'E': ('Exiting', '#1a73e8', '#e8f0fe'),
    'S': ('Suspended', '#e8710a', '#feefe3'),
    'U': ('Suspended', '#e8710a', '#feefe3'),
    'T': ('Transit', '#8430ce', '#f3e8fd'),
    'M': ('Moved', '#5f6368', '#f1f3f4'),
    'F': ('Finished', '#5f6368', '#f1f3f4'),
    'X': ('Finished', '#5f6368', '#f1f3f4'),
}
UNKNOWN_STATE = ('Unknown', '#3c4043', '#ffffff')

# Colors for the window chrome
BG = '#f5f6f8'
HEADER_BG = '#1f2937'
HEADER_FG = '#ffffff'
MUTED = '#6b7280'
ACCENT = '#2563eb'

COLUMNS = (
    ('id', 'Job ID', 90, False),
    ('name', 'Name', 160, True),
    ('queue', 'Queue', 90, False),
    ('state', 'State', 100, False),
    ('nodes', 'Nodes', 60, False),
    ('cpus', 'CPUs', 60, False),
    ('mem', 'Memory', 80, False),
    ('req_time', 'Req. time', 85, False),
    ('elapsed', 'Elapsed', 85, False),
)

# (label, qstat -f attribute(s)); two attributes are shown as "used / requested"
SUMMARY_FIELDS = (
    ('Owner', ('Job_Owner',)),
    ('Queue', ('queue',)),
    ('Exec host', ('exec_host',)),
    ('Walltime', ('resources_used.walltime', 'Resource_List.walltime')),
    ('CPU time', ('resources_used.cput',)),
    ('CPUs', ('resources_used.ncpus', 'Resource_List.ncpus')),
    ('Memory', ('resources_used.mem', 'Resource_List.mem')),
    ('Submitted', ('qtime',)),
    ('Started', ('stime',)),
    ('Exit status', ('Exit_status',)),
    ('Output', ('Output_Path',)),
    ('Error', ('Error_Path',)),
)


def strip_job_id(job_id):
    """'1234.energon01' -> '1234' (qstat also truncates long ids with '*')"""
    return job_id.split('.')[0]


def parse_job_list(output):
    """Parse `qstat -u` output into a list of job dicts"""
    jobs = []
    in_table = False
    for line in (output or '').splitlines():
        if line.startswith('---'):
            in_table = True
            continue
        parts = line.split()
        # Job ID Username Queue Jobname SessID NDS TSK Memory Time S Time
        if not in_table or len(parts) < 11:
            continue
        jobs.append({
            'id': strip_job_id(parts[0]),
            'user': parts[1],
            'queue': parts[2],
            'name': ' '.join(parts[3:-7]),
            'nodes': parts[-6],
            'cpus': parts[-5],
            'mem': parts[-4],
            'req_time': parts[-3],
            'state': parts[-2],
            'elapsed': parts[-1],
        })
    return jobs


def parse_job_details(output):
    """Parse `qstat -f` output into an ordered dict of attributes"""
    attrs = {}
    last = None
    for line in (output or '').splitlines():
        if line.startswith('Job Id:'):
            attrs['Job Id'] = line.split(':', 1)[1].strip()
            last = 'Job Id'
        elif line.startswith('\t') and last:
            attrs[last] += line.strip()  # continuation of a wrapped value
        elif ' = ' in line:
            key, value = line.strip().split(' = ', 1)
            attrs[key] = value
            last = key
    return attrs


def job_sort_key(job_id):
    digits = ''.join(c for c in job_id if c.isdigit())
    return (int(digits) if digits else 0, job_id)


class BookmarkStore:
    """Sites and logins, encrypted with a local Fernet key"""

    def __init__(self):
        try:
            with open(KEY_FILE, 'rb') as f:
                self.fernet = Fernet(f.read())
        except FileNotFoundError:
            key = Fernet.generate_key()
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(key)
            self.fernet = Fernet(key)

        self.sites = {}
        self.last = None
        self.refresh_seconds = AUTO_REFRESH_DEFAULT_S
        self.load()

    def load(self):
        try:
            with open(BOOKMARKS_FILE, 'rb') as f:
                data = json.loads(self.fernet.decrypt(f.read()).decode())
            self.sites = data.get('sites', {})
            self.last = data.get('last')
            self.refresh_seconds = data.get('refresh_seconds', AUTO_REFRESH_DEFAULT_S)
        except FileNotFoundError:
            self.import_legacy()
        except Exception as e:
            print(f"Error loading bookmarks: {e}")

    def import_legacy(self):
        """Import the single login saved by older versions (credentials.enc)"""
        try:
            with open(LEGACY_CREDENTIALS_FILE, 'rb') as f:
                parts = self.fernet.decrypt(f.read()).decode().split('|')
            host, user = parts[0].strip(), parts[1].strip()
            password = parts[2] if len(parts) > 2 else ''
            self.put(host, host, user, password)
        except Exception:
            pass

    def save(self):
        data = json.dumps({'sites': self.sites, 'last': self.last,
                           'refresh_seconds': self.refresh_seconds}).encode()
        fd = os.open(BOOKMARKS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(self.fernet.encrypt(data))

    def put(self, name, host, user, password):
        self.sites[name] = {'host': host, 'user': user, 'password': password}
        self.last = name
        self.save()

    def delete(self, name):
        self.sites.pop(name, None)
        if self.last == name:
            self.last = None
        self.save()

    def names(self):
        return sorted(self.sites, key=str.lower)


class PBSJobMonitor:
    def __init__(self):
        self.master = tk.Tk()
        self.master.title("PBS Job Monitor")
        self.master.geometry("1280x760")
        self.master.minsize(900, 560)
        self.master.configure(bg=BG)

        self.bookmarks = BookmarkStore()
        self.ssh = None
        self.ssh_lock = threading.Lock()
        self.conn = None  # (host, user, password) of the live connection
        self.results = queue.Queue()
        self.jobs = []
        self.state_filter = None
        self.sort_column, self.sort_reverse = 'id', False
        self.refresh_job = None
        self.loading = False
        self.detail_request = 0

        self.setup_styles()
        self.build_header()
        self.build_connection_bar()
        self.build_toolbar()
        self.build_status_bar()  # before the expanding main area, so pack keeps room for it
        self.build_main_area()

        self.refresh_bookmark_list()
        last = self.bookmarks.last
        if last is not None and last in self.bookmarks.sites:
            self.bookmark_var.set(last)
            self.on_bookmark_selected()

        # Start with the divider where all job list columns fit
        self.master.update_idletasks()
        self.paned.sashpos(0, sum(c[2] for c in COLUMNS) + 20)

        self.master.bind('<F5>', lambda _: self.refresh_jobs())
        self.master.protocol('WM_DELETE_WINDOW', self.on_close)
        self.master.after(100, self.poll_results)

    # ------------------------------------------------------------------ UI

    def setup_styles(self):
        default_font = tkfont.nametofont('TkDefaultFont')
        default_font.configure(size=10)
        self.font_bold = default_font.copy()
        self.font_bold.configure(weight='bold')
        self.font_title = default_font.copy()
        self.font_title.configure(size=14, weight='bold')
        self.font_mono = tkfont.Font(family='Courier', size=10)

        style = ttk.Style(self.master)
        style.theme_use('clam')
        style.configure('.', background=BG)
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG)
        style.configure('Card.TFrame', background='white', relief='solid', borderwidth=1)
        style.configure('Card.TLabel', background='white')
        style.configure('Muted.TLabel', background='white', foreground=MUTED)
        style.configure('Title.TLabel', background='white', font=self.font_title)
        style.configure('TLabelframe', background=BG)
        style.configure('TLabelframe.Label', background=BG, foreground=MUTED, font=self.font_bold)
        style.configure('TCheckbutton', background=BG)
        style.configure('Accent.TButton', background=ACCENT, foreground='white', font=self.font_bold)
        style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('disabled', '#93c5fd')])
        style.configure('Treeview', rowheight=26, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', font=self.font_bold, background='#e5e7eb')
        style.map('Treeview', background=[('selected', '#bfdbfe')], foreground=[('selected', '#111827')])

    def build_header(self):
        header = tk.Frame(self.master, bg=HEADER_BG, height=48)
        header.pack(fill='x')
        tk.Label(header, text="PBS Job Monitor", bg=HEADER_BG, fg=HEADER_FG,
                 font=self.font_title).pack(side='left', padx=16, pady=10)
        # Status dot is drawn rather than a text glyph: Tk builds without Xft lack most symbols
        self.conn_label = tk.Label(header, text="Disconnected", bg=HEADER_BG, fg='#9ca3af',
                                   font=self.font_bold)
        self.conn_label.pack(side='right', padx=(4, 16))
        self.conn_dot = tk.Canvas(header, width=12, height=12, bg=HEADER_BG, highlightthickness=0)
        self.conn_dot_id = self.conn_dot.create_oval(1, 1, 11, 11, fill='#9ca3af', outline='')
        self.conn_dot.pack(side='right')

    def build_connection_bar(self):
        bar = ttk.LabelFrame(self.master, text="Connection", padding=(10, 6))
        bar.pack(fill='x', padx=12, pady=(10, 4))

        ttk.Label(bar, text="Bookmark").grid(row=0, column=0, sticky='w', padx=(0, 6))
        self.bookmark_var = tk.StringVar()
        self.bookmark_combo = ttk.Combobox(bar, textvariable=self.bookmark_var, state='readonly', width=22)
        self.bookmark_combo.grid(row=0, column=1, sticky='w')
        self.bookmark_combo.bind('<<ComboboxSelected>>', self.on_bookmark_selected)
        ttk.Button(bar, text="Save", command=self.save_bookmark).grid(row=0, column=2, padx=(6, 2))
        ttk.Button(bar, text="Delete", command=self.delete_bookmark).grid(row=0, column=3, padx=(2, 16))

        self.host_var, self.user_var, self.password_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        fields = (("Host", self.host_var, 24, ''), ("User", self.user_var, 14, ''),
                  ("Password", self.password_var, 16, '*'))
        col = 4
        for label, var, width, show in fields:
            ttk.Label(bar, text=label).grid(row=0, column=col, sticky='w', padx=(8, 6))
            entry = ttk.Entry(bar, textvariable=var, width=width, show=show)
            entry.grid(row=0, column=col + 1, sticky='we')
            entry.bind('<Return>', lambda _: self.connect())
            col += 2
        bar.columnconfigure(5, weight=1)

        self.connect_btn = ttk.Button(bar, text="Connect", style='Accent.TButton', command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=col, padx=(12, 0))

    def build_toolbar(self):
        bar = ttk.Frame(self.master, padding=(12, 6))
        bar.pack(fill='x')

        self.chips_frame = ttk.Frame(bar)
        self.chips_frame.pack(side='left')

        self.refresh_btn = ttk.Button(bar, text="Refresh", command=self.refresh_jobs)
        self.refresh_btn.pack(side='right')
        ttk.Label(bar, text="s").pack(side='right', padx=(2, 8))
        self.interval_var = tk.StringVar(value=str(self.bookmarks.refresh_seconds))
        interval = ttk.Spinbox(bar, textvariable=self.interval_var, width=5, increment=5,
                               from_=AUTO_REFRESH_MIN_S, to=AUTO_REFRESH_MAX_S,
                               command=self.on_interval_changed)
        interval.pack(side='right')
        interval.bind('<Return>', self.on_interval_changed)
        interval.bind('<FocusOut>', self.on_interval_changed)
        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Auto-refresh every", variable=self.auto_var,
                        command=self.schedule_refresh).pack(side='right', padx=(8, 4))
        self.finished_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Include finished", variable=self.finished_var,
                        command=self.refresh_jobs).pack(side='right', padx=8)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self.populate_tree())
        ttk.Entry(bar, textvariable=self.search_var, width=22).pack(side='right')
        ttk.Label(bar, text="Search").pack(side='right', padx=(8, 4))

        self.render_chips()

    def build_main_area(self):
        self.paned = paned = ttk.PanedWindow(self.master, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=12, pady=(0, 6))

        # Job list
        list_frame = ttk.Frame(paned)
        self.tree = ttk.Treeview(list_frame, columns=[c[0] for c in COLUMNS], show='headings',
                                 selectmode='browse')
        for key, title, width, stretch in COLUMNS:
            self.tree.heading(key, text=title, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, minwidth=width if stretch else 50, stretch=stretch,
                             anchor='w' if key in ('name', 'queue', 'state') else 'center')
        for letter, (_, fg, bg) in STATES.items():
            self.tree.tag_configure(letter, foreground=fg, background=bg)
        self.add_scrollbars(list_frame, self.tree)
        self.tree.bind('<<TreeviewSelect>>', self.on_job_selected)
        paned.add(list_frame, weight=3)

        # Details card
        card = ttk.Frame(paned, style='Card.TFrame', padding=12)
        head = ttk.Frame(card, style='Card.TFrame', borderwidth=0)
        head.pack(fill='x')
        self.detail_title = ttk.Label(head, text="No job selected", style='Title.TLabel')
        self.detail_title.pack(side='left')
        self.detail_badge = tk.Label(head, text="", font=self.font_bold, padx=8, pady=2, bg='white')
        self.detail_badge.pack(side='right')
        self.detail_subtitle = ttk.Label(card, text="Select a job from the list to see its details.",
                                         style='Muted.TLabel')
        self.detail_subtitle.pack(fill='x', pady=(2, 8))

        self.summary_frame = ttk.Frame(card, style='Card.TFrame', borderwidth=0)
        self.summary_frame.pack(fill='x')
        self.summary_frame.columnconfigure(1, weight=1)

        ttk.Label(card, text="All attributes", style='Muted.TLabel').pack(anchor='w', pady=(10, 2))
        attr_frame = ttk.Frame(card, style='Card.TFrame', borderwidth=0)
        attr_frame.pack(fill='both', expand=True)
        self.attr_tree = ttk.Treeview(attr_frame, columns=('attr', 'value'), show='headings')
        self.attr_tree.heading('attr', text='Attribute', anchor='w')
        self.attr_tree.heading('value', text='Value', anchor='w')
        self.attr_tree.column('attr', width=170, stretch=False)
        self.attr_tree.column('value', width=280, stretch=False)
        self.add_scrollbars(attr_frame, self.attr_tree)
        self.attr_tree.bind('<Double-1>', self.copy_attribute)
        paned.add(card, weight=2)

    def add_scrollbars(self, frame, tree):
        """Grid tree with both scrollbars; unlike pack, grid keeps them visible when the pane shrinks"""
        vscroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        hscroll = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def build_status_bar(self):
        self.status_var = tk.StringVar(value="Not connected")
        tk.Label(self.master, textvariable=self.status_var, anchor='w', bg='#e5e7eb', fg='#374151',
                 padx=12, pady=3).pack(fill='x', side='bottom')

    def set_status(self, text):
        self.status_var.set(text)

    def set_indicator(self, text, color):
        self.conn_label.configure(text=text, fg=color)
        self.conn_dot.itemconfigure(self.conn_dot_id, fill=color)

    def set_connected(self, connected, text=None):
        if connected:
            self.set_indicator(text, '#34d399')
            self.connect_btn.configure(text="Disconnect")
        else:
            self.set_indicator(text or 'Disconnected', '#9ca3af')
            self.connect_btn.configure(text="Connect")

    # ------------------------------------------------------------ bookmarks

    def refresh_bookmark_list(self):
        self.bookmark_combo.configure(values=self.bookmarks.names())

    def on_bookmark_selected(self, _=None):
        site = self.bookmarks.sites.get(self.bookmark_var.get())
        if site:
            self.host_var.set(site['host'])
            self.user_var.set(site['user'])
            self.password_var.set(site.get('password', ''))

    def save_bookmark(self):
        host, user = self.host_var.get().strip(), self.user_var.get().strip()
        if not host or not user:
            messagebox.showwarning("Bookmark", "Fill in host and user first.")
            return
        name = simpledialog.askstring("Save bookmark", "Bookmark name:", parent=self.master,
                                      initialvalue=self.bookmark_var.get() or f"{user}@{host}")
        if not name:
            return
        try:
            self.bookmarks.put(name.strip(), host, user, self.password_var.get())
        except Exception as e:
            messagebox.showerror("Bookmark", f"Failed to save bookmark: {e}")
            return
        self.refresh_bookmark_list()
        self.bookmark_var.set(name.strip())
        self.set_status(f"Bookmark '{name.strip()}' saved")

    def delete_bookmark(self):
        name = self.bookmark_var.get()
        if not name:
            return
        if messagebox.askyesno("Delete bookmark", f"Delete bookmark '{name}'?"):
            self.bookmarks.delete(name)
            self.bookmark_var.set('')
            self.refresh_bookmark_list()
            self.set_status(f"Bookmark '{name}' deleted")

    # ------------------------------------------------------------------ SSH

    def run_async(self, func, on_done):
        """Run func in a worker thread; on_done(result, error) runs on the Tk thread"""
        def worker():
            try:
                self.results.put((on_done, func(), None))
            except Exception as e:
                self.results.put((on_done, None, e))
        threading.Thread(target=worker, daemon=True).start()

    def poll_results(self):
        try:
            while True:
                on_done, result, error = self.results.get_nowait()
                on_done(result, error)
        except queue.Empty:
            pass
        self.master.after(100, self.poll_results)

    def open_ssh(self, host, user, password):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Empty password falls back to SSH keys / agent
        client.connect(host, username=user, password=password or None, timeout=20)
        with self.ssh_lock:
            self.ssh = client

    def close_ssh(self):
        with self.ssh_lock:
            if self.ssh is not None:
                self.ssh.close()
            self.ssh = None

    def run_remote(self, command):
        """Run a command on the frontend, returning (exit_code, stdout, stderr)"""
        with self.ssh_lock:
            ssh = self.ssh
            transport = ssh.get_transport() if ssh is not None else None
            if ssh is None or transport is None or not transport.is_active():
                raise ConnectionError("Not connected")
            _, stdout, stderr = ssh.exec_command(command, timeout=30)
            out = stdout.read().decode(errors='replace')
            err = stderr.read().decode(errors='replace')
            return stdout.channel.recv_exit_status(), out, err

    def toggle_connection(self):
        if self.conn:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        host, user = self.host_var.get().strip(), self.user_var.get().strip()
        password = self.password_var.get()
        if not host or not user:
            messagebox.showwarning("Input Required", "Please fill in host and user.")
            return
        self.disconnect()
        self.connect_btn.configure(state='disabled')
        self.set_status(f"Connecting to {user}@{host}...")
        self.set_indicator("Connecting...", '#fbbf24')
        self.run_async(lambda: self.open_ssh(host, user, password),
                       lambda _, e: self.on_connected(host, user, password, e))

    def on_connected(self, host, user, password, error):
        self.connect_btn.configure(state='normal')
        if error:
            self.set_connected(False)
            if isinstance(error, paramiko.AuthenticationException):
                msg = "SSH authentication failed. Check user and password."
            else:
                msg = f"Could not connect to {host}:\n{error}"
            self.set_status("Connection failed")
            messagebox.showerror("Connection failed", msg)
            return
        self.conn = (host, user, password)
        self.set_connected(True, f"{user}@{host}")
        name = self.bookmark_var.get()
        if name in self.bookmarks.sites and self.bookmarks.last != name:
            self.bookmarks.last = name
            self.bookmarks.save()
        self.refresh_jobs()

    def disconnect(self):
        if self.refresh_job:
            self.master.after_cancel(self.refresh_job)
            self.refresh_job = None
        self.conn = None
        self.close_ssh()
        self.set_connected(False)
        self.set_status("Not connected")

    # ----------------------------------------------------------------- jobs

    def refresh_jobs(self):
        if not self.conn or self.loading:
            return
        self.loading = True
        self.refresh_btn.configure(state='disabled')
        self.set_status("Loading jobs...")
        user = self.conn[1]
        cmd = f"{QSTAT} -u {shlex.quote(user)}" + (" -x" if self.finished_var.get() else "")
        self.run_async(lambda: self.run_remote(cmd), self.on_jobs_loaded)

    def on_jobs_loaded(self, result, error):
        self.loading = False
        self.refresh_btn.configure(state='normal')
        if not self.conn:
            return  # disconnected while loading
        if error:
            self.set_status(f"Failed to load jobs: {error}")
            if not isinstance(error, ConnectionError):
                self.close_ssh()
            self.set_connected(False, "Connection lost")
            self.conn = None
            return
        code, out, err = result
        if code != 0:
            self.set_status(f"qstat failed: {err.strip() or f'exit code {code}'}")
        else:
            self.jobs = parse_job_list(out)
            host, user, _ = self.conn
            self.set_status(f"{user}@{host}  |  {len(self.jobs)} jobs  |  updated "
                            f"{datetime.now().strftime('%H:%M:%S')}")
        self.render_chips()
        self.populate_tree()
        self.schedule_refresh()

    def schedule_refresh(self):
        if self.refresh_job:
            self.master.after_cancel(self.refresh_job)
            self.refresh_job = None
        if self.auto_var.get() and self.conn:
            self.refresh_job = self.master.after(self.refresh_interval() * 1000, self.refresh_jobs)

    def refresh_interval(self):
        """Auto-refresh interval in seconds, clamped to the allowed range"""
        try:
            seconds = int(float(self.interval_var.get()))
        except ValueError:
            seconds = self.bookmarks.refresh_seconds
        return max(AUTO_REFRESH_MIN_S, min(AUTO_REFRESH_MAX_S, seconds))

    def on_interval_changed(self, _=None):
        seconds = self.refresh_interval()
        self.interval_var.set(str(seconds))
        if seconds != self.bookmarks.refresh_seconds:
            self.bookmarks.refresh_seconds = seconds
            try:
                self.bookmarks.save()
            except Exception as e:
                print(f"Error saving settings: {e}")
        self.schedule_refresh()

    def render_chips(self):
        """Clickable per-state counters that double as the state filter"""
        for widget in self.chips_frame.winfo_children():
            widget.destroy()
        counts = {}
        for job in self.jobs:
            counts[job['state']] = counts.get(job['state'], 0) + 1
        if self.state_filter not in counts:
            self.state_filter = None

        chips = [(None, f"All  {len(self.jobs)}", '#374151', '#e5e7eb')]
        for letter in sorted(counts, key=lambda s: list(STATES).index(s) if s in STATES else 99):
            label, fg, bg = STATES.get(letter, UNKNOWN_STATE)
            chips.append((letter, f"{label}  {counts[letter]}", fg, bg))

        for letter, text, fg, bg in chips:
            active = letter == self.state_filter
            chip = tk.Label(self.chips_frame, text=text, fg=fg, bg=bg, font=self.font_bold,
                            padx=10, pady=3, cursor='hand2',
                            highlightthickness=2, highlightbackground=fg if active else BG)
            chip.pack(side='left', padx=(0, 6))
            chip.bind('<Button-1>', lambda _, s=letter: self.set_state_filter(s))

    def set_state_filter(self, letter):
        self.state_filter = letter
        self.render_chips()
        self.populate_tree()

    def visible_jobs(self):
        needle = self.search_var.get().strip().lower()
        jobs = [j for j in self.jobs
                if (self.state_filter is None or j['state'] == self.state_filter)
                and (not needle or needle in f"{j['id']} {j['name']} {j['queue']}".lower())]
        if self.sort_column == 'id':
            key = lambda j: job_sort_key(j['id'])
        else:
            key = lambda j: j[self.sort_column].lower()
        return sorted(jobs, key=key, reverse=self.sort_reverse)

    def populate_tree(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for job in self.visible_jobs():
            label = STATES.get(job['state'], UNKNOWN_STATE)[0]
            values = [job[c[0]] for c in COLUMNS]
            values[3] = f"{job['state']}  {label}"
            self.tree.insert('', 'end', iid=job['id'], values=values, tags=(job['state'],))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
            self.tree.see(selected[0])

    def sort_by(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column, self.sort_reverse = column, False
        for key, title, _, _ in COLUMNS:
            arrow = (' v' if self.sort_reverse else ' ^') if key == column else ''
            self.tree.heading(key, text=title + arrow)
        self.populate_tree()

    # -------------------------------------------------------------- details

    def on_job_selected(self, _=None):
        selection = self.tree.selection()
        if not selection or not self.conn:
            return
        job = next((j for j in self.jobs if j['id'] == selection[0]), None)
        if job is None:
            return
        self.detail_request += 1
        request = self.detail_request
        self.detail_title.configure(text=f"Job {job['id']}")
        self.detail_subtitle.configure(text="Loading details...")
        finished = job['state'] in ('F', 'X') or self.finished_var.get()
        cmd = f"{QSTAT} -f{' -x' if finished else ''} {shlex.quote(job['id'])}"
        self.run_async(lambda: self.run_remote(cmd),
                       lambda r, e: self.on_details_loaded(request, job, r, e))

    def on_details_loaded(self, request, job, result, error):
        if request != self.detail_request:
            return  # a newer selection is already loading
        if error:
            self.detail_subtitle.configure(text=f"Failed to load details: {error}")
            return
        code, out, err = result
        if code != 0:
            self.detail_subtitle.configure(text=f"qstat -f failed: {err.strip() or code}")
            return
        attrs = parse_job_details(out)
        self.show_details(job, attrs)

    def show_details(self, job, attrs):
        state = attrs.get('job_state', job['state'])
        label, fg, bg = STATES.get(state, UNKNOWN_STATE)
        self.detail_title.configure(text=f"Job {job['id']}")
        self.detail_badge.configure(text=f" {label} ", fg=fg, bg=bg)
        self.detail_subtitle.configure(text=attrs.get('Job_Name', job['name']))

        for widget in self.summary_frame.winfo_children():
            widget.destroy()
        row = 0
        for title, keys in SUMMARY_FIELDS:
            values = [attrs[k] for k in keys if k in attrs]
            if not values:
                continue
            ttk.Label(self.summary_frame, text=title, style='Muted.TLabel').grid(
                row=row, column=0, sticky='nw', padx=(0, 12), pady=1)
            ttk.Label(self.summary_frame, text=' / '.join(values), style='Card.TLabel',
                      wraplength=360).grid(row=row, column=1, sticky='w', pady=1)
            row += 1

        self.attr_tree.delete(*self.attr_tree.get_children())
        for key, value in attrs.items():
            self.attr_tree.insert('', 'end', values=(key, value))
        font = tkfont.nametofont('TkDefaultFont')
        widest = max((font.measure(v) for v in attrs.values()), default=0)
        self.attr_tree.column('value', width=max(280, widest + 20))

    def copy_attribute(self, _=None):
        item = self.attr_tree.focus()
        if item:
            value = self.attr_tree.item(item, 'values')[1]
            self.master.clipboard_clear()
            self.master.clipboard_append(value)
            self.set_status("Value copied to clipboard")

    # ------------------------------------------------------------------ app

    def on_close(self):
        self.close_ssh()
        self.master.destroy()

    def run(self):
        """Start the application main loop"""
        self.master.mainloop()


def main():
    """Main entry point"""
    app = PBSJobMonitor()
    app.run()


if __name__ == "__main__":
    main()
