# Generated by Django 3.2.6 on 2021-10-28 15:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('poc', '0003_auto_20211027_1133'),
    ]

    operations = [
        migrations.CreateModel(
            name='Debt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(default=0.0, verbose_name='Сумма')),
                ('is_sended', models.BooleanField(default=False, verbose_name='Перевод осуществлен?')),
                ('is_confirmed', models.BooleanField(default=False, verbose_name='Перевод получен?')),
                ('check_obj', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='poc.check', verbose_name='Счет')),
                ('from_member', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='from_user', to='poc.member', verbose_name='Должник')),
                ('to_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='to_user', to='poc.member', verbose_name='Получатель')),
            ],
            options={
                'verbose_name': 'Долг',
                'verbose_name_plural': 'Долги',
            },
        ),
    ]
