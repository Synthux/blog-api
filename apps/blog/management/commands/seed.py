import logging
import random

from django.core.management.base import BaseCommand

logger = logging.getLogger('blog')


class Command(BaseCommand):
    help = 'Populate the database with test users, posts, categories, tags, and comments.'

    def handle(self, *args, **options) -> None:
        from apps.blog.constants import PostStatus
        from apps.blog.models import Category, Comment, Post, Tag
        from apps.users.models import User

        self.stdout.write('Seeding database...')

        # Users
        users = []
        for i in range(1, 5):
            email = f'user{i}@example.com'
            u, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'User{i}',
                    'last_name': 'Test',
                    'preferred_language': random.choice(['en', 'ru', 'kk']),
                },
            )
            if created:
                u.set_password('test1234')
                u.save()
            users.append(u)

        # Categories
        for name_en, name_ru, name_kk, slug in [
            ('Technology', 'Технологии', 'Технология', 'technology'),
            ('Travel', 'Путешествия', 'Саяхат', 'travel'),
            ('Food', 'Еда', 'Тамақ', 'food'),
        ]:
            Category.objects.get_or_create(
                slug=slug,
                defaults={'name_en': name_en, 'name_ru': name_ru, 'name_kk': name_kk},
            )

        cats = list(Category.objects.all())
        tags = [
            Tag.objects.get_or_create(slug=s, defaults={'name': s})[0]
            for s in ['python', 'django', 'api', 'web', 'rest', 'json']
        ]

        # Posts
        for i in range(1, 15):
            slug = f'test-post-{i}'
            if not Post.objects.filter(slug=slug).exists():
                post = Post.objects.create(
                    author=random.choice(users),
                    title=f'Test Post {i}',
                    slug=slug,
                    body='Sample body content. ' * 10,
                    category=random.choice(cats),
                    status=PostStatus.PUBLISHED if i <= 10 else PostStatus.DRAFT,
                )
                post.tags.set(random.sample(tags, 2))
                for j in range(1, 4):
                    Comment.objects.create(
                        post=post,
                        author=random.choice(users),
                        body=f'Comment {j} on post {i}',
                    )

        self.stdout.write(self.style.SUCCESS('Database seeded successfully.'))
        logger.info('Database seeded via management command')
