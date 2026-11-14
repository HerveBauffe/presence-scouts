# Troisième Troupe
Application de prise de présences pour la Troisième Troupe des Ardents de Saint-Michel

## Setup
### Prerequisites
- Python3

### Starting the app
```
python3 -m venv venv
```
Activate the venv
```
source venv/bin/activate
```
Install dependencies
```
pip3 install -r requirements.txt
```
You should be able to start the app with
```
python3 run.py
```

### Customizing
You can customize the header, footer and the favicon as you wish

### Making it a system service
```
sudo nano /etc/systemd/system/presence-scouts.service
```
Then write
```
[Unit]
Description=Presence App Flask
After=network.target

[Service]
User=yourUSER
Group=www-data
WorkingDirectory=/home/yourUSER/presence-scouts
Environment="PATH=/home/yourUSER/presence-scouts/venv/bin"
ExecStart=/home/yourUSER/presence-scouts/venv/bin/gunicorn --workers 3 --b>

[Install]
WantedBy=multi-user.target
```
