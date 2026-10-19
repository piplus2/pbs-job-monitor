# PBS Job Monitor - Visual Guide

## Main Application Screenshot

![PBS Job Monitor GUI](./screenshot.png)

**Note**: The above image is a placeholder. After running the application with `python pbs_job_monitor.py`, take a screenshot and replace this file with the actual image.

### Screen Description

The main login screen shows:
- **Window Title**: "PBS Job Monitor" with a close button (✕) in the top-right corner
- **Input Fields**:
  - Frontend IP/Hostname field
  - Username field  
  - Password field (masked with dots)
- **Action Buttons**:
  - Green "Save & Login" button - primary action
  - Blue "Load Saved Credentials" button - for quick access to previously saved credentials

### Window Features

- Clean, modern design with gradient background
- Subtle visual pattern for depth
- Instructional text below buttons explaining the interface
- Footer showing app information

## Application States

### 1. Login Screen (Main)

Shown above - this is the initial state when first launching the application or after logging out.

### 2. Job List Screen

After saving credentials and clicking "Save & Login":
- Displays all your PBS jobs in a scrollable list
- Each job shows: `Job ID (State)` with color indicator
- Color-coded states for quick identification:
  - 🟢 Running, ⚫ Completed, 🔴 Held, etc.
- Filter dropdown to show only specific states
- Click any job to view full details

### 3. Job Details Screen

After clicking on a job in the list:
- Shows complete qstat output for that job
- Scrollable text area with monospace font
- Displays all job information including:
  - Batch name and ID
  - Queue, start/end times
  - Memory usage
  - Command being executed
- Close button to return to job list

## Window Behavior

### Resizability
- All windows are resizable for comfortable viewing
- Drag from window edges or corners

### Scrollbars
- Vertical scrollbars appear automatically when content is long
- Smooth scrolling for job lists and details

### Click Interaction
- Any job in the list changes cursor to pointer when hovered
- Click displays full job details in new window
- Detail windows have close button (X) in top-right corner

## Color Coding System

| State | Emoji | Meaning | Example Use Case |
|-------|-------|---------|------------------|
| R | 🟢 Green | Running | Analysis jobs processing data |
| C | ⚫ Gray | Completed | Reports generated successfully |
| H | 🔴 Red | Held | Jobs waiting to be released |
| E | 🔵 Blue | Exited | Script finished (check exit code) |
| S | 🟠 Orange | Suspending | Paused due to resource limits |
| T | 🟣 Purple | Terminating | Being killed manually |
| P | 🟡 Yellow | Pending | Waiting for scheduler allocation |

## Installation & First Run

1. **Install dependencies**:
   ```bash
   pip install cryptography
   ```

2. **Launch application**:
   ```bash
   python pbs_job_monitor.py
   ```

3. **First time setup**:
   - Enter PBS server IP, username, password
   - Click "Save & Login" 
   - Credentials saved encrypted to `credentials.enc`
   - Jobs displayed automatically

## Tips for Best Results

- Use a high-resolution display for better visual clarity
- Consider using SSH keys instead of passwords for enhanced security
- Take screenshot after first successful login to replace placeholder
- Check SCREENSHOT.md for detailed ASCII mockups of each screen state

## File Structure

```
pbs-job-monitor/
├── pbs_job_monitor.py    # Main GUI application
├── README.md              # Main documentation with screenshot
├── SCREENSHOT.md          # This visual guide
└── credentials.enc        # Encrypted credential storage (auto-generated)
```

## Future Enhancement Ideas

- Add actual PNG/JPEG screenshots when available
- Include before/after state comparisons
- Show error handling examples
- Document keyboard shortcuts if added later
