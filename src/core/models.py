from datetime import datetime
import random
import string
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone

class CustomUser(AbstractUser):
    parrain = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    gains = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    nom = models.CharField(max_length=255, null=True, blank=True)
    prenom = models.CharField(max_length=255, null=True, blank=True)


    def save(self, *args, **kwargs):
        # Générer automatiquement un username si non fourni
        if not self.username:
            base_username = (self.nom[:1] + self.prenom[:4]).lower() or "user"
            
            # Proposer 5 suggestions possibles
            suggestions = [
                f"{base_username}{random.randint(10,99)}",
                f"{base_username}{random.choice(string.ascii_lowercase)}{random.randint(100,999)}",
                f"{base_username}_{random.choice(string.ascii_lowercase)}",
                f"{base_username}{random.randint(1000,9999)}",
                f"{base_username}{random.choice(string.ascii_lowercase)}{random.choice(string.ascii_lowercase)}"
            ]

            # Choisir le premier username libre
            for name in suggestions:
                if not CustomUser.objects.filter(username=name).exists():
                    self.username = name
                    break
            else:
                # En dernier recours
                self.username = f"{base_username}{random.randint(10000,99999)}"

        super().save(*args, **kwargs)

class Produit(models.Model):
    nom = models.CharField(max_length=255)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    gain = models.DecimalField(max_digits=10, decimal_places=2)  # Gain qu’on reçoit à l’achat
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="produits/", blank=True, null=True)
    
    def __str__(self):
        return self.nom
    

class Panier(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.produit.prix * self.quantite

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} - {self.utilisateur.username}"
    
User = settings.AUTH_USER_MODEL

class Profil(models.Model):
    utilisateur = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="profil"
)
    parrain = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.SET_NULL,
                               null=True, blank=True,
                               related_name='filleuls')  # important: related_name='filleuls'
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gains_retires = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    telephone = models.CharField(max_length=20, blank=True)
    mon_code = models.CharField(max_length=30, default=0, blank=True)
    parrain_code = models.CharField(max_length=30, blank=True,null=True)
    is_paid = models.BooleanField(default=False)
    date_created = models.DateTimeField(default=timezone.now)

    #def __str__(self):
        #return self.utilisateur.username

    def generate_code(self):
        # première lettre du nom (last_name), année d'inscription, dernière lettre du prénom (first_name)
        nom = (self.utilisateur.last_name or '').strip()
        prenom = (self.utilisateur.first_name or '').strip()
        annee = timezone.now().year
        first_letter = nom[0].upper() if nom else random.choice(string.ascii_uppercase)
        last_letter = prenom[-1].upper() if prenom else random.choice(string.ascii_uppercase)
        code = f"{first_letter}{annee}{last_letter}"
        # garantir unicité
        base = code
        i = 0
        while Profil.objects.filter(mon_code=code).exists():
            i += 1
            code = f"{base}{i}"
        return code
    
    def get_generation(self):
        """Retourne la génération du filleul"""
        if not self.utilisateur.parrain:
            return 0
        elif not self.utilisateur.parrain.parrain:
            return 1
        elif not self.utilisateur.parrain.parrain.parrain:
            return 2
        elif not self.utilisateur.parrain.parrain.parrain.parrain:
            return 3
        else:
            return 4  # plus de 3 générations = 4 (en rouge)


    def __str__(self):
        return f"Profil de {self.utilisateur.username}"

    def save(self, *args, **kwargs):
        if not self.mon_code:
            self.mon_code = self.generate_code()
        super().save(*args, **kwargs)

class Parrainage(models.Model):
    parrain = models.ForeignKey(User, related_name='mes_filleuls', on_delete=models.CASCADE)
    filleul = models.OneToOneField(User, related_name='mon_parrain', on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parrain} → {self.filleul}"
    

class Achat(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur.username} - {self.montant} FCFA"
    
class Vente(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur.username} - {self.montant} FC"