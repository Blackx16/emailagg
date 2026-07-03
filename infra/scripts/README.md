# EmailAgg Paid Tier - Backup Scripts

This directory contains utility scripts exclusive to the paid tier of EmailAgg. 

## Automated Log Backups (`backup_logs.sh`)

This script automates the backup of all Docker container logs to a linked Google Drive using `rclone`. This is crucial for long-term storage and compliance without risking VPS disk exhaustion.

### Setup Instructions

1. **Install Rclone**: 
   Ensure `rclone` is installed on your server.
   ```bash
   curl https://rclone.org/install.sh | sudo bash
   ```

2. **Configure Google Drive OAuth**:
   On your local machine (where you have a web browser), install `rclone` and run:
   ```bash
   rclone authorize "drive"
   ```
   Log into your Google account and grant permissions. It will output a JSON block.

3. **Configure VPS Rclone**:
   On your server, create the `rclone.conf` file:
   ```bash
   sudo mkdir -p /root/.config/rclone
   sudo nano /root/.config/rclone/rclone.conf
   ```
   Paste the following, substituting the JSON from step 2 for the `token`:
   ```ini
   [gdrive]
   type = drive
   scope = drive
   token = {"access_token":"...","token_type":"Bearer","refresh_token":"...","expiry":"..."}
   ```

4. **Install the Cron Job**:
   Set the script to run daily at midnight by running:
   ```bash
   (sudo crontab -l 2>/dev/null; echo "0 0 * * * $(pwd)/backup_logs.sh >> /var/log/backup_logs.log 2>&1") | sudo crontab -
   ```
