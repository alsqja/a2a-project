# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Chat(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    contents = models.TextField(blank=True, null=True)
    chat_room = models.ForeignKey('ChatRoom', models.DO_NOTHING)
    from_field = models.ForeignKey('Company', models.DO_NOTHING, db_column='from_id', blank=True, null=True)  # Field renamed because it was a Python reserved word.
    to = models.ForeignKey('Company', models.DO_NOTHING, related_name='chat_to_set')

    class Meta:
        managed = False
        db_table = 'chat'


class ChatRoom(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    lead = models.OneToOneField('Lead', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'chat_room'


class Company(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, blank=True, null=True)
    homepage = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    key_executive = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    sales = models.FloatField(blank=True, null=True)
    total_funding = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company'


class CompanyFile(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    company = models.ForeignKey(Company, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company_file'


class Lead(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    lead_score = models.FloatField(blank=True, null=True)
    lead_company = models.ForeignKey(Company, models.DO_NOTHING)
    source_company = models.ForeignKey(Company, models.DO_NOTHING, related_name='lead_source_company_set')

    class Meta:
        managed = False
        db_table = 'lead'
