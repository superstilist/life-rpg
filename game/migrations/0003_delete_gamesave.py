from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0002_character_alignment_character_companion_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="GameSave"),
    ]
