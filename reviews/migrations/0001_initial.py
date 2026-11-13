# Generated for the initial ReviewGuard schema.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('product_id', models.CharField(max_length=32, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('genre', models.CharField(blank=True, max_length=60)),
            ],
            options={'ordering': ['title']},
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, max_length=64)),
                ('rating', models.PositiveSmallIntegerField()),
                ('review_text', models.TextField()),
                ('account_age_days', models.PositiveIntegerField()),
                ('review_length', models.PositiveIntegerField()),
                ('is_fake', models.BooleanField(blank=True, help_text='Ground-truth label (training data only)', null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('device_id', models.CharField(blank=True, max_length=128, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('fake_probability', models.FloatField(blank=True, db_index=True, null=True)),
                ('predicted_fake', models.BooleanField(db_index=True, default=False)),
                ('reasons', models.TextField(blank=True)),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='reviews.movie')),
            ],
            options={'indexes': [models.Index(fields=['movie', 'predicted_fake'], name='rev_movie_fake_idx')]},
        ),
        migrations.CreateModel(
            name='TrustScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('n_reviews', models.PositiveIntegerField()),
                ('n_flagged', models.PositiveIntegerField()),
                ('fake_share', models.FloatField()),
                ('raw_avg', models.FloatField()),
                ('verified_avg', models.FloatField()),
                ('rating_inflation', models.FloatField()),
                ('trust_score', models.FloatField(db_index=True)),
                ('grade', models.CharField(max_length=16)),
                ('manipulated', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('movie', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='trust', to='reviews.movie')),
            ],
            options={'ordering': ['-trust_score']},
        ),
    ]
