from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    parrain = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    gains = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    solde = models.DecimalField(default=0.0, max_digits=10, decimal_places=2)

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
    
class Profil(models.Model):
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parrain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="filleuls")
    solde = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gains_retires = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Nouveau champ
    telephone = models.CharField(max_length=20, blank=True)
    parrain_code = models.CharField(max_length=20, blank=True)
    is_paid = models.BooleanField(default=False)  # pour vérifier le paiement
    
    def __str__(self):
        return self.utilisateur.username

User = settings.AUTH_USER_MODEL

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