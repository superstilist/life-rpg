import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('race', models.CharField(default='Human', max_length=50)),
                ('origin', models.CharField(default='Born to a humble village family', max_length=255)),
                ('traits', models.JSONField(default=list)),
                ('age', models.IntegerField(default=16)),
                ('turns', models.IntegerField(default=0)),
                ('current_location', models.CharField(default='Oakham Crossroad Village', max_length=100)),
                ('hp', models.IntegerField(default=100)),
                ('max_hp', models.IntegerField(default=100)),
                ('mana', models.IntegerField(default=50)),
                ('max_mana', models.IntegerField(default=50)),
                ('gold', models.IntegerField(default=50)),
                ('reputation', models.IntegerField(default=0)),
                ('strength', models.IntegerField(default=10)),
                ('agility', models.IntegerField(default=10)),
                ('intelligence', models.IntegerField(default=10)),
                ('charisma', models.IntegerField(default=10)),
                ('luck', models.IntegerField(default=10)),
                ('is_alive', models.BooleanField(default=True)),
                ('cause_of_death', models.CharField(blank=True, max_length=255, null=True)),
                ('score', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('item_type', models.CharField(choices=[('WEAPON', 'Weapon / Arms'), ('ARMOR', 'Armor / Shield'), ('POTION', 'Potion / Consumable'), ('ARTIFACT', 'Magic Artifact'), ('SCROLL', 'Spell Scroll')], default='POTION', max_length=20)),
                ('price', models.IntegerField(default=50)),
                ('icon_symbol', models.CharField(default='[+]', max_length=10)),
                ('hp_bonus', models.IntegerField(default=0)),
                ('mana_bonus', models.IntegerField(default=0)),
                ('strength_bonus', models.IntegerField(default=0)),
                ('agility_bonus', models.IntegerField(default=0)),
                ('intelligence_bonus', models.IntegerField(default=0)),
                ('charisma_bonus', models.IntegerField(default=0)),
                ('luck_bonus', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory', to='game.character')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.item')),
            ],
        ),
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.IntegerField()),
                ('turn', models.IntegerField()),
                ('title', models.CharField(max_length=150)),
                ('text', models.TextField()),
                ('log_type', models.CharField(choices=[('quest', 'Quest / Battle'), ('event', 'World Encounter'), ('magic', 'Arcane Meditation'), ('system', 'Life Milestone'), ('death', 'Fallen Hero')], default='event', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='game.character')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
    ]
