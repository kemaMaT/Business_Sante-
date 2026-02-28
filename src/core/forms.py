
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profil

class RegisterForm(UserCreationForm):
    parrain_code = forms.CharField(required=False, label="Code de Parrainage (facultatif)")
    phone_number = forms.CharField(max_length=20, required=True)
    nom_de_famille = forms.CharField(max_length=100, required=True)
    prenom = forms.CharField(max_length=100, required=True)

    class Meta:
        model = CustomUser
        fields = ["nom_de_famille", "prenom", "email",'phone_number', "password1", "password2","parrain_code"]

    def save(self, commit=True):
        user = super().save(commit=False)
        parrain_code = self.cleaned_data.get("parrain_code")
        if parrain_code:
            try:
                parrain = Profil.objects.get(mon_code=parrain_code)
                user.parrain = parrain.utilisateur
            except CustomUser.DoesNotExist:
                pass  # Code invalide, pas de parrain
        if commit:
            user.save()
        return user

class PaiementForm(forms.Form):
    nom_complet = forms.CharField(max_length=100)
    telephone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)
    adresse = forms.CharField(widget=forms.Textarea, required=False)

    METHODE_CHOIX = [
        ('momo_airtel', 'Airtel Money'),
        ('momo_orange', 'Orange Money'),
        ('momo_vodacom', 'M-PSA'),
        ('momo_mtn', 'MTN Mobile Money'),
        ('carte', 'Carte bancaire'),
    ]

    methode_paiement = forms.ChoiceField(choices=METHODE_CHOIX)