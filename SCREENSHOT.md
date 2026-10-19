# PBS Job Monitor - Visual Guide

## Application Screenshots

### 1. Login Screen

The first time you run the application, you'll see a clean login interface:

```
┌─────────────────────────────────────────────────────────┐
│                    PBS Job Monitor                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend IP/Hostname: [________________]               │
│                                                          │
│  Username:        [________________]                     │
│                                                          │
│  Password:             [________________*]               │
│                                                          │
│          [Save & Login]     [Load Saved Credentials]     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Green "Save & Login" button for primary action
- Blue "Load Saved Credentials" button for quick access
- Auto-fill on credential load

### 2. PBS Job List Screen

After logging in, view all your jobs:

```
┌───────────────────────────────────────────────────────────────────┐
│ PBS Jobs - Click to view details                          [X]     │
├───────────────────────────────────────────────────────────────────┤
│                                                          [Filter ▼] │
├───────────────────────────────────────────────────────────────────┤
│ Job 12345 (R): R                                                🟢 │
│ Job 12346 (C): C                                                ⚫ │
│ Job 12347 (H): H                                                🔴 │
│ Job 12348 (E): E                                                🔵 │
│ Job 12349 (S): S                                                🟠 │
│ Job 12350 (T): T                                                🟣 │
│ Job 12351 (P): P                                                🟡 │
├───────────────────────────────────────────────────────────────────┤
│ Filter by: [All ▼]                              [Apply Filter]    │
└───────────────────────────────────────────────────────────────────┘
```

**Features:**
- Color-coded job states for quick identification
- Click any job to see full details
- Dropdown filter for specific states
- Scrollable list for many jobs

### 3. Job Details Screen

Click on a job to view complete information:

```
┌───────────────────────────────────────────────────────────────────┐
│ Job Details: 12345 (R)                                      [X] │
├───────────────────────────────────────────────────────────────────┤
│ Batch Name:              my_analysis_job                         │
│ Batch ID:                12345                                   │
│ State:                   R                                       │
│ Job Run:                 0                                       │
│ Queue:                  batch                                    │
│ Start Time:     Mon Oct 19 10:30:00 2026                       │
│ End Time:          (running)                                   │
│ Elapsed Time:      02:15:30                                    │
│ Request Memory:    4096 MB                                     │
│ Used Memory:        2048 MB                                     │
│ Exit Code:              -                                       │
│ User:                 piuser                                    │
│ Host:                slurm01                                     │
│ Account:              research                                   │
│ Command:            python /path/to/script.py                   │
│ ...                                                              │
├───────────────────────────────────────────────────────────────────┤
│ [Close]                                                            │
└───────────────────────────────────────────────────────────────────┘
```

**Features:**
- All qstat -f output displayed
- Scrollable text area for long details
- Clean monospace font for easy reading
- Close button to return to job list

### 4. Filtered Job List

Use the filter dropdown to show only specific job states:

```
┌───────────────────────────────────────────────────────────────────┐
│ PBS Jobs - Click to view details                          [X]     │
├───────────────────────────────────────────────────────────────────┤
│                                                          [Filter ▼] │
├───────────────────────────────────────────────────────────────────┤
│ Filter by: [Running (R) ▼]                                       │
├───────────────────────────────────────────────────────────────────┤
│ Job 12345 (R): R                                                🟢 │
│ Job 12400 (R): R                                                🟢 │
│ Job 12401 (R): R                                                🟢 │
│ Job 12500 (R): R                                                🟢 │
├───────────────────────────────────────────────────────────────────┤
│ Filter by: [Completed (C) ▼]                                     │
│                                                          [Apply Filter] │
└───────────────────────────────────────────────────────────────────┘
```

### 5. Empty/No Jobs State

When no jobs are found:

```
┌───────────────────────────────────────────────────────────────────┐
│ PBS Jobs - Click to view details                          [X]     │
├───────────────────────────────────────────────────────────────────┤
│                                                          [Filter ▼] │
├───────────────────────────────────────────────────────────────────┤
│ No jobs found or SSH connection failed.                        │
│                                                                  │
│ Make sure:                                                       │
│   1. The frontend IP is correct                                 │
│   2. Username and password are valid                             │
│   3. PBS queue is accessible via SSH                             │
├───────────────────────────────────────────────────────────────────┤
│ Filter by: [All ▼]                              [Apply Filter]    │
└───────────────────────────────────────────────────────────────────┘
```

## Window Features

### Resizability
- Both windows are resizable for comfortable viewing
- Drag from window edges or corners

### Scrollbars
- Vertical scrollbars appear automatically when content is long
- Smooth scrolling for job lists and details

### Click Interaction
- Any job in the list can be clicked (cursor changes to pointer)
- Job details display full qstat output
- Close buttons on detail windows

### Status Bar
- Optional status bar at bottom shows connection state
- Displays "Connected" when SSH is working

## Color Coding Explanation

Each job state has a distinct color:

| State | Emoji | Meaning | Example Use Case |
|-------|-------|---------|------------------|
| 🟢 R | Running | Job actively processing data | Your analysis jobs running |
| ⚫ C | Completed | Finished successfully | Batch reports generated |
| 🔴 H | Held | Waiting to run | Jobs held for debugging |
| 🔵 E | Exited | Finished with code | Script completed (check exit code) |
| 🟠 S | Suspending | Pausing job | Memory limit reached |
| 🟣 T | Terminating | Killing job | Manual termination |
| 🟡 P | Pending | Waiting for resources | Jobs queued for allocation |

## Keyboard Shortcuts (Optional Enhancement)

Future enhancements could include:
- `Ctrl+C`: Copy selected job ID
- `Ctrl+F`: Find job in list
- `Esc`: Close detail window
