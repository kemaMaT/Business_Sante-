from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('produits/', views.produits_list, name='produits'),
    path('panier/', views.panier_view, name='panier'),
    path('ajouter-au-panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('supprimer-du-panier/<int:produit_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),
    path("retrait/", views.retirer_gains, name="retrait"),
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('retrait/', views.demander_retrait, name='demander_retrait'),
    path('start/', views.start, name='start'),

    path('cgu/', views.cgu, name='cgu'),
    path('cgv/', views.cgv, name='cgv'),
    path('payment/', views.payment, name='payment'),
    path('solde/', views.solde, name='solde'),
    path('filleuls/', views.mes_filleuls_view, name='filleuls'),
    path('gains/', views.mes_gains_view, name='gains'),

   
   


    
]

