#!/usr/bin/env bash
# Starts the Blog API project from zero with a single command.
set -eE  # exit immediately on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}! $1${NC}"; }
fail() { echo -e "${RED}✗ FAILED at step: $1${NC}"; exit 1; }

# ---------- Step 1: Validate environment variables ----------
echo "Step 1: Checking environment variables..."
ENV_FILE="settings/.env"
if [ ! -f "$ENV_FILE" ]; then
    fail ".env file not found at $ENV_FILE. Copy settings/.env.example and fill it in."
fi

REQUIRED_VARS=(BLOG_SECRET_KEY BLOG_REDIS_URL BLOG_ENV_ID)
for var in "${REQUIRED_VARS[@]}"; do
    val=$(grep -E "^${var}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
    if [ -z "$val" ]; then
        fail "Required variable '$var' is missing or blank in $ENV_FILE"
    fi
done
ok "Environment variables OK"

# ---------- Step 2: Virtual environment and dependencies ----------
echo "Step 2: Installing dependencies..."
if [ ! -d "env" ]; then
    python3 -m venv env || fail "Creating virtual environment"
fi
# shellcheck disable=SC1091
source env/bin/activate || fail "Activating virtual environment"
pip install -r requirements/dev.txt -q || fail "Installing dependencies"
ok "Dependencies installed"

# ---------- Step 3: Migrations ----------
echo "Step 3: Running migrations..."
python manage.py migrate --no-input || fail "Running migrations"
ok "Migrations applied"

# ---------- Step 4: Static files ----------
echo "Step 4: Collecting static files..."
python manage.py collectstatic --no-input --clear -v 0 2>/dev/null || \
    warn "collectstatic had warnings (continuing)"
ok "Static files collected"

# ---------- Step 5: Compile translations ----------
echo "Step 5: Compiling translation files..."
python manage.py compilemessages -v 0 || fail "Compiling translations"
ok "Translations compiled"

# ---------- Step 6: Superuser ----------
echo "Step 6: Creating superuser..."
SUPERUSER_EMAIL="admin@blog.com"
SUPERUSER_PASSWORD="Admin1234!"
python manage.py shell -c "
from apps.users.models import User
if not User.objects.filter(email='${SUPERUSER_EMAIL}').exists():
    User.objects.create_superuser('${SUPERUSER_EMAIL}', '${SUPERUSER_PASSWORD}',
                                   first_name='Admin', last_name='User')
    print('created')
else:
    print('already exists, skipping')
" || fail "Creating superuser"
ok "Superuser ready"

# ---------- Step 7: Seed database ----------
echo "Step 7: Seeding test data..."
python manage.py shell -c "
import random
from apps.users.models import User
from apps.blog.models import Category, Tag, Post, Comment
from apps.blog.constants import PostStatus

users = []
for i in range(1, 5):
    email = f'user{i}@example.com'
    u, _ = User.objects.get_or_create(email=email,
        defaults=dict(first_name=f'User{i}', last_name='Test',
                      preferred_language=random.choice(['en','ru','kk'])))
    if _:
        u.set_password('test1234')
        u.save()
    users.append(u)

for en, ru, kk, slug in [
    ('Technology','Технологии','Технология','technology'),
    ('Travel','Путешествия','Саяхат','travel'),
    ('Food','Еда','Тамақ','food'),
]:
    Category.objects.get_or_create(slug=slug,
        defaults=dict(name_en=en, name_ru=ru, name_kk=kk))

cats = list(Category.objects.all())
tags = [Tag.objects.get_or_create(slug=s, defaults={'name': s})[0]
        for s in ['python','django','api','web','rest','json']]

for i in range(1, 15):
    slug = f'test-post-{i}'
    if not Post.objects.filter(slug=slug).exists():
        p = Post.objects.create(
            author=random.choice(users),
            title=f'Test Post {i}',
            slug=slug,
            body='Sample body content. ' * 10,
            category=random.choice(cats),
            status=PostStatus.PUBLISHED if i <= 10 else PostStatus.DRAFT,
        )
        p.tags.set(random.sample(tags, 2))
        for j in range(1, 4):
            Comment.objects.create(post=p, author=random.choice(users),
                                   body=f'Comment {j} on post {i}')

print('Seeded successfully')
" || fail "Seeding database"
ok "Database seeded"

# ---------- Step 8: Start server ----------
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Blog API is ready! ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "  API:       http://127.0.0.1:8000/api/"
echo "  Swagger:   http://127.0.0.1:8000/api/docs/"
echo "  ReDoc:     http://127.0.0.1:8000/api/redoc/"
echo "  Schema:    http://127.0.0.1:8000/api/schema/"
echo "  Admin:     http://127.0.0.1:8000/admin/"
echo ""
echo "  Superuser:"
echo "    Email:    ${SUPERUSER_EMAIL}"
echo "    Password: ${SUPERUSER_PASSWORD}"
echo ""

python manage.py runserver || fail "Starting development server"
