from django.contrib import admin
from .models import CustomUser, Panier, Produit, Profil, Parrainage

admin.site.register(Produit)
admin.site.register(CustomUser)
admin.site.register(Panier)
admin.site.register(Profil)
admin.site.register(Parrainage)
