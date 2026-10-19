# PBS Job Monitor

A simple GUI application to check and monitor PBS (Portable Batch System) job states with encrypted local credential storage.

## Features

- **Secure Login**: Enter frontend IP/hostname, username, and password
- **Encrypted Credentials**: Passwords are saved locally using Fernet encryption
- **Job List View**: Display all your PBS jobs with their current states
- **Filter by State**: Filter jobs by state (Running, Completed, Held, etc.)
- **Detailed View**: Click on any job to view full job details

## Requirements

- Python 3.7+
- `cryptography` package for encryption
- SSH access to PBS server

### Installation

```bash
pip install cryptography
```

## Usage

1. Run the application:
   ```bash
   python pbs_job_monitor.py
   ```

2. On first run, click "Load Saved Credentials" or enter credentials and click "Save & Login"

3. View your PBS jobs with their states (color-coded)

4. Click on any job to see full details

## Color Legend

- 🟢 **Running (R)**: Job is currently running
- ⚫ **Completed (C)**: Job has finished successfully
- 🔴 **Held (H)**: Job is held/pending release
- 🔵 **Exited (E)**: Job completed with exit code
- 🟠 **Suspending (S)**: Job is being suspended
- 🟣 **Terminating (T)**: Job is being terminated
- 🟡 **Pending (P)**: Job is pending allocation

## Security Notes

- Credentials are encrypted locally using Fernet encryption
- Encryption key is stored with the credentials file
- Never share your password or credentials file with others
- Consider using SSH keys for more secure authentication

## Project Structure

```
pbs-job-monitor/
├── pbs_job_monitor.py   # Main application
├── README.md            # This file
└── credentials.enc      # Encrypted credentials (auto-generated)
```

## License

MIT License - Feel free to use and modify as needed.
