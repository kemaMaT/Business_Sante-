from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login

from .models import Produit, Panier, Profil,Parrainage
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.core.mail import send_mail


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            phone_number = form.cleaned_data.get('phone_number')
            profil, created = Profil.objects.get_or_create(utilisateur=user, defaults={'telephone': phone_number})

            # Envoi email de confirmation
            
            return redirect('payment')  # redirection vers la page de paiement
           
    else:
        form = RegisterForm()
    return render(request, "core/register.html", {"form": form})

@login_required
def home(request):
    utilisateur = request.user

    # Exemple de calculs
    total_gains = utilisateur.solde
    filleuls = Parrainage.objects.filter(parrain=utilisateur)
    nb_filleuls = filleuls.count()

    achats = Panier.objects.filter(utilisateur=utilisateur)

    context = {
        'solde': total_gains,
        'nb_filleuls': nb_filleuls,
        'achats': achats,
    }

    return render(request, 'core/start.html', context)

@login_required
def demander_retrait(request):
    # logique fictive
    return render(request, 'core/retrait.html')

@login_required
def profile(request):
    return render(request, 'core/profile.html')

def start(request):
    return render(request, 'core/home.html')

def produits_list(request):
    produits = Produit.objects.all()
    return render(request, "core/produits.html", {"produits": produits})

@login_required
def panier_view(request):
    panier = Panier.objects.filter(utilisateur=request.user)
    total = sum(item.total_price() for item in panier)
    return render(request, "core/panier.html", {"panier": panier, "total": total})

@login_required
def ajouter_au_panier(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    panier_item, created = Panier.objects.get_or_create(utilisateur=request.user, produit=produit)

    utilisateur = request.user

    # Ajouter au panier
    Panier.objects.create(utilisateur=utilisateur, produit=produit)

    # Ajouter le gain à l’utilisateur
    utilisateur.solde += produit.gain
    utilisateur.save()

    # Vérifier s’il a un parrain
    try:
        parrainage = Parrainage.objects.get(filleul=utilisateur)
        parrain = parrainage.parrain

        # Calcul du pourcentage du parrain (ex. 10%)
        pourcentage_parrain = Decimal('0.10')
        gain_parrain = produit.gain * pourcentage_parrain

        parrain.solde += gain_parrain
        parrain.save()

    except Parrainage.DoesNotExist:
        pass  # Pas de parrain, rien à faire

    return redirect('home')
    
    #if not created:
        #panier_item.quantite += 1
        #panier_item.save()

    #return redirect('panier')

@login_required
def supprimer_du_panier(request, produit_id):
    panier_item = get_object_or_404(Panier, utilisateur=request.user, produit_id=produit_id)
    panier_item.delete()
    return redirect('panier')

def traiter_achat(request):
    panier = Panier.objects.filter(utilisateur=request.user)
    total = sum(item.total_price() for item in panier)

    profil = request.user.profil
    if profil.parrain:
        profil.parrain.profil.solde += total * 0.10  # 10% pour le parrain
        profil.parrain.profil.save()
    
    profil.solde += total * 0.06  # 6% pour le filleul
    profil.save()

    panier.delete()
    return redirect('panier')

@login_required
def retirer_gains(request):
    #profil = Profil.objects.get(utilisateur=request.user)
    profil, created = Profil.objects.get_or_create(utilisateur=request.user)


    if request.method == "POST":
        montant = float(request.POST.get("montant", 0))
        
        if montant <= 0:
            messages.error(request, "Le montant doit être positif.")
        elif montant > profil.solde:
            messages.error(request, "Fonds insuffisants pour ce retrait.")
        else:
            profil.solde -= montant
            profil.gains_retires += montant
            profil.save()
            messages.success(request, f"Vous avez retiré {montant} € avec succès.")

    return render(request, "core/retrait.html", {"profil": profil})

def cgu(request):
    return render(request, 'core/cgu.html')

def cgv(request):
    return render(request, 'core/cgv.html')

def payment(request):
    return render(request, 'core/payment_page.html')