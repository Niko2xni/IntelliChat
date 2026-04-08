from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0003_student_account_type_student_leader_organization_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='attachments',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
