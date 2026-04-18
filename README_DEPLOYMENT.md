# Tweet Tracker VPS Deployment

## One-Command Deployment

Deploy Tweet Tracker on any VPS with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/your-repo/tweet-tracker/main/deploy.sh | bash
```

Or if you have the files locally:

```bash
chmod +x deploy.sh && ./deploy.sh
```

## Prerequisites

- Any Linux VPS (Ubuntu, CentOS, Debian, etc.)
- At least 512MB RAM, 1GB recommended
- 1GB+ disk space
- Internet access

## What the Script Does

1. **Installs Docker** if not present
2. **Installs Docker Compose** if not present  
3. **Creates data directory** for persistent storage
4. **Builds Docker image** with all dependencies
5. **Starts the application** in detached mode
6. **Verifies deployment** and shows access URL

## After Deployment

### Access Your Instance
- **Web Interface**: `http://YOUR-VPS-IP:5000`
- **API Endpoints**: `http://YOUR-VPS-IP:5000/api/`
- **API Documentation**: `http://YOUR-VPS-IP:5000/docs`

### Quick Test
```bash
# Check if running
curl http://YOUR-VPS-IP:5000/api/stats

# Get users
curl http://YOUR-VPS-IP:5000/api/users
```

### Management Commands

```bash
# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# Update to latest version
docker-compose pull && docker-compose up -d

# Access container shell
docker-compose exec tweet-tracker bash
```

## Data Persistence

- **Database**: Stored in `./data/tweets.db`
- **Settings**: Stored in `./settings.json`
- **Environment**: Stored in `./env`
- **Logs**: Accessible via `docker-compose logs`

## Security Considerations

1. **Firewall**: Configure to only allow necessary ports
   ```bash
   sudo ufw allow 22    # SSH
   sudo ufw allow 5000  # Tweet Tracker
   sudo ufw enable
   ```

2. **Reverse Proxy** (optional but recommended):
   ```bash
   # Install Nginx
   sudo apt update && sudo apt install nginx
   
   # Create config
   sudo nano /etc/nginx/sites-available/tweet-tracker
   ```

   Nginx config:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **SSL Certificate** (optional):
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Environment Configuration

Create `.env` file before deployment:

```bash
# Database (optional - defaults to local SQLite)
TURSO_DATABASE_URL=your-turso-url
TURSO_AUTH_TOKEN=your-turso-token

# Server (optional)
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Custom settings (optional)
NITTER_BASE=https://nitter.net
REQUEST_TIMEOUT=30
MAX_RETRIES=5
```

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs tweet-tracker
```

### Rebuild Container
```bash
docker-compose down
docker-compose up --build -d
```

### Reset Data
```bash
docker-compose down
sudo rm -rf data/
docker-compose up -d
```

### Port Already in Use
```bash
# Check what's using port 5000
sudo netstat -tlnp | grep :5000

# Kill the process
sudo kill -9 PID
```

## Performance Tips

1. **Memory**: Monitor with `docker stats`
2. **Disk Space**: Clean old logs: `docker system prune`
3. **Database**: Consider using Turso for production
4. **Backup**: Regularly backup `./data/` directory

## Scaling

For high-traffic deployments:

1. **Use Reverse Proxy**: Nginx or Caddy
2. **Add SSL**: Let's Encrypt certificates
3. **Monitor**: Set up health checks
4. **Backup**: Automated database backups
5. **Load Balancer**: Multiple instances behind load balancer

## Support

If deployment fails:
1. Check `docker-compose logs` for errors
2. Verify Docker is running: `docker --version`
3. Check port availability: `netstat -tlnp | grep :5000`
4. Ensure sufficient disk space: `df -h`

## Manual Deployment (Alternative)

If the script doesn't work, deploy manually:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Deploy
docker-compose up --build -d
```
