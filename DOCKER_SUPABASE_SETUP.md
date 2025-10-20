# Docker Setup with Supabase Integration

This guide explains how to configure Docker services with the new Supabase integration.

## 🐳 Docker Configuration Updates

The Docker services have been updated to support Supabase integration:

### Updated Files:
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment  
- `backend/Dockerfile` - Added PostgreSQL client dependencies

### New Environment Variables

All Docker services now support these Supabase environment variables:

```bash
# Supabase configuration (optional)
SUPABASE_URL=${SUPABASE_URL:-}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY:-}
POSTGRES_URL=${POSTGRES_URL:-}

# Database configuration
DB_READ_PRIMARY=${DB_READ_PRIMARY:-sqlite}
DB_WRITE_SUPABASE=${DB_WRITE_SUPABASE:-true}
DB_WRITE_SQLITE=${DB_WRITE_SQLITE:-true}
ENABLE_PGVECTOR=${ENABLE_PGVECTOR:-true}
```

## 🚀 Quick Start

### 1. Without Supabase (Default)
```bash
# Just run with existing configuration
docker-compose up
```

The app will work exactly as before, using only SQLite.

### 2. With Supabase
```bash
# Create .env file with Supabase configuration
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
POSTGRES_URL=postgresql+psycopg://postgres:your_password@db.your-project-id.supabase.co:5432/postgres
DB_READ_PRIMARY=sqlite
DB_WRITE_SUPABASE=true
DB_WRITE_SQLITE=true
ENABLE_PGVECTOR=true
EOF

# Run with Supabase integration
docker-compose up
```

## 🔧 Docker Service Details

### Backend Service
- **Port**: 8000
- **Health Check**: `GET /healthz` (updated from root endpoint)
- **Dependencies**: Redis
- **Volumes**: 
  - `./backend/uploads:/app/uploads`
  - `./backend/pdf_flashcards.db:/app/pdf_flashcards.db`

### Worker Service (Celery)
- **Command**: `celery -A worker_tasks worker --loglevel=info`
- **Environment**: Same as backend service
- **Dependencies**: Redis

### Frontend Service
- **Port**: 3000
- **Environment**: `NEXT_PUBLIC_API_URL=http://backend:8000`

### Redis Service
- **Port**: 6379
- **Image**: `redis:7-alpine`

## 📊 Health Checks

### Development (`docker-compose.yml`)
- Basic health checks on root endpoints

### Production (`docker-compose.prod.yml`)
- **Backend**: `GET /healthz` - Basic health check
- **Frontend**: `GET /` - Frontend health check
- **Interval**: 30s, **Timeout**: 10s, **Retries**: 3

## 🧪 Testing Docker Setup

### 1. Test Basic Functionality
```bash
# Start services
docker-compose up -d

# Check health
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz

# Test frontend
curl http://localhost:3000/
```

### 2. Test Supabase Integration
```bash
# Check if Supabase is enabled
curl http://localhost:8000/readyz | jq '.supabase'

# Should return "disabled" if not configured, "healthy" if working
```

### 3. Run Integration Tests
```bash
# Run tests inside the backend container
docker-compose exec backend python test_supabase_integration.py
```

## 🔄 Migration Workflow

### 1. Deploy with Dual-Write
```bash
# Deploy with SQLite as primary read
docker-compose up -d
```

### 2. Run Backfill (if Supabase enabled)
```bash
# Run backfill script
docker-compose exec backend python scripts/backfill_to_supabase.py
```

### 3. Verify Data Parity
```bash
# Check record counts
docker-compose exec backend python -c "
from repo.dual_repo import get_read_session
import sqlite3

# Check SQLite
with sqlite3.connect('pdf_flashcards.db') as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM pdfs')
    print(f'SQLite PDFs: {cursor.fetchone()[0]}')
    cursor.execute('SELECT COUNT(*) FROM flashcards')
    print(f'SQLite Flashcards: {cursor.fetchone()[0]}')
"
```

### 4. Cutover to Supabase (Future)
```bash
# Update environment
echo "DB_READ_PRIMARY=supabase" >> .env

# Restart services
docker-compose restart backend worker
```

## 🛠️ Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   ```bash
   # Check if libpq-dev is installed
   docker-compose exec backend apt list --installed | grep libpq
   
   # Check connection string format
   echo $POSTGRES_URL
   ```

2. **Health Check Failures**
   ```bash
   # Check backend logs
   docker-compose logs backend
   
   # Test health endpoint manually
   docker-compose exec backend curl -f http://localhost:8000/healthz
   ```

3. **Dual-Write Issues**
   ```bash
   # Check configuration
   docker-compose exec backend python -c "
   from repo.dual_repo import DB_READ_PRIMARY, WRITE_SUPABASE, WRITE_SQLITE
   print(f'Read: {DB_READ_PRIMARY}, Write SQLite: {WRITE_SQLITE}, Write Supabase: {WRITE_SUPABASE}')
   "
   ```

### Debug Commands

```bash
# Check environment variables
docker-compose exec backend env | grep -E "(SUPABASE|DB_|POSTGRES)"

# Check database connectivity
docker-compose exec backend python -c "
from db.supabase_engine import SUPABASE_ENABLED
print(f'Supabase enabled: {SUPABASE_ENABLED}')
"

# View logs
docker-compose logs -f backend
docker-compose logs -f worker
```

## 📝 Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | (empty) | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | (empty) | Supabase service role key |
| `POSTGRES_URL` | (empty) | PostgreSQL connection string |
| `DB_READ_PRIMARY` | `sqlite` | Primary database for reads |
| `DB_WRITE_SUPABASE` | `true` | Enable Supabase writes |
| `DB_WRITE_SQLITE` | `true` | Enable SQLite writes |
| `ENABLE_PGVECTOR` | `true` | Enable vector support |

## 🔒 Security Notes

- **Never expose** `SUPABASE_SERVICE_ROLE_KEY` to the frontend
- **Use environment variables** for all sensitive configuration
- **Rotate keys** regularly in production
- **Monitor access logs** for unauthorized usage

## 🚀 Production Deployment

For production deployment:

1. **Use production compose file**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Set up proper secrets management**:
   ```bash
   # Use Docker secrets or external secret management
   echo "your_service_role_key" | docker secret create supabase_key -
   ```

3. **Configure monitoring**:
   ```bash
   # Set up health check monitoring
   curl -f http://your-domain:8000/readyz
   ```

4. **Enable logging**:
   ```bash
   # Configure log aggregation
   docker-compose logs -f > app.log
   ```
