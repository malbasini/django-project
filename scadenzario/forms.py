from cProfile import label
from calendar import calendar
from datetime import timezone
from typing_extensions import Required
from wsgiref.validate import validator
from django import forms
from django.contrib.auth.models import User
from pkg_resources import require
from .models import ModelBeneficiario,ModelScadenze
from phonenumber_field.formfields import PhoneNumberField
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox


class FormRegistrazioneUser(forms.ModelForm):

    username = forms.CharField(widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput())
    password = forms.CharField(widget=forms.PasswordInput())
    conferma_password = forms.CharField(widget=forms.PasswordInput())
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(api_params={'hl': 'cl', 'onload': 'onLoadFunc'}))

    class Meta:
        model = User
        fields = ["username", "email", "password", "conferma_password","captcha"]

    def clean(self):
        """https://docs.djangoproject.com/en/dev/ref/forms/validation/#cleaning-and-validating-fields-that-depend-on-each-other"""
        super().clean()
        password = self.cleaned_data.get("password")
        conferma_password = self.cleaned_data.get("conferma_password")
        if password != conferma_password:
           raise forms.ValidationError("Le password non combaciano!")
        return self.cleaned_data

     
class BeneficiarioModelForm(forms.ModelForm):
    id = forms.IntegerField(widget=forms.HiddenInput(),required=False)
    beneficiario = forms.CharField(widget=forms.TextInput(),required=True)
    descrizione = forms.CharField(widget=SummernoteWidget(),required=True)  # instead of forms.Textarea
    email = forms.CharField(widget=forms.EmailInput(),required=False)
    telefono = PhoneNumberField(widget=forms.TextInput(),required=False)
    sitoweb = forms.CharField(widget=forms.URLInput(),required=False)
    iduser = forms.IntegerField(widget=forms.HiddenInput(),required=False)
    
    class Meta:
        model = ModelBeneficiario
        fields = ["beneficiario", "descrizione", "email", "telefono","sitoweb","iduser"]
        widgets = {
            'descrizione': SummernoteWidget(),
        }
        

class ScadenzeModelForm(forms.ModelForm):
    id = forms.IntegerField(label='id',widget=forms.HiddenInput(),required=False)
    beneficiario = forms.ModelChoiceField(queryset = ModelBeneficiario.objects.all() , required=True,label='Beneficiario')
    datascadenza = forms.DateField(widget=forms.widgets.TextInput(attrs={'type': 'date','format':'d/m/Y'}),label='Data Scadenza')
    importo = forms.DecimalField(required=True,label='Importo')
    sollecito = forms.BooleanField(required=False,label='Sollecito')
    giorniritardo = forms.CharField(widget=forms.widgets.NumberInput(attrs={'readonly': 'readonly'}),required=False,label='Giorni Ritardo/Mancanti(-)')
    datapagamento = forms.DateField(widget=forms.widgets.TextInput(attrs={'type': 'date','format':'d/m/Y'}),label='Data Pagamento',required=False)
    iduser = forms.IntegerField(widget=forms.HiddenInput(),required=False)
    count = forms.IntegerField(widget=forms.HiddenInput(),required=False)
    idbeneficiario_id = forms.IntegerField(widget=forms.HiddenInput(),required=False)
    class Meta:
        model = ModelScadenze
        fields = ["id","beneficiario","datascadenza", "importo", "sollecito","giorniritardo", "datapagamento", "iduser","count","idbeneficiario_id"]
 