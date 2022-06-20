import base64
from encodings import utf_8
from http.client import HTTPResponse
import io
from queue import Empty
from select import select
from this import s
from tkinter.tix import Form
from urllib import request
from xmlrpc.client import DateTime
from django.shortcuts import render
from multiprocessing import context
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from .forms import FormRegistrazioneUser,BeneficiarioModelForm, ScadenzeModelForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from .models import ModelBeneficiario, ModelScadenze
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import get_object_or_404
from datetime import datetime,date
from django import template
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import pathlib
import mimetypes
# import os module
import os
# Import HttpResponse module
from django.http.response import HttpResponse

# Create your views here.

@login_required(login_url='/accounts/login/')
def homepage(request):
    return render(request,'scadenzario/home.html')



def registrazione(request):
    if request.method == "POST":
        form = FormRegistrazioneUser(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            User.objects.create_user(username=username, password=password, email=email)
            user = authenticate(username=username, password=password)
            login(request, user)
            return HttpResponseRedirect("/")
    else:
        form = FormRegistrazioneUser()
    context = {"form": form}
    return render(request, "registration/registrazione.html", context)


@login_required(login_url='/accounts/login/')
def creaBeneficiarioView(request):
    if request.method == 'POST':
        form = BeneficiarioModelForm(request.POST)
        if form.is_valid():
            form.iduser = request.POST.get('iduser')
            form.save()
            return HttpResponseRedirect('/')
    else:
        form = BeneficiarioModelForm()
    context = {'form':form}
    return render(request,'beneficiario/create_beneficiario.html',context)


@login_required(login_url='/accounts/login/')
def creaScadenzaView(request):
    if request.method == 'POST':
        form = ScadenzeModelForm(request.POST)
        if form.is_valid():
            form.iduser = request.POST.get('iduser')
            #CALCOLO I GIORNI RITARDO
            if form.cleaned_data['datapagamento'] != '':
                form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'],form.cleaned_data['datapagamento'])
            else:
                form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'] , date.today())
            query = my_custom_sql(form.cleaned_data['beneficiario'])
            my_insert_sql(form,query[0])
            return HttpResponseRedirect('/')
    else:
        form = ScadenzeModelForm(initial={'giorniritardo': 0})
    form.fields['beneficiario'].queryset = ModelBeneficiario.objects.filter(iduser=request.user.pk)
    context = {'form':form}
    return render(request,'scadenze/create_scadenza.html',context)

#LISTA BENEFICIARI CON PAGINAZIONE
@login_required(login_url='/accounts/login/')
def index(request):
    object_list =  ModelBeneficiario.objects.filter(iduser=request.user.pk)
    page_num = request.GET.get('page', 1)
    paginator = Paginator(object_list, 6) # 6 employees per page
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        # if page is not an integer, deliver the first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # if the page is out of range, deliver the last page
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj})


#LISTA SCADENZE CON PAGINAZIONE
@login_required(login_url='/accounts/login/')
def index_scadenze(request):
    object_list =  ModelScadenze.objects.filter(iduser=request.user.pk)
    page_num = request.GET.get('page', 1)
    paginator = Paginator(object_list, 6) # 6 employees per page
    try:
         page_obj = paginator.page(page_num)
    except PageNotAnInteger:
         # if page is not an integer, deliver the first page
         page_obj = paginator.page(1)
    except EmptyPage:
         # if the page is out of range, deliver the last page
         page_obj = paginator.page(paginator.num_pages)
    return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj})

#RICERCA BENEFICIARIO
@login_required(login_url='/accounts/login/')
def get_queryset(request):
    query = request.GET.get("q")
    page_obj = ModelBeneficiario.objects.filter(Q(beneficiario__icontains=query))
    page_num = request.GET.get('page', 1)
    paginator = Paginator(page_obj, 6) # 6 employees per page
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        # if page is not an integer, deliver the first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # if the page is out of range, deliver the last page
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj ,'query':query})

#RICERCA SCADENZE
@login_required(login_url='/accounts/login/')
def get_queryset_scadenze(request):
    query = request.GET.get("q")
    if query != '':
        try:
            datetime_object = datetime.strptime(query, '%d/%m/%Y').date()
            if isinstance(datetime_object, date):
                page_obj = ModelScadenze.objects.filter(Q(datascadenza__icontains=datetime_object))
        except:
            page_obj = ModelScadenze.objects.filter(Q(beneficiario__icontains=query))
    else:
        page_obj = ModelScadenze.objects.filter(Q(beneficiario__icontains=query))
    page_num = request.GET.get('page', 1)
    paginator = Paginator(page_obj, 6) # 6 employees per page
    try:
         page_obj = paginator.page(page_num)
    except PageNotAnInteger:
          #if page is not an integer, deliver the first page
          page_obj = paginator.page(1)
    except EmptyPage:
          # if the page is out of range, deliver the last page
         page_obj = paginator.page(paginator.num_pages)
    return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj ,'query':query})

#DETTAGLIO BENEFICIARIO
@login_required(login_url='/accounts/login/')
def detail_view(request,pk):
    # dictionary for initial data with
    # field names as keys
    context ={}
    data = ModelBeneficiario.objects.get(id = pk)
    # add the dictionary during initialization
    context = {'data':data, 'pk':pk}
    return render(request, "beneficiario/detail_view.html", context)


#DETTAGLIO SCADENZA
@login_required(login_url='/accounts/login/')
def detail_view_scadenza(request,pk):
    # dictionary for initial data with
    # field names as keys
    context ={}
    data = my_select_dettaglio_scadenza_sql(pk)
    form = ScadenzeModelForm()
    initialize_form_for_update(form,pk)
    # add the dictionary during initialization
    context = {'data':data, "form":form ,'pk':pk}
    return render(request, "scadenze/detail_view_scadenze.html", context)


#UPDATE BENEFICIARIO
# update view for details
@login_required(login_url='/accounts/login/')
def update_view(request, pk):
    # dictionary for initial data with
    # field names as keys
    context ={}
    # fetch the object related to passed id
    obj = get_object_or_404(ModelBeneficiario, id = pk)
    # pass the object as instance in form
    form = BeneficiarioModelForm(request.POST or None, instance = obj)
    # save the data from the form and
    # redirect to detail_view
    if form.is_valid():
        form.save()
        return HttpResponseRedirect("/")
    # add form dictionary to context
    context = {'form':form,'id':pk}
    return render(request, "update_view.html", context)


#GET SCADENZA FOR UPDATE
@login_required(login_url='/accounts/login/')
def update_view_scadenza(request, pk):
    context ={}
    form = {}
    giorni=0
    if request.method == 'GET':
        form = ScadenzeModelForm()
        giorni=initialize_form_for_update(form,pk)
    data = my_select_ricevute_sql(pk)
    count = my_select_count_sql(pk)
    context = {'form':form,'pk':pk,"data":data,"count":count,"giorni":giorni}
    return render(request, "update_view_scadenza.html", context)



#INIZIALIZZO IL FORM PER L'UPDATE
def initialize_form_for_update(form,pk):
    data = my_select_dettaglio_scadenza_sql(pk)
    form.fields['beneficiario'].initial=data[8]
    form.fields['datascadenza'].initial = data[2]
    form.fields['id'].initial=data[0]
    form.fields['importo'].initial=data[3]
    form.fields['sollecito'].initial=data[4]
    form.fields['giorniritardo'].initial=data[5]
    form.fields['datapagamento'].initial=data[6]
    form.fields['iduser'].initial=data[7]
    form.fields['idbeneficiario_id'].initial=data[8]
    giorni = data[5]
    return giorni
    
    
    
    
#AGGIORNA LA SCADENZA CON UN CURSORE
def update_view_sql(request,pk):
    response=''
    giorni = 0
    if request.method == "GET":
        print('DENTRO GET')
        form = ScadenzeModelForm()
        giorni= initialize_form_for_update(form,pk)
        form.fields['beneficiario'].queryset = ModelBeneficiario.objects.filter(iduser=request.user.pk)
        data = my_select_ricevute_sql(pk)
        count = my_select_count_sql(pk)
        context = {'form':form,'pk':pk,"data":data,"count":count,"giorni":giorni}
        return render(request, "update_view_scadenza.html", context)
    if request.method == "POST": 
        form = ScadenzeModelForm(request.POST or None)
        files = request.FILES.getlist('files',None)
        if form.is_valid():
            print('FORM VALIDO')
            count = len(request.FILES.getlist('files'))
            print('COUNT:',count)
            beneficiario=form.cleaned_data['beneficiario']
            if count > 0:
                response = "FILE SUCCESSFULLY UPLOADED"
                for f in files:
                        handle_uploaded_file(f)
                        binary_file = open("templates/upload/"+ f.name, "rb").read()
                        #INSERISCO LE RICEVUTE
                        my_insert_sql_ricevuta(f.name,pathlib.Path("templates/upload/"+ f.name).suffix,binary_file, beneficiario,"templates/upload/"+ f.name,pk)
                        #CANCELLO IL FILE INSERITO
                        os.remove("templates/upload/"+ f.name)
                        response = "RICEVUTA/E INSERITE CON SUCCESSO"
                        data = my_select_ricevute_sql(pk)
                        count = my_select_count_sql(pk)
                        context = {'form':form,'pk':pk,"data":data,"count":count,"response":response,"giorni":giorni}
                return render(request, "update_view_scadenza.html", context)  
            else:
                context ={}
                if form.cleaned_data['datapagamento'] != '':
                    form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'],form.cleaned_data['datapagamento'])
                else:
                    form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'] , date.today())
                query = my_custom_sql(form.cleaned_data['beneficiario'])
                print('IDBENEFICIARIO',query[0])
                my_update_scadenza_sql(form,pk,query[0])
                return HttpResponseRedirect('/')  
        return HttpResponseRedirect('/')             

#DELETE RICEVUTA
def delete_ricevuta(request,pk,id):
    if request.method == "POST":
        my_delete_ricevuta_sql(pk)
        form = ScadenzeModelForm()
        giorni = initialize_form_for_update(form,id)
        data = my_select_ricevute_sql(id)
        count = my_select_count_sql(id)
        context = {'form':form,'pk':id,"data":data,"count":count,"giorni":giorni}
        return render(request, "update_view_scadenza.html", context)
    else:
        return HttpResponseRedirect('/')

#DOWNLOAD
def download_file(request,id):
    dati = my_select_blog_sql(id)
    blob = dati[0]
    file = dati[1]
    writeTofile(blob,file)
    # Define Django project base directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Define text file name
    filename = file
    # Define the full file path
    filepath = BASE_DIR + '/templates/upload/' + filename
    # Open the file for reading content
    path = open(filepath, 'rb')
    # Set the mime type
    mime_type, _ = mimetypes.guess_type(filepath)
    # Set the return value of the HttpResponse
    response = HttpResponse(path, content_type=mime_type)
    # Set the HTTP header for sending to browser
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    # Return the response value
    #CANCELLO IL FILE INSERITO
    os.remove("templates/upload/"+ filename)
    return response

def writeTofile(data, filename):
    # Convert binary data to proper format and write it on Hard Disk
    with open('templates/upload/'+filename, 'wb') as file:
        file.write(data)
    print("Stored blob data into: ", filename, "\n")
    
    
                   
#UPLOAD FILES
def handle_uploaded_file(f):
    print('dentro HANDLE')
    with open('templates/upload/'+ f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
            
            
#DELETE BENEFICIARIO
@login_required(login_url='/accounts/login/')
def delete_view(request, pk):
    # dictionary for initial data with
    # field names as keys
    context ={}
    # fetch the object related to passed id
    obj = get_object_or_404(ModelBeneficiario, id = pk)
    if request.method =="POST":
        # delete object
        my_delete_beneficiario_sql(pk)
        # after deleting redirect to
        # lista beneficiari
        return HttpResponseRedirect('/')
    return render(request, "update_view.html", context)

#CANCELLA UNA SCADENZA E LE SUE RICEVUTE A CASCATA
@login_required(login_url='/accounts/login/')
def delete_view_scadenza(request, pk):
    # dictionary for initial data with
    # field names as keys
    context ={}
    if request.method =="POST":
        # delete object
        my_delete_scadenza_sql(pk)
        return HttpResponseRedirect('/')
    return render(request, "update_view_scadenza.html", context)


#CALCOLA I GIORNI RITARDO O MANCANTI ALLA SCADENZA
def calcolo_giorni_ritardo(d1,d2):
     return (d2-d1).days



#REGION SQL COMMAND
from django.db import connection, connections
#RECUPERA L'IDENTIFICATIVO DEL BENEFICIARIO
def my_custom_sql(beneficiario):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM scadenzario.scadenzario_modelbeneficiario WHERE beneficiario = %s", [beneficiario])
        row = cursor.fetchone()
    close_connection()
    return row
#INSERISCE UNA SCADENZA
def my_insert_sql(form,idbeneficiario):
    with connection.cursor() as cursor:
        sql = "INSERT INTO scadenzario_modelscadenze (beneficiario,datascadenza,importo,sollecito,giorniritardo,datapagamento,iduser,idbeneficiario_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        val = (form.cleaned_data['beneficiario'],form.cleaned_data['datascadenza'],form.cleaned_data['importo'],form.cleaned_data['sollecito'],form.giorniritardo,form.cleaned_data['datapagamento'],form.iduser,idbeneficiario)
        cursor.execute(sql, val)
        print(cursor.rowcount, "record inserted.")
        close_connection()
            
#CANCELLA UN BENEFICIARIO IN BASE ALLA CHIAVE PRIMARIA     
def my_delete_beneficiario_sql(pk):
    with connection.cursor() as cursor:
        sql = "DELETE FROM scadenzario_modelbeneficiario WHERE id = %s"
        val = [pk]
        cursor.execute(sql, val)
        close_connection()
        
#RECUPERA LE SCADENZE PER UTENTE
def my_select_scadenze_sql(iduser):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, beneficiario, datascadenza, importo,CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE iduser = %s", [iduser])
        rows = cursor.fetchall()
        close_connection()
    return rows


#RECUPERA LE SCADENZE PER BENEFICIARIO
def my_select_search_sql_beneficiario(beneficiario):
    value=beneficiario
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, beneficiario, datascadenza, importo,CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE beneficiario like'%value%'")
        rows = cursor.fetchall()
        close_connection()
    return rows
#RECUPERA LE SCADENZE PER DATA SCADENZA
def my_select_search_sql_beneficiario(datascadenza):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, beneficiario, datascadenza, importo,CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE datascadenza like '% datascadenza % '", [datascadenza])
        rows = cursor.fetchall()
        close_connection()
    return rows

#DETTAGLIO SCADENZA
def my_select_dettaglio_scadenza_sql(id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, beneficiario, datascadenza, importo, CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE id = %s", [id])
        row = cursor.fetchone()
        close_connection()
    return row

#CANCELLA UNA SCADENZA
def my_delete_scadenza_sql(pk):
    with connection.cursor() as cursor:
        sql = "DELETE FROM scadenzario_modelscadenze WHERE id = %s"
        val = [pk]
        cursor.execute(sql, val)
        close_connection()
        
#UPDATE DI UNA SCADENZA
def my_update_scadenza_sql(form,pk,idbeneficiario):
    with connection.cursor() as cursor:
        sql = "UPDATE scadenzario_modelscadenze SET beneficiario = %s, datascadenza=%s, importo=%s, sollecito=%s, giorniritardo=%s, datapagamento=%s,idbeneficiario_id=%s WHERE id = %s"
        val = [form.cleaned_data['beneficiario'],form.cleaned_data['datascadenza'],form.cleaned_data['importo'],form.cleaned_data['sollecito'],form.giorniritardo,form.cleaned_data['datapagamento'],idbeneficiario,pk]
        cursor.execute(sql, val)
        close_connection()
    
#INSERISCE UNA RICEVUTA
def my_insert_sql_ricevuta(nome,tipofile,contenuto,beneficiario,path,idscadenza):
    with connection.cursor() as cursor:
        sql = "INSERT INTO scadenzario_modelricevute (nomeFile,typeFile,contentFile,beneficiario,path,scadenze) VALUES (%s,%s,%s,%s,%s,%s)"
        val = (nome,tipofile,contenuto,beneficiario,path,idscadenza)
        cursor.execute(sql, val)
        print(cursor.rowcount, "record inserted.")
        close_connection() 
        
 #CANCELLA UNA RICEVUTA
def my_delete_ricevuta_sql(id):
    with connection.cursor() as cursor:
        sql = "DELETE FROM scadenzario_modelricevute WHERE id = %s"
        val = [id]
        cursor.execute(sql, val)
        close_connection()  
        
#RECUPERA LE RICEVUTE PER IDSCADENZA
def my_select_ricevute_sql(idscadenza):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nomeFile,typeFile,beneficiario,scadenze FROM scadenzario_modelricevute WHERE scadenze = %s", [idscadenza])
        rows = cursor.fetchall()
        close_connection()
    return rows

#RECUPERA IL NUMERO DI RICEVUTE
def my_select_count_sql(idscadenza):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM scadenzario_modelricevute WHERE scadenze = %s", [idscadenza])
        row = cursor.fetchone()
        close_connection()
    return row


 #RECUPERA IL CAMPO BLOG
def my_select_blog_sql(id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT contentFile,nomeFile,typeFile FROM scadenzario.scadenzario_modelricevute WHERE ID = %s", [id])
        row = cursor.fetchone()
        close_connection()
    return row
   
#CHIUDE TUTTE LE CONNESSIONI AL DATABASE
def close_connection():
    for conn in connections.all():
            conn.close()
            