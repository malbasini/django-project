from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from .forms import FormRegistrazioneUser,BeneficiarioModelForm, ScadenzeModelForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from .models import ModelBeneficiario, ModelScadenze
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import get_object_or_404
from datetime import datetime,date
import pathlib
import mimetypes
# import os module
import os
# Import HttpResponse module
from django.http.response import HttpResponse
from django.db import connection, connections
from typing import Protocol
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from .forms import UserRegistrationForm
from .decorators import user_not_authenticated
from .tokens import account_activation_token
from django.contrib import messages
# Create your views here.

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        confirmed = True
        return render(
            request=request,
            template_name="registration/confirmed.html",
            context={"confirmed": confirmed})
    else:
        confirmed = False
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            user.delete()
        except:
            user = None
        return render(
            request=request,
            template_name="registration/confirmed.html",
            context={"confirmed": confirmed})

def activateEmail(request, user, to_email):
    mail_subject = "Activate your user account."
    message = render_to_string("template_activate_account.html", {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "protocol": 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        message = f'Dear <b>{user}</b>, please go to you email <b>{to_email}</b> inbox and click on \
                received activation link to confirm and complete the registration. <b>Note:</b> Check your spam folder.'
    else:
        message = f'Problem sending email to {to_email}, check if you typed it correctly.'
        return render(
            request=request,
            template_name="registration/register.html",
            context={"message":message}
    )
@user_not_authenticated
def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active=False
            user.save()
            activateEmail(request, user, form.cleaned_data.get('email'))
            return render(
                request=request,
                template_name="registration/confirm.html",
                context={"form": form}
            )
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)

    else:
        form = UserRegistrationForm()

    return render(
        request=request,
        template_name="registration/register.html",
        context={"form": form}
        )
#HOME PAGE
@login_required(login_url='/accounts/login/')
def homepage(request):
    return render(request,'scadenzario/home.html')



def registrazione(request):
    if request.method == "POST":
        form = FormRegistrazioneUser(request.POST)
        if form.is_valid():
            try:
                username = form.cleaned_data["username"]
                email = form.cleaned_data["email"]
                password = form.cleaned_data["password"]
                User.objects.create_user(username=username, password=password, email=email)
                user = authenticate(username=username, password=password)
                login(request, user)
            except Exception as e:
                print("Errore in fase di registrazione: "+str(e))
            return HttpResponseRedirect("/")
    else:
        form = FormRegistrazioneUser()
    context = {"form": form}
    return render(request, "registration/registrazione.html", context)


@login_required(login_url='/accounts/login/')
def creaBeneficiarioView(request):
    context = {}
    form = {}
    try:
        if request.method == 'POST':
            form = BeneficiarioModelForm(request.POST)
            form.iduser = request.user.id
            if form.is_valid():
                beneficiario = form.cleaned_data['beneficiario']
                count = my_custom_sql_beneficiario(beneficiario)
                if count[0] > 0:
                    response = "HAI GIA' INSERITO QUESTO BENEFICIARIO!"
                    context = {'form':form,"response":response}
                    return render(request,'beneficiario/create_beneficiario.html',context)
                else: 
                    form.save()
                    return HttpResponseRedirect('/')
            else:
                print(form.errors.as_data()) # here you print errors to terminal
        else:
            form = BeneficiarioModelForm()
    except Exception as e:
        print('Errore nella creazione del beneficiario. ' + str(e))
    context = {'form':form}
    return render(request,'beneficiario/create_beneficiario.html',context)


@login_required(login_url='/accounts/login/')
def creaScadenzaView(request):
    try:
        if request.method == 'POST':
            form = ScadenzeModelForm(request.POST)
            if form.is_valid():
                form.iduser = request.POST.get('iduser')
                #CALCOLO I GIORNI RITARDO
                print('DATAPAGAMANENTO:',form.cleaned_data['datapagamento'])
                if form.cleaned_data['datapagamento'] != None:
                    form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'],form.cleaned_data['datapagamento'])
                else:
                    form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'] , date.today())
                query = my_custom_sql(form.cleaned_data['beneficiario'])
                my_insert_sql(form,query[0])
                return HttpResponseRedirect('/')
        else:
            form = ScadenzeModelForm(initial={'giorniritardo': 0})
    except Exception as e:
        print('Errore in fase di inserimento della scadenza: ' + str(e))
    form = ScadenzeModelForm(initial={'giorniritardo': 0})
    form.fields['beneficiario'].queryset = ModelBeneficiario.objects.filter(iduser=request.user.pk)
    context = {'form':form}
    return render(request,'scadenze/create_scadenza.html',context)

#LISTA BENEFICIARI CON PAGINAZIONE
@login_required(login_url='/accounts/login/')
def index(request):
    object_list =  ModelBeneficiario.objects.filter(iduser=request.user.pk)
    page_num = request.GET.get('page', 1)
    paginator = Paginator(object_list, 3) # 6 employees per page
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        # if page is not an integer, deliver the first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # if the page is out of range, deliver the last page
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj})



#ORDER BY BENEFICIARI CON PAGINAZIONE
@login_required(login_url='/accounts/login/')
def index_order_by(request,id):
    if id == 1:
        id = 0
        object_list = ModelBeneficiario.objects.all().order_by('-beneficiario').values().filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj,"id":id})
    else:
        object_list = ModelBeneficiario.objects.all().order_by('beneficiario').values().filter(iduser=request.user.pk)
        id = 1
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj,"id":id})

#LISTA SCADENZE CON PAGINAZIONE
@login_required(login_url='/accounts/login/')
def index_scadenze(request):
    object_list =  ModelScadenze.objects.filter(iduser=request.user.pk)
    page_num = request.GET.get('page', 1)
    paginator = Paginator(object_list, 3) # 6 employees per page
    try:
         page_obj = paginator.page(page_num)
    except PageNotAnInteger:
         # if page is not an integer, deliver the first page
         page_obj = paginator.page(1)
    except EmptyPage:
         # if the page is out of range, deliver the last page
         page_obj = paginator.page(paginator.num_pages)
    return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj})


#ORDER BY SCADENZE BENEFICIARIO CON PAGINAZIONE
def index_scadenze_order_by_beneficiario(request,id):
    if id == 1:
        id = 0
        object_list = ModelScadenze.objects.all().order_by('-beneficiario').values().filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})
    else:
        object_list = ModelScadenze.objects.all().order_by('beneficiario').values().filter(iduser=request.user.pk)
        id = 1
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})
    
    
#ORDER BY SCADENZE PER DATA SCADENZA CON PAGINAZIONE
def index_scadenze_order_by_data(request,id):
    if id == 1:
        id = 0
        object_list = ModelScadenze.objects.all().order_by('-datascadenza').values().filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})
    else:
        object_list = ModelScadenze.objects.all().order_by('datascadenza').values().filter(iduser=request.user.pk)
        id = 1
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})
    
    
#ORDER BY SCADENZE PER IMPORTO CON PAGINAZIONE
def index_scadenze_order_by_importo(request,id):
    if id == 1:
        id = 0
        object_list = ModelScadenze.objects.all().order_by('-importo').values().filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})
    else:
        object_list = ModelScadenze.objects.all().order_by('importo').values().filter(iduser=request.user.pk)
        id = 1
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj,"id":id})


#RICERCA BENEFICIARIO
@login_required(login_url='/accounts/login/')
def get_queryset(request):
    query = request.GET.get("q")
    if query != None:
        page_obj = ModelBeneficiario.objects.filter(Q(beneficiario__icontains=query))
        page_num = request.GET.get('page', 1)
        paginator = Paginator(page_obj, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj ,'query':query})
    else:
        object_list =  ModelBeneficiario.objects.filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'beneficiario/lista_beneficiario.html', {'page_obj': page_obj})

#RICERCA SCADENZE
@login_required(login_url='/accounts/login/')
def get_queryset_scadenze(request):
    query = request.GET.get("q")
    if query != None:
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
        paginator = Paginator(page_obj, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            #if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj ,'query':query})
    else:
        object_list =  ModelScadenze.objects.filter(iduser=request.user.pk)
        page_num = request.GET.get('page', 1)
        paginator = Paginator(object_list, 3) # 6 employees per page
        try:
            page_obj = paginator.page(page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if the page is out of range, deliver the last page
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'scadenze/lista_scadenze.html', {'page_obj': page_obj})

#DETTAGLIO BENEFICIARIO
@login_required(login_url='/accounts/login/')
def detail_view(request,pk):
    context ={}
    try:
        data = ModelBeneficiario.objects.get(id = pk)
    except Exception as e:
        print('Errore in detail_view in fase di creazione del modello. ' +str(e))
    context = {'data':data, 'pk':pk}
    return render(request, "beneficiario/detail_view.html", context)


#DETTAGLIO SCADENZA
@login_required(login_url='/accounts/login/')
def detail_view_scadenza(request,pk):
    context ={}
    try:
        data = my_select_dettaglio_scadenza_sql(pk)
        ricevute = my_select_ricevute_sql(pk)
        count = my_select_count_sql(pk)
        form = ScadenzeModelForm()
        initialize_form_for_update(form,pk)
    except Exception as e:
        print('errore in creazione del Model Form in detail_view_scadenza: ' + str(e))
    context = {'data':data, "form":form ,'pk':pk, 'ricevute':ricevute , 'count':count}
    return render(request, "scadenze/detail_view_scadenze.html", context)

#UPDATE BENEFICIARIO
@login_required(login_url='/accounts/login/')
def update_view(request, pk):
    try:
        form = {}
        context = {}
        data={}
        data = ModelBeneficiario.objects.get(id = pk)
        if request.method == 'POST':
            form = BeneficiarioModelForm(request.POST)
            form.iduser= request.POST.get('iduser')
            if form.is_valid():
                my_update_beneficiario_sql(form,form.iduser,pk)
                return HttpResponseRedirect('/')
            else:
                print(form.errors.as_data()) #
        else:
            form = BeneficiarioModelForm(request.GET or None, instance = data)
    except Exception as e:
        print('Errore nella creazione del beneficiario. ' + str(e))
    context = {'form':form,"id":pk}
    return render(request,'beneficiario/update_view.html',context)


#GET SCADENZA FOR UPDATE
@login_required(login_url='/accounts/login/')
def update_view_scadenza(request, pk):
    context ={}
    form = {}
    giorni=0
    count = 0
    data = {}
    try:
        if request.method == 'GET':
            form = ScadenzeModelForm()
            giorni=initialize_form_for_update(form,pk)
        data = my_select_ricevute_sql(pk)
        count = my_select_count_sql(pk)
    except Exception as e:
        print('Errore in update_view_scadenza: ' + str(e))
    context = {'form':form,'pk':pk,"data":data,"count":count,"giorni":giorni}
    return render(request, "update_view_scadenza.html", context)

#INIZIALIZZO IL FORM PER L'UPDATE
def initialize_form_for_update(form,pk):
    try:
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
    except Exception as e:
        print('Errore in initialize_form_for_update: ' + str(e))
        return 0
    return giorni
    
#AGGIORNA LA SCADENZA CON UN CURSORE
def update_view_sql(request,pk):
    response=''
    giorni = 0
    data={}
    context={}
    try:
        if request.method == "GET":
            form = ScadenzeModelForm()
            giorni= initialize_form_for_update(form,pk)
            form.fields['beneficiario'].queryset = ModelBeneficiario.objects.filter(iduser=request.user.pk)
            data = my_select_ricevute_sql(pk)
            count = my_select_count_sql(pk)
            context = {'form':form,'pk':pk,"data":data,"count":count,"giorni":giorni}
            return render(request, "update_view_scadenza.html", context)
    except Exception as e:
        print('Errore metodo GET in update_view_sql: '+str(e))
    try:
        if request.method == "POST": 
            form = ScadenzeModelForm(request.POST or None)
            files = request.FILES.getlist('files',None)
            if form.is_valid():
                count = len(request.FILES.getlist('files'))
                beneficiario=form.cleaned_data['beneficiario']
                if count > 0:
                    for f in files:
                            file = handle_uploaded_file(f)
                            binary_file = open(file.name, "rb").read()
                            #INSERISCO LE RICEVUTE
                            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            filepath = BASE_DIR + '/templates/upload/' + f.name
                            my_insert_sql_ricevuta(f.name,pathlib.Path("templates/upload/"+ f.name).suffix,binary_file, beneficiario,filepath,pk)
                            #CANCELLO IL FILE INSERITO
                            os.remove("templates/upload/"+ f.name)
                            response = "RICEVUTA/E INSERITE CON SUCCESSO"
                            data = my_select_ricevute_sql(pk)
                            count = my_select_count_sql(pk)
                            context = {'form':form,'pk':pk,"data":data,"count":count,"response":response,"giorni":giorni}
                    return render(request, "update_view_scadenza.html", context)  
                else:
                    context ={}
                    if form.cleaned_data['datapagamento'] != None:
                        form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'],form.cleaned_data['datapagamento'])
                    else:
                        form.giorniritardo=calcolo_giorni_ritardo(form.cleaned_data['datascadenza'] , date.today())
                    query = my_custom_sql(form.cleaned_data['beneficiario'])
                    my_update_scadenza_sql(form,pk,query[0])
                    return HttpResponseRedirect('/')  
            else:
                print(form.errors.as_data()) # here you print errors to terminal
                form = ScadenzeModelForm()
                giorni= initialize_form_for_update(form,pk)
                form.fields['beneficiario'].queryset = ModelBeneficiario.objects.filter(iduser=request.user.pk)
                data = my_select_ricevute_sql(pk)
                count = my_select_count_sql(pk)
                context = {'form':form,'pk':pk,"data":data,"count":count,"giorni":giorni}
                return render(request, "update_view_scadenza.html", context)
    except Exception as a:
        print('Errore metodo POST in update_view_sql:' + str(a))           

#DELETE RICEVUTA
def delete_ricevuta(request,pk,id):
    if request.method == "POST":
        try:
            my_delete_ricevuta_sql(pk)
            form = ScadenzeModelForm()
            giorni = initialize_form_for_update(form,id)
            data = my_select_ricevute_sql(id)
            count = my_select_count_sql(id)
        except Exception as e:
            print('Errore in delete_ricevuta: ' +str(e))
        context = {'form':form,'pk':id,"data":data,"count":count,"giorni":giorni}
        return render(request, "update_view_scadenza.html", context)
    else:
        return HttpResponseRedirect('/')

#DOWNLOAD
def download_file(request,id):
    try:
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
        #CANCELLO IL FILE INSERITO
        os.remove("templates/upload/"+ filename)
        # Return the response value
        return response
    except Exception as e:
        print('Errore in download_file: ' + str(e))
        return e


#SCRIVO IL FILE
def writeTofile(data, filename):
    # Convert binary data to proper format and write it on Hard Disk
    with open('templates/upload/'+filename, 'wb') as file:
        try:
            file.write(data)
        except:
            print('Errore nella scrittura del file')
        finally:
            file.close()
    print("Stored blob data into: ", filename, "\n")
    
    
                   
#UPLOAD FILES
def handle_uploaded_file(f):
    with open('templates/upload/'+ f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return destination        
            
            
#DELETE BENEFICIARIO
@login_required(login_url='/accounts/login/')
def delete_view(request, pk):
    context ={}
    try:
        obj = get_object_or_404(ModelBeneficiario, id = pk)
        if request.method =="POST":
            my_delete_beneficiario_sql(pk)
            return HttpResponseRedirect('/')
    except Exception as e:
        print('Errore in delete_view: ' + str(e))
    return render(request, "update_view.html", context)

#CANCELLA UNA SCADENZA E LE SUE RICEVUTE A CASCATA
@login_required(login_url='/accounts/login/')
def delete_view_scadenza(request, pk):
    context ={}
    if request.method =="POST":
        try:
            my_delete_scadenza_sql(pk)
            return HttpResponseRedirect('/')
        except Exception as e:
            print('Errore in delete_view_scadenza' + str(e))
    return render(request, "update_view_scadenza.html", context)


#CALCOLA I GIORNI RITARDO O MANCANTI ALLA SCADENZA
def calcolo_giorni_ritardo(d1,d2):
     return (d2-d1).days

#RECUPERA L'IDENTIFICATIVO DEL BENEFICIARIO
def my_custom_sql(beneficiario):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM scadenzario.scadenzario_modelbeneficiario WHERE beneficiario = %s", [beneficiario])
            row = cursor.fetchone()
        close_connection()
        return row
    except Exception as e:
         print(str(e))
    
#INSERISCE UNA SCADENZA
def my_insert_sql(form,idbeneficiario):
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO scadenzario_modelscadenze (beneficiario,datascadenza,importo,sollecito,giorniritardo,datapagamento,iduser,idbeneficiario_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            val = (form.cleaned_data['beneficiario'],form.cleaned_data['datascadenza'],form.cleaned_data['importo'],form.cleaned_data['sollecito'],form.giorniritardo,form.cleaned_data['datapagamento'],form.iduser,idbeneficiario)
            cursor.execute(sql, val)
            print(cursor.rowcount, "record inserted.")
            close_connection()
    except Exception as e:
        print(str(e))
            
#CANCELLA UN BENEFICIARIO IN BASE ALLA CHIAVE PRIMARIA     
def my_delete_beneficiario_sql(pk):
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM scadenzario_modelbeneficiario WHERE id = %s"
            val = [pk]
            cursor.execute(sql, val)
            close_connection()
    except Exception as e:
        print(str(e))
        
#RECUPERA LE SCADENZE PER UTENTE
def my_select_scadenze_sql(iduser):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, beneficiario, datascadenza, importo,CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE iduser = %s", [iduser])
            rows = cursor.fetchall()
            close_connection()
        return rows
    except Exception as e:
        print(str(e))

#DETTAGLIO SCADENZA
def my_select_dettaglio_scadenza_sql(id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, beneficiario, datascadenza, importo, CASE WHEN sollecito =1 THEN 'TRUE' ELSE 'FALSE' END as sollecito, giorniritardo, datapagamento, iduser, idbeneficiario_id FROM scadenzario.scadenzario_modelscadenze WHERE id = %s", [id])
            row = cursor.fetchone()
            close_connection()
        return row
    except Exception as e:
        print(str(e))

#CANCELLA UNA SCADENZA
def my_delete_scadenza_sql(pk):
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM scadenzario_modelscadenze WHERE id = %s"
            val = [pk]
            cursor.execute(sql, val)
            close_connection()
    except Exception as e:
        print(str(e))
        
#UPDATE DI UNA SCADENZA
def my_update_scadenza_sql(form,pk,idbeneficiario):
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE scadenzario_modelscadenze SET beneficiario = %s, datascadenza=%s, importo=%s, sollecito=%s, giorniritardo=%s, datapagamento=%s,idbeneficiario_id=%s WHERE id = %s"
            val = [form.cleaned_data['beneficiario'],form.cleaned_data['datascadenza'],form.cleaned_data['importo'],form.cleaned_data['sollecito'],form.giorniritardo,form.cleaned_data['datapagamento'],idbeneficiario,pk]
            cursor.execute(sql, val)
            close_connection()
    except Exception as e:
        print(str(e))
        
        
#UPDATE DI UN BENEFICIARIO
def my_update_beneficiario_sql(form,iduser,pk):
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE scadenzario_modelbeneficiario SET descrizione = %s, email = %s, telefono = %s, sitoweb = %s, iduser=%s WHERE id = %s"
            val = [form.cleaned_data['descrizione'],form.cleaned_data['email'],form.cleaned_data['telefono'],form.cleaned_data['sitoweb'],iduser, pk]
            cursor.execute(sql, val)
            close_connection()
    except Exception as e:
        print(str(e))
 
#COUNT DEL BENEFICIARIO
def my_custom_sql_beneficiario(beneficiario):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM scadenzario.scadenzario_modelbeneficiario WHERE beneficiario = %s", [beneficiario])
            row = cursor.fetchone()
        close_connection()
        return row
    except Exception as e:
         print(str(e))
    
 
 
 
    
#INSERISCE UNA RICEVUTA
def my_insert_sql_ricevuta(nome,tipofile,contenuto,beneficiario,path,idscadenza):
    with connection.cursor() as cursor:
        try:
            sql = "INSERT INTO scadenzario_modelricevute (nomeFile,typeFile,contentFile,beneficiario,path,scadenze_id) VALUES (%s,%s,%s,%s,%s,%s)"
            val = (nome,tipofile,contenuto,beneficiario,path,idscadenza)
            cursor.execute(sql, val)
            print(cursor.rowcount, "record inserted.")
            close_connection() 
        except Exception as e:
            print('ERRORE INSERIMENTO RICEVUTA: ' + str(e))
            
 #CANCELLA UNA RICEVUTA
def my_delete_ricevuta_sql(id):
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM scadenzario_modelricevute WHERE id = %s"
            val = [id]
            cursor.execute(sql, val)
            close_connection()
    except Exception as e:
        print(str(e))  
        
#RECUPERA LE RICEVUTE PER IDSCADENZA
def my_select_ricevute_sql(idscadenza):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nomeFile,typeFile,beneficiario,scadenze_id FROM scadenzario_modelricevute WHERE scadenze_id = %s", [idscadenza])
            rows = cursor.fetchall()
            close_connection()
        return rows
    except Exception as e:
        print(str(e))

#RECUPERA IL NUMERO DI RICEVUTE
def my_select_count_sql(idscadenza):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM scadenzario_modelricevute WHERE scadenze_id = %s", [idscadenza])
            row = cursor.fetchone()
            close_connection()
        return row
    except Exception as e:
        print(str(e))


 #RECUPERA IL CAMPO BLOG
def my_select_blog_sql(id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT contentFile,nomeFile,typeFile FROM scadenzario.scadenzario_modelricevute WHERE id = %s", [id])
            row = cursor.fetchone()
            close_connection()
        return row
    except Exception as b:
        print(str(b))
   
#CHIUDE TUTTE LE CONNESSIONI AL DATABASE
def close_connection():
    for conn in connections.all():
            conn.close()
