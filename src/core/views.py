from datetime import datetime
import random
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
import requests
from .utils import generer_facture_pdf, get_generations_users, GEN_PERC

from .models import Commande, CustomUser, Produit, Panier, Profil,Parrainage, Achat
from .forms import PaiementForm, RegisterForm
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

@login_required
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            prenom = form.cleaned_data.get('prenom')
            nom_de_famille = form.cleaned_data.get('nom_de_famille')
            suggestions = generate_username_suggestions(prenom, nom_de_famille)

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
    nb_filleuls = CustomUser.objects.filter(parrain=user).count()
    filleuls = user.filleuls.select_related('profil').all() if hasattr(user, 'filleuls') else []

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
    produits = Produit.objects.all()
    return render(request, "core/produits.html", {"produits": produits})

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
        adresse = request.POST.get("adresse")
        methode = request.POST.get("methode_paiement")
        panier = Panier.objects.filter(utilisateur=request.user)

        if not panier.exists():
            messages.error(request, "Votre panier est vide.")
            return redirect('panier')

        total = sum([item.produit.prix * item.quantite for item in panier])

        # Création d'une commande avec référence unique
        reference = str(uuid.uuid4()).replace("-", "")[:12].upper()
        commande = Commande.objects.create(
            utilisateur=request.user,
            total=total,
            adresse=adresse,
            methode_paiement=methode,
            reference=reference
        )

        # Préparation payload Flutterwave
        payload = {
            "tx_ref": reference,
            "amount": float(total),
            "currency": "CDF",
            "redirect_url": request.build_absolute_uri('/paiement_confirme/'),
            "payment_options": "card,ussd,banktransfer,mobilemoney",
            "customer": {
                "email": request.user.email,
                "name": request.user.username,
                "phone_number": request.user.telephone
            },
            "meta": {"commande_id": commande.id},
            "customizations": {
                "title": "Business Santé",
                "description": "Paiement de vos produits",
                "logo": request.build_absolute_uri("/static/images/logo.png")
            }
        }

        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            headers=headers,
            data=json.dumps(payload)
        )

        data = response.json()
        if data.get("status") == "success":
            # Redirection vers page de paiement Flutterwave
            return redirect(data['data']['link'])
        else:
            messages.error(request, "Impossible de lancer le paiement. Veuillez réessayer.")
            return redirect('panier')

@login_required
def paiement_confirme(request):
    tx_ref = request.GET.get('tx_ref')
    status = request.GET.get('status')

    if not tx_ref:
        messages.error(request, "Aucune transaction trouvée.")
        return redirect('panier')

    try:
        commande = Commande.objects.get(reference=tx_ref)
    except Commande.DoesNotExist:
        messages.error(request, "Commande introuvable.")
        return redirect('panier')

    # Vérifier avec l'API Flutterwave
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
    }
    response = requests.get(f"https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}", headers=headers)
    data = response.json()

    if data['status'] == 'success' and data['data']['status'] == 'successful':
        commande.statut = 'PAYE'
        commande.save()

        # Ici tu peux attribuer le gain 6% à l'utilisateur
        request.user.profil.solde += Decimal(str(commande.total)) * Decimal('0.06')
        request.user.profil.save()

        # Vider le panier
        Panier.objects.filter(utilisateur=request.user).delete()

        messages.success(request, "Paiement confirmé !")
    else:
        messages.error(request, "Le paiement n'a pas été confirmé.")

    return redirect('produits')

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
def mes_filleuls_view(request):
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

@login_required
def mmes_gains_view(request):
    gains = Achat.objects.filter(utilisateur=request.user).order_by('date')

    gain_propre = gains.filter(utilisateur="0").aggregate(Sum('montant'))['montant__sum'] or 0
    gain_1 = gains.filter(utilisateur="1").aggregate(Sum('montant'))['montant__sum'] or 0
    gain_2 = gains.filter(utilisateur="2").aggregate(Sum('montant'))['montant__sum'] or 0
    gain_3 = gains.filter(utilisateur="3").aggregate(Sum('montant'))['montant__sum'] or 0

    total_gains = gain_propre + gain_1 + gain_2 + gain_3

    chart_labels = [g.date.strftime("%d/%m") for g in gains]
    chart_data = [float(g.montant) for g in gains]

    context = {
        "gain_propre": gain_propre,
        "gain_1": gain_1,
        "gain_2": gain_2,
        "gain_3": gain_3,
        "total_gains": total_gains,
        "historique": gains,
        "chart_labels": json.dumps(chart_labels),
        "chart_data": json.dumps(chart_data),
    }

    
    return render(request, "core/mes_gains.html", context)

@login_required
def mees_gains_view(request):
    user = request.user
    profil = user.profil

    gain_propre = profil.solde or Decimal('0.00')

    tous_profils = Profil.objects.exclude(utilisateur=user)

    gain_1 = Decimal('0.00')
    gain_2 = Decimal('0.00')
    gain_3 = Decimal('0.00')

    for f in tous_profils:
        generation = f.get_generation()
        solde_filleul = f.solde or Decimal('0.00')

        if generation == 1:
            gain_1 += solde_filleul * Decimal('0.10')
        elif generation == 2:
            gain_2 += solde_filleul * Decimal('0.06')
        elif generation == 3:
            gain_3 += solde_filleul * Decimal('0.03')

    total_gains = gain_propre + gain_1 + gain_2 + gain_3

    context = {
        'gain_propre': gain_propre,
        'gain_1': gain_1,
        'gain_2': gain_2,
        'gain_3': gain_3,
        'total_gains': total_gains,
    }

    return render(request, 'core/mes_gains.html', context)

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

    # Gains propres
    gain_propre = profil.solde or Decimal('0.00')

    # Gains par génération
    tous_profils = Profil.objects.exclude(utilisateur=user)
    gain_1 = Decimal('0.00')
    gain_2 = Decimal('0.00')
    gain_3 = Decimal('0.00')

    # Créer un "historique" fictif pour le tableau
    historique = []

    for f in tous_profils:
        generation = f.get_generation()
        solde_filleul = f.solde or Decimal('0.00')

        if generation == 1:
            montant = solde_filleul * Decimal('0.10')
            gain_1 += montant
        elif generation == 2:
            montant = solde_filleul * Decimal('0.06')
            gain_2 += montant
        elif generation == 3:
            montant = solde_filleul * Decimal('0.03')
            gain_3 += montant
        else:
            montant = Decimal('0.00')

        if montant > 0:
            historique.append({
                'date': timezone.now().strftime("%d/%m/%Y"),
                'type': f"Gains génération {generation} de {f.utilisateur.username}",
                'montant': montant,
            })

    # Ajouter le gain propre de l'utilisateur
    if gain_propre > 0:
        historique.append({
            'date': timezone.now().strftime("%d/%m/%Y"),
            'type': "Gains personnels (6%)",
            'montant': gain_propre,
        })

    total_gains = gain_propre + gain_1 + gain_2 + gain_3

    context = {
        'gain_propre': gain_propre,
        'gain_1': gain_1,
        'gain_2': gain_2,
        'gain_3': gain_3,
        'total_gains': total_gains,
        'historique': historique,  # ⚠️ ici on fournit les données
    }

    return render(request, 'core/mes_gains.html', context)

