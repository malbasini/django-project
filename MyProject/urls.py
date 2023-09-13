"""MyProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from scadenzario.views import download_file,index_scadenze_order_by_beneficiario,index_scadenze_order_by_data,index_scadenze_order_by_importo
from scadenzario.views import index,get_queryset,update_view,detail_view,delete_view,index_scadenze,get_queryset_scadenze
from scadenzario.views import registrazione,homepage,creaBeneficiarioView,creaScadenzaView,detail_view_scadenza
from scadenzario.views import update_view_scadenza,delete_view_scadenza,update_view_sql,delete_ricevuta,index_order_by,activate,register

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', homepage, name='homepage'),
    path('registrazione/', register, name='registrazione'),
    path('beneficiario/', creaBeneficiarioView, name='beneficiario'),
    path('beneficiari/', index, name='myindex'),
    path('listascadenze/', index_scadenze, name='index'),
    path('search_results/', get_queryset, name='search'),
    path('update/<int:pk>/', update_view, name='aggiorna'),
    path('edit/<int:pk>/', update_view_scadenza, name='update_scadenza'),
    path('detail/<int:pk>/', detail_view, name='detail_view'),
    path('detailscadenze/<int:pk>/', detail_view_scadenza, name='detailscadenza'),
    path('delete/<int:pk>/', delete_view, name='delete_view'),
    path('deletescadenza/<int:pk>/', delete_view_scadenza, name='delete_view_scadenza'),
    path('scadenze/', creaScadenzaView, name='scadenza_view'),
    path('upload/<int:pk>/', update_view_sql, name='upload_files'),
    path('delete/<int:pk>/ricevuta/<int:id>', delete_ricevuta, name='delete_ricevuta'),
    path('search_results_scadenza/', get_queryset_scadenze, name='search_scadenze'),
    path('download/<int:id>', download_file,name='downloadfile'),
    path('orderby/<int:id>',index_order_by,name='orderby_beneficiario'),
    path('orderby_scadenze/<int:id>',index_scadenze_order_by_beneficiario,name='orderby_scadenze_beneficiario'),
    path('orderby_scadenze_datascadenza/<int:id>',index_scadenze_order_by_data,name='orderby_scadenze_data'),
    path('orderby_scadenze_importoscadenza/<int:id>',index_scadenze_order_by_importo,name='orderby_scadenze_importo'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('summernote/', include('django_summernote.urls')),
    path('activate/<uidb64>/<token>', activate, name='activate')
]
