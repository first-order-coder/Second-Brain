# Supabase Integration

This document describes the safe, add-only, zero-downtime Supabase integration for the Second Brain application.

## 🎯 Overview

The integration introduces **Supabase Postgres** alongside existing SQLite with:
- **Phase 1 (Current):** Dual-write to both databases, read from SQLite
- **Phase 2 (Future):** Switch reads to Supabase after verification
- **Rollback:** Instant revert by changing `DB_READ_PRIMARY=sqlite`

## 🚫 What's NOT Changed

- ✅ PDF → flashcards → auto-open deck flow unchanged
- ✅ YouTube → 10 flashcards → auto-open deck unchanged
- ✅ All existing routes and API responses unchanged
- ✅ No Docker/env file deletions
- ✅ SQLite remains primary read DB until flag is flipped

## 📁 New Files Added

```
backend/
├── db/
│   ├── supabase_engine.py          # Supabase connection management
│   └── supabase/
│       └── schema.sql              # PostgreSQL schema
├── repo/
│   └── dual_repo.py                # Dual-write repository layer
└── test_supabase_integration.py    # Integration tests

scripts/
└── backfill_to_supabase.py         # One-time data migration

SUPABASE_INTEGRATION.md             # This documentation
```

## 🔧 Environment Variables

Add these to your `.env` file:

```bash
# Supabase (server-side only; never expose service key to browser)
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# DB connection strings
POSTGRES_URL=postgresql+psycopg://postgres:password@db.supabase.co:5432/postgres
DB_READ_PRIMARY=sqlite   # sqlite | supabase
DB_WRITE_SUPABASE=true   # true | false (dual-write flag)
DB_WRITE_SQLITE=true     # keep true for now

# Vector support (enable later)
ENABLE_PGVECTOR=true
```

## 🗄️ Database Schema

The Supabase schema mirrors the existing SQLite structure with PostgreSQL optimizations:

- **UUIDs** for better distributed system compatibility
- **Full-text search** indexes for better search performance
- **Vector support** ready for future embeddings
- **Automatic timestamps** with triggers
- **Foreign key constraints** for data integrity

## 🔄 Dual-Write Architecture

### Write Operations
All critical writes now go to **both** databases:
- PDF uploads
- Flashcard generation
- Status updates
- YouTube deck saves

### Read Operations
Controlled by `DB_READ_PRIMARY` environment variable:
- `sqlite` (default): Read from SQLite
- `supabase`: Read from Supabase with SQLite fallback

### Error Handling
- If Supabase write fails, operation continues with SQLite
- If Supabase read fails, automatically falls back to SQLite
- All errors are logged for monitoring

## 🏥 Health Checks

New endpoints added:

- `GET /healthz` - Basic health check (SQLite connectivity)
- `GET /readyz` - Readiness check (SQLite + Supabase + Redis)

## 📊 Monitoring

The integration includes:
- **Startup logging** of configuration
- **Dual-write success/failure** counters
- **Read source tracking** (sqlite|supabase)
- **Connection health** monitoring

## 🚀 Deployment Steps

### 1. Setup Supabase
1. Create a Supabase project
2. Run the schema from `backend/db/supabase/schema.sql`
3. Get your project URL and service role key

### 2. Configure Environment
1. Add environment variables to `.env`
2. Install new dependencies: `pip install psycopg2-binary`

### 3. Deploy with Dual-Write
1. Deploy with `DB_READ_PRIMARY=sqlite`
2. Verify dual-write is working via logs
3. Run backfill script: `python scripts/backfill_to_supabase.py`

### 4. Verify Data Parity
1. Check record counts match between databases
2. Test critical user flows (PDF upload, YouTube cards)
3. Monitor error logs for any issues

### 5. Cutover to Supabase (Future)
1. Set `DB_READ_PRIMARY=supabase` in staging
2. Run smoke tests
3. Deploy to production during quiet window
4. Monitor for 24-48 hours
5. Keep dual-write enabled for safety

## 🔄 Rollback Plan

If issues arise:
1. Set `DB_READ_PRIMARY=sqlite`
2. Redeploy or restart application
3. All reads immediately revert to SQLite
4. Dual-write continues for data consistency

## 🧪 Testing

Run the integration test:
```bash
cd backend
python test_supabase_integration.py
```

This tests:
- Supabase connection
- Dual-write functionality
- Read operations
- Configuration validation

## 📈 Future Enhancements

### Phase 2 Features
- **Vector search** with pgvector for semantic search
- **Real-time subscriptions** for live updates
- **Advanced analytics** with PostgreSQL functions
- **Backup and replication** via Supabase

### Performance Optimizations
- **Connection pooling** (already implemented)
- **Read replicas** for scaling reads
- **Caching layer** with Redis
- **Query optimization** with PostgreSQL-specific features

## 🔍 Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
   - Verify network connectivity to Supabase
   - Check PostgreSQL connection string format

2. **Dual-Write Failures**
   - Check logs for specific error messages
   - Verify both databases are accessible
   - Ensure schema matches between databases

3. **Read Fallback Issues**
   - Check `DB_READ_PRIMARY` setting
   - Verify SQLite database exists and is accessible
   - Check fallback logic in `dual_repo.py`

### Debug Commands

```bash
# Test Supabase connection
curl http://localhost:8000/readyz

# Check configuration
python -c "from backend.db.supabase_engine import SUPABASE_ENABLED; print(f'Supabase enabled: {SUPABASE_ENABLED}')"

# Run integration tests
python backend/test_supabase_integration.py
```

## 📝 Migration Notes

- **Zero downtime**: All changes are additive
- **Backward compatible**: Existing functionality unchanged
- **Gradual rollout**: Can be enabled/disabled via environment variables
- **Data safety**: Dual-write ensures no data loss during transition

## 🤝 Contributing

When making changes to the database layer:
1. Update both SQLite and Supabase schemas
2. Test dual-write functionality
3. Update backfill script if needed
4. Add integration tests for new features
5. Update this documentation
