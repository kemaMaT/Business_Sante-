
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profil
from django.contrib.auth.password_validation import password_validators_help_text_html
from .models import Produit


class ProduitForm(forms.ModelForm):

    class Meta:
        model = Produit
        fields = [
            "nom",
            "description",
            "prix",
            "image",
        ]

        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du produit"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Description du produit"
            }),

            "prix": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Prix du produit"
            }),

            "image": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }


class RegisterForm(UserCreationForm):
    parrain_code = forms.CharField(required=False, label="Code de Parrainage (facultatif)")
    phone_number = forms.CharField(max_length=20, required=True)
    nom = forms.CharField(max_length=100, required=True)
    prenom = forms.CharField(max_length=100, required=True)

    class Meta:
        model = CustomUser
        fields = ["nom", "prenom", "email", "phone_number", "password1", "password2", "parrain_code"]

    password1 = forms.CharField(
    label="Mot de passe",
    widget=forms.PasswordInput,
    help_text="""
    <strong>Votre mot de passe doit :</strong>
    <ul style="margin-top:5px; padding-left:18px;">
        <li>contenir au moins 8 caractères</li>
        <li>ne pas être trop similaire à vos informations personnelles</li>
        <li>ne pas être un mot de passe courant</li>
        <li>ne pas être entièrement numérique</li>
    </ul>

    <div class="password-strength mt-2">
        <div class="progress" style="height:8px;">
            <div id="password-strength-bar" class="progress-bar"></div>
        </div>
        <small id="password-strength-text"></small>
    </div>
    """
    )

    password2 = forms.CharField(
    label="Confirmer le mot de passe",
    widget=forms.PasswordInput,
    help_text="""
    Veuillez saisir le même mot de passe pour vérification.

    <small id="password-match-text"></small>
    """
    )

   
    def save(self, commit=True):
        user = super().save(commit=False)

        # 🔥 ENREGISTREMENT DES CHAMPS PERSONNALISÉS
        user.last_name = self.cleaned_data.get("nom")
        user.first_name = self.cleaned_data.get("prenom")
        user.telephone = self.cleaned_data.get("phone_number")

        # 🔥 Traitement du code parrain
        parrain_code = self.cleaned_data.get("parrain_code")
        if parrain_code:
            try:
                parrain = Profil.objects.get(mon_code=parrain_code)
                user.parrain = parrain.utilisateur
            except Profil.DoesNotExist:
                pass

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