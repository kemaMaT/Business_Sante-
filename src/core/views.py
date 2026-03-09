from datetime import datetime
import random
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
import requests
from .utils import generer_facture_pdf, get_generations_users, GEN_PERC

from .models import Commande, CustomUser, Produit, Panier, Profil,Parrainage, Achat
from .forms import PaiementForm, ProduitForm, RegisterForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.core.mail import send_mail
from django.db.models import Sum
import json

import base64
from django.core.files.base import ContentFile
from django.db import transaction
import uuid
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_produits(request):

    produits = Produit.objects.all().order_by("-date_creation")

    return render(request, "admin_business/produits.html", {
        "produits": produits
    })

@staff_member_required
def accepter_produit(request, produit_id):

    produit = get_object_or_404(Produit, id=produit_id)

    produit.statut = "valide"
    produit.save()

    return redirect("admin_produits")

@staff_member_required
def refuser_produit(request, produit_id):

    produit = get_object_or_404(Produit, id=produit_id)

    produit.statut = "refuse"
    produit.save()

    return redirect("admin_produits")

@login_required
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data.get('prenom')
            last_name = form.cleaned_data.get('nom')
            suggestions = generate_username_suggestions(first_name,last_name)

            # tu peux par exemple en choisir un automatiquement :
            username = random.choice(suggestions)

            user = form.save(commit=False)
            user.username = username
            code = form.cleaned_data.get('code_parrain')

            # Lier le parrain automatiquement
            if code:
                try:
                    parrain = CustomUser.objects.get(mon_code=code)
                    user.parrain = parrain
                except CustomUser.DoesNotExist:
                    pass  # code invalide → pas de parrain

            user.save()
            phone_number = form.cleaned_data.get('phone_number')
            
            profil, created = Profil.objects.get_or_create(utilisateur=user, defaults={'telephone': phone_number})
            login(request, user)
            #Profil.objects.create(utilisateur=user)

            return redirect('payment')
    else:
        form = RegisterForm()
    return render(request, "core/register.html", {"form": form})

@login_required
def home(request):
    utilisateur = request.user

    # Récupérer le profil associé à l'utilisateur
    profil = Profil.objects.get(utilisateur=utilisateur)

    total_gains = profil.solde
    filleuls = Parrainage.objects.filter(parrain=utilisateur)
    total_filleuls = CustomUser.objects.filter(parrain=utilisateur).count()
    achats = Panier.objects.filter(utilisateur=utilisateur)

    context = {
        'solde': total_gains,
        'total_filleuls': total_filleuls,
        'achats': achats,
        'profil': profil,

    }

    return render(request, 'core/start.html', context)

@login_required
def demander_retrait(request):
    # logique fictive
    return render(request, 'core/retrait.html')

@login_required
def profile(request):

    user = request.user
    profil, _ = Profil.objects.get_or_create(utilisateur=user)
    # autres données utiles
    nb_filleuls = user.filleul.count()
    filleuls = user.filleul.select_related('profil').all()
    
    context = {
        'user': user,
        'profil': profil,
        'nb_filleuls': nb_filleuls,
        'filleuls': filleuls,
        
    }
    return render(request, 'core/profile.html', context)

@login_required
def modifier_profile(request):
    profil = request.user.profil

    if request.method == "POST":
        profil.telephone = request.POST.get("telephone")
        request.user.email = request.POST.get("email")

        # Gestion image rognée
        cropped_image = request.POST.get("cropped_image")

        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]
            file = ContentFile(base64.b64decode(imgstr),
                               name='avatar.' + ext)
            profil.avatar = file

        request.user.save()
        profil.save()

        return redirect("profile")

    return render(request, "core/modifier_profile.html", {
        "profil": profil
    })

def start(request):
    return render(request, 'core/home.html')

def produits_list(request):
    #roduits = Produit.objects.all()
    produits = Produit.objects.filter(statut="valide").order_by("-date_creation")

 
    return render(request, "core/produits.html", {"produits": produits})

@login_required
def aajouter_produit(request):
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save(commit=False)

            # ✅ AJOUT IMPORTANT
            produit.vendeur = request.user

            # produit en attente de validation
            produit.statut = "en_attente"

            produit.save()
            return redirect("home")
    else:
        form = ProduitForm()

    return render(request, "core/ajouter_produit.html", {"form": form})

@login_required
def ajouter_produit(request):
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save(commit=False)

            produit.vendeur = request.user
            produit.statut = "en_attente"

            produit.save()

            return redirect("mes_requetes")

    else:
        form = ProduitForm()

    return render(request, "core/ajouter_produit.html", {"form": form})

@login_required
def mes_requetes(request):

    produits = Produit.objects.filter(vendeur=request.user).order_by("-date_creation")

    return render(request, "core/mes_requetes.html", {
        "produits": produits
    })

@login_required
def panier_view(request):
    panier = Panier.objects.filter(utilisateur=request.user)
    #total = sum(item.total_price() for item in panier)
    total = Decimal('0.00')

    for item in panier:
        item.total = item.produit.prix * item.quantite
        total += item.total

    context = {
        'panier': panier,
        'total': total
    }
    return render(request, "core/panier.html", {"panier": panier, "total": total})

@login_required
def ajouter_au_panier(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    
    # Récupération de la quantité depuis le formulaire POST, sinon 1
    quantite = int(request.POST.get('quantite', 1))
    if quantite < 1:
        quantite = 1
    elif quantite > 1000:
        quantite = 1000

    # Créer ou mettre à jour le panier
    panier_item, created = Panier.objects.get_or_create(
        utilisateur=request.user,
        produit=produit,
        est_paye=False,
        defaults={'quantite': quantite}
    )
    if not created:
        panier_item.quantite += quantite
        panier_item.save()

    messages.success(request, f"{produit.nom} ajouté au panier ({quantite}) !")
    return redirect('produits')  # reste sur la page produits

@login_required
def paayer_panier(request):
    panier = Panier.objects.filter(utilisateur=request.user)

    if not panier.exists():
        messages.warning(request, "Votre panier est vide.")
        return redirect('panier')

    #total = sum(item.quantite for item in panier)
    total = Decimal('0.00')
    for item in panier:
        item.total = item.produit.prix * item.quantite
        total += item.total

    if request.method == "POST":
        form = PaiementForm(request.POST)
        if form.is_valid():

            # Ici on simule confirmation paiement
            # IMPORTANT : c’est ici qu’on attribuera les gains

            utilisateur = request.user

            # Bonus 6%
            bonus = total * Decimal('0.06')
            utilisateur.gains += bonus
            utilisateur.save()

            # Vider panier
            panier.delete()

            messages.success(request, "Paiement confirmé avec succès !")
            return redirect('panier')

    else:
        form = PaiementForm()
    
    context = {
        'panier': panier,
        'total': total
    }

    return render(request, 'core/payer_panier.html', context)

@login_required
def payer_panier(request):

    panier = Panier.objects.filter(utilisateur=request.user)

    if not panier.exists():
        return redirect('panier')

    #total = sum(item.total for item in panier)
    total = Decimal('0.00')

    for item in panier:
        item.total = item.produit.prix * item.quantite
        total += item.total

    if request.method == "POST":

        adresse = request.POST.get('adresse')
        methode = request.POST.get('methode_paiement')
        certifie = request.POST.get('certifie')

        if not certifie:
            messages.error(request, "Vous devez certifier vos informations.")
            return redirect('payer_panier')

        # Création commande
        commande = Commande.objects.create(
            utilisateur=request.user,
            total=total,
            adresse=adresse,
            methode_paiement=methode,
            statut='EN_ATTENTE'
        )

        # Redirection selon méthode
        if methode == "momo_airtel":
            return redirect('paiement_airtel', commande.id)
        elif methode == "momo_orange":
            return redirect('paiement_orange', commande.id)
        elif methode == "momo_mpsa":
            return redirect('paiement_mpsa', commande.id)
        elif methode == "momo_mtn":
            return redirect('paiement_mtn', commande.id)
        else:
            return redirect('paiement_carte', commande.id)

    return render(request, 'core/payer_panier.html', {
        'total': total
    })

@login_required
def initier_paiement(request):
    if request.method == "POST":
        total = request.POST.get("total")
        commande_id = request.POST.get("commande_id")

        trans_id = str(uuid.uuid4()).replace("-", "")[:12]

        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": trans_id,
            "amount": total,
            "currency": "CDF",
            "description": "Paiement Business Santé",
            "notify_url": settings.CINETPAY_NOTIFY_URL,
            "return_url": settings.CINETPAY_RETURN_URL,
            "customer_name": request.user.username,
            "customer_email": request.user.email,
        }

        url = "https://api-checkout.cinetpay.com/v2/payment"

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get("code") == "201":
            # Redirection vers la page CinetPay
            paiement_url = data["data"]["payment_url"]
            return redirect(paiement_url)
        else:
            messages.error(request, "Impossible de créer le paiement.")
            return redirect("payer_panier")

    return redirect("payer_panier")

#@csrf_exempt
def cinetpay_notify(request):
    if request.method == "POST":
        data = json.loads(request.body)

        transaction_id = data.get("transaction_id")
        
        # Re-vérification
        verification_payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id
        }

        url = "https://api-checkout.cinetpay.com/v2/payment/check"
        r = requests.post(url, json=verification_payload)
        response = r.json()

        status = response["data"]["status"]

        if status == "ACCEPTED":
            # Marquer commande payée
            commande = Commande.objects.filter(reference=transaction_id).first()
            if commande:
                commande.statut = "PAYE"
                commande.save()

            return HttpResponse("OK", status=200)

        return HttpResponse("FAILED", status=400)

@login_required
def paiement_confirme(request):
    messages.success(request, "Votre paiement a été validé par CinetPay.")
    return redirect("produits")

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

@login_required
def solde(request):
    try:
        profil = Profil.objects.get(utilisateur=request.user)
        solde = profil.solde
    except Profil.DoesNotExist:
        solde = 0  # ou None selon ton modèle

    return render(request, 'core/solde.html', {'solde': solde})

@login_required
def mess_filleuls_view(request):
    user= request.user

    # Génération 1 : filleuls directs
    gen1_users = CustomUser.objects.filter(parrain=user)

    # Génération 2
    gen2_users = CustomUser.objects.filter(parrain__in=gen1_users)

    # Génération 3
    gen3_users = CustomUser.objects.filter(parrain__in=gen2_users)

    # Génération 4+
    gen4_users = CustomUser.objects.filter(parrain__in=gen3_users)

    all_users = list(gen1_users) + list(gen2_users) + list(gen3_users) + list(gen4_users)

    # 👉 Convertir Users → Profils
    filleuls = Profil.objects.filter(utilisateur__in=all_users)

    return render(request, 'core/mes_filleuls.html', {'filleuls': filleuls})

def generation_par_rapport_a(parent, enfant):
    """Retourne la génération (1,2,3...) OU 0 si ce n'est pas un descendant."""
    generation = 1
    courant = enfant.parrain

    while courant:
        if courant == parent:
            return generation
        courant = courant.parrain
        generation += 1

    return 0

@login_required
def mess_filleuls_view(request):
    user = request.user 

    tous_users = CustomUser.objects.exclude(id=user.id)

    filleuls = []

    for u in tous_users:
        gen = generation_par_rapport_a(user, u)
        if gen > 0:
            u.generation = gen   # on injecte dynamiquement l'info
            filleuls.append(u)

    # Trier par génération
    filleuls = sorted(filleuls, key=lambda x: x.generation)

    context = {
        "filleuls": filleuls,
    }

    return render(request, "core/mes_filleuls.html", context)

def generate_username_suggestions(first_name, last_name):
    year = datetime.now().year % 100  # ex: 25 pour 2025
    suggestions = [
        f"{first_name.lower()}{last_name[0].lower()}",
        f"{first_name.lower()}.{last_name.lower()}",
        f"{last_name.lower()}.{first_name[0].lower()}",
        f"{first_name.lower()}_{year}",
        f"{first_name.lower()}{last_name.lower()[:2]}{random.randint(10,99)}",
    ]
    return suggestions

from decimal import Decimal
from django.utils import timezone

@login_required
def mes_gains_view(request):
    user = request.user
    profil = user.profil

    # Gains propres (ex: cashback personnel)
    gain_propre = profil.solde or Decimal('0.00')

    # Gains par génération
    gain_1 = Decimal('0.00')
    gain_2 = Decimal('0.00')
    gain_3 = Decimal('0.00')

    historique = []

    # Tous les autres utilisateurs
    tous_users = CustomUser.objects.exclude(id=user.id)

    for u in tous_users:
        generation = generation_par_rapport_a(user, u)

        # On récupère le solde du profil de ce filleul
        solde_filleul = u.profil.solde or Decimal('0.00')

        # Calcul du bonus selon la génération
        montant = Decimal('0.00')
        if generation == 1:
            montant = solde_filleul * Decimal('0.10')
            gain_1 += montant
        elif generation == 2:
            montant = solde_filleul * Decimal('0.06')
            gain_2 += montant
        elif generation == 3:
            montant = solde_filleul * Decimal('0.03')
            gain_3 += montant

        # Enregistrer dans l'historique
        if montant > 0:
            historique.append({
                "date": timezone.now().strftime("%d/%m/%Y"),
                "type": f"Gains génération {generation} de {u.username}",
                "montant": montant,
            })

    # Ajouter gains personnels à l'historique
    if gain_propre > 0:
        historique.append({
            "date": timezone.now().strftime("%d/%m/%Y"),
            "type": "Gains personnels (6%)",
            "montant": gain_propre,
        })

    total_gains = gain_propre + gain_1 + gain_2 + gain_3

    context = {
        "gain_propre": gain_propre,
        "gain_1": gain_1,
        "gain_2": gain_2,
        "gain_3": gain_3,
        "total_gains": total_gains,
        "historique": historique,
    }

    return render(request, "core/mes_gains.html", context)
    
@login_required
def mes_filleuls_view(request):
    user = request.user

    # tous les utilisateurs sauf moi
    tous_users = CustomUser.objects.exclude(id=user.id)

    filleuls = []

    for u in tous_users:

        generation = generation_par_rapport_a(user, u)

        if generation:  # seulement ceux de mon réseau

            solde = u.profil.solde or Decimal('0.00')

            gain = Decimal('0.00')

            if generation == 1:
                gain = solde * Decimal('0.10')

            elif generation == 2:
                gain = solde * Decimal('0.06')

            elif generation == 3:
                gain = solde * Decimal('0.03')

            # on attache les données
            u.generation = generation
            u.gain_apporte = gain

            filleuls.append(u)

    context = {
        "filleuls": filleuls
    }

    return render(request, "core/mes_filleuls.html", context)