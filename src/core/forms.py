from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class RegisterForm(UserCreationForm):
    parrain_code = forms.CharField(required=False, label="Code de Parrainage")

    class Meta:
        model = CustomUser
        fields = ["username", "email", "password1", "password2", "parrain_code"]

    def save(self, commit=True):
        user = super().save(commit=False)
        parrain_code = self.cleaned_data.get("parrain_code")
        if parrain_code:
            try:
                parrain = CustomUser.objects.get(username=parrain_code)
                user.parrain = parrain
            except CustomUser.DoesNotExist:
                pass  # Code invalide, pas de parrain
        if commit:
            user.save()
        return user
