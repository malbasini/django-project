from ast import Import
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.

class ModelBeneficiario(models.Model):
    id = models.AutoField(primary_key=True)
    beneficiario = models.CharField(max_length=160,unique=False)
    descrizione = models.TextField(max_length=1500)
    email = models.EmailField(null=True)
    telefono = PhoneNumberField(null=True)
    sitoweb = models.URLField(null=True)
    iduser = models.BigIntegerField(null=False)
    
    class Meta:
        db_table = 'scadenzario_modelbeneficiario'
    
    def __str__(self):
        return self.beneficiario

class ModelScadenze(models.Model):
    id = models.AutoField(primary_key=True)
    beneficiario = models.CharField(max_length=100)
    datascadenza = models.DateField()
    importo = models.DecimalField(max_digits=19, decimal_places=2)
    sollecito = models.BooleanField()
    giorniritardo = models.SmallIntegerField(null=True)
    datapagamento = models.DateField(null=True)
    iduser = models.BigIntegerField()
    idbeneficiario = models.ForeignKey(ModelBeneficiario, on_delete = models.CASCADE, null=True, default=0)
    
    class Meta:
        db_table = 'scadenzario_modelscadenze'
    
    def __str__(self):
        return self.beneficiario


class ModelRicevute(models.Model):
    id = models.AutoField(primary_key=True)
    nomeFile = models.CharField(max_length=150)
    typeFile = models.CharField(max_length=50,null=True)
    contentFile = models.FileField()
    beneficiario = models.CharField(max_length=150)
    path = models.CharField(max_length=1450,null=True)
    scadenze = models.ForeignKey(ModelScadenze, on_delete = models.CASCADE, null=True,related_name = "related_scadenze",default=0)
    
    class Meta:
        db_table = 'scadenzario_modelricevute'
    
    
    def __str__(self):
        return self.nomeFile
