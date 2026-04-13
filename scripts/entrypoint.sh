#!/usr/bin/env bash
set -e

echo "--- Waiting for Redis ---"
until python -c "import redis; redis.from_url('${BLOG_REDIS_URL:-redis://redis:6379/0}').ping()" 2>/dev/null; do
    echo "Redis not ready, retrying in 2s..."
    sleep 2
done
echo "Redis is up."

echo "--- Running migrations ---"
python manage.py migrate --no-input

echo "--- Collecting static files ---"
python manage.py collectstatic --no-input --clear -v 0

echo "--- Compiling translations ---"
python manage.py compilemessages -v 0

echo "--- Seeding database (if requested) ---"
if [ "${BLOG_SEED_DB:-false}" = "true" ]; then
    python manage.py seed
fi

echo "--- Starting application ---"
exec "$@"
