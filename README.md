# PBS Job Monitor

A simple GUI application to check and monitor PBS (Portable Batch System) job states with encrypted local credential storage.

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **🔐 Secure Login**: Enter frontend IP/hostname, username, and password
- **💾 Encrypted Credentials**: Passwords are saved locally using Fernet encryption
- **📊 Job List View**: Display all your PBS jobs with their current states (color-coded)
- **🎯 Filter by State**: Filter jobs by state (Running, Completed, Held, etc.)
- **🔍 Detailed View**: Click on any job to view full job details

## Screenshots

![PBS Job Monitor GUI](screenshot.png)

*The PBS Job Monitor application shows a clean login interface where you enter your PBS server credentials. The green "Save & Login" button saves credentials locally encrypted, and the blue "Load Saved Credentials" button allows quick access without re-entering passwords.*

**Note**: Replace `screenshot.png` with an actual screenshot image file when available. The current placeholder can be replaced by taking a screenshot after running:
```bash
python pbs_job_monitor.py
```

## Requirements

- Python 3.7+
- `cryptography` package for encryption
- SSH access to PBS server

### Installation

1. **Install dependencies:**
   ```bash
   pip install cryptography
   ```

2. **Run the application:**
   ```bash
   python pbs_job_monitor.py
   ```

## Usage

### First Time Setup

1. Launch the application:
   ```bash
   python pbs_job_monitor.py
   ```

2. You'll see the login screen with two options:
   - **Save & Login**: Enter your PBS server credentials and save them encrypted locally
   - **Load Saved Credentials**: Load previously saved credentials (credentials are stored securely in `credentials.enc`)

3. After saving, you'll automatically see your job list

### Viewing Jobs

- **All jobs** are displayed by default with color-coded states
- Click on any job to see full details
- Use the filter dropdown to show only specific job states
- Jobs are sorted by JobID

## Color Legend

| State | Color | Description |
|-------|-------|-------------|
| 🟢 R (Running) | Green | Job is currently running |
| ⚫ C (Completed) | Gray | Job has finished successfully |
| 🔴 H (Held) | Red | Job is held/pending release |
| 🔵 E (Exited) | Blue | Job completed with exit code |
| 🟠 S (Suspending) | Orange | Job is being suspended |
| 🟣 T (Terminating) | Purple | Job is being terminated |
| 🟡 P (Pending) | Yellow | Job is pending allocation |

## Security Notes

- ✅ Credentials are encrypted locally using Fernet encryption
- ✅ Encryption key is stored with the credentials file
- ✅ Never share your password or `credentials.enc` file
- ✅ Consider using SSH keys for more secure authentication
- ✅ Credentials are only decrypted in memory during session

## Project Structure

```
pbs-job-monitor/
├── pbs_job_monitor.py    # Main GUI application (341 lines)
├── README.md              # This documentation
├── SCREENSHOT.md          # Detailed UI guide with ASCII mockups
└── credentials.enc        # Encrypted credentials (auto-generated on login)
```

### Code Highlights

- **Single Class Design**: `PBSJobMonitor` class handles all functionality
- **Secure Storage**: Fernet encryption for credentials
- **Clean UI**: Tkinter with modern styling and colors
- **Error Handling**: Graceful handling of SSH failures and timeouts
- **Filter Functionality**: Filter jobs by state with dropdown

## Troubleshooting

### "No jobs found" Error

Make sure:
1. The frontend IP is correct and accessible
2. Username and password are valid for PBS server
3. You have permission to view your jobs with `qstat -u <user>`

### SSH Connection Failed

- Verify you can SSH to the PBS server from your terminal
- Check that `qstat` command is installed on the PBS server
- Ensure network connectivity between your machine and PBS server

### Import Error: cryptography

Install the cryptography package:
```bash
pip install cryptography
```

## License

MIT License - Feel free to use and modify as needed.

## Author

Created by pingl for PBS job monitoring tasks

## Contributing

Feel free to:
- Report bugs
- Suggest features (e.g., job submission, cancellation)
- Improve the UI/UX
- Add support for other queue management systems

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review PBS documentation for your server setup
3. Ensure SSH connectivity to PBS server is working