# Generated by Django 2.1.4 on 2019-01-19 08:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_auto_20190119_1148'),
    ]

    operations = [
        migrations.AddField(
            model_name='administratorpage',
            name='participant_group',
            field=models.OneToOneField(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.ParticipantGroup'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='botbinding',
            name='participant_group',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.ParticipantGroup'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='groupspecificparticipantdata',
            name='participant_group',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.ParticipantGroup'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subjectgroupbinding',
            name='participant_group',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.ParticipantGroup'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='telegraphpage',
            name='participant_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.ParticipantGroup'),
        ),
    ]
