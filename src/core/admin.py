from django.contrib import admin
from .models import Commande, CustomUser, Panier, Produit, Profil, Parrainage

#admin.site.register(Produit)
admin.site.register(CustomUser)
admin.site.register(Panier)
admin.site.register(Profil)
admin.site.register(Parrainage)
admin.site.register(Commande)

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        if not obj.vendeur:
            obj.vendeur = request.user
        super().save_model(request, obj, form, change)
