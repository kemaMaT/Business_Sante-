from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
  
     # Authentification
    #path('', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),

    # Pages principales
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('', views.start, name='start'),
    path('modifier_profile/', views.modifier_profile, name='modifier_profile'),


    # Produits & panier
    path('produits/', views.produits_list, name='produits'),
    path('panier/', views.panier_view, name='panier'),
    path('ajouter-au-panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('supprimer-du-panier/<int:produit_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),

    # Retraits et paiements
    path('solde/', views.solde, name='solde'),
    path('payment/', views.payment, name='payment'),
    path('initier_paiement/', views.initier_paiement, name='initier_paiement'),

    path("retrait/", views.retirer_gains, name="retrait"),
    path('retrait/', views.demander_retrait, name='demander_retrait'),
    path("payer_panier/", views.payer_panier, name="payer_panier"),

    # Parrainage
    path('filleuls/', views.mes_filleuls_view, name='filleuls'),
    path('gains/', views.mes_gains_view, name='gains'),

    # Informations
    path('cgu/', views.cgu, name='cgu'),
    path('cgv/', views.cgv, name='cgv'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   

