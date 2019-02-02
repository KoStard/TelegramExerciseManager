# Generated by Django 2.1.4 on 2019-02-02 16:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0028_auto_20190119_1754'),
    ]

    operations = [
        migrations.CreateModel(
            name='Violation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('groupspecificparticipantdata', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.GroupSpecificParticipantData')),
            ],
            options={
                'verbose_name': 'Violation',
                'db_table': 'db_violation',
            },
        ),
        migrations.CreateModel(
            name='ViolationType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=20)),
                ('value', models.CharField(max_length=20)),
            ],
            options={
                'verbose_name': 'Violation Type',
                'db_table': 'db_violation_type',
            },
        ),
        migrations.AddField(
            model_name='violation',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.ViolationType'),
        ),
    ]
