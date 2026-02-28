# core/utils.py
from .models import Profil, Achat  # adapte Achat model
from reportlab.pdfgen import canvas
from django.http import HttpResponse

def generer_facture_pdf(commande):

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{commande.id}.pdf"'

    p = canvas.Canvas(response)
    p.drawString(100, 800, f"FACTURE - Business Santé")
    p.drawString(100, 780, f"Commande ID: {commande.id}")
    p.drawString(100, 760, f"Client: {commande.utilisateur.username}")
    p.drawString(100, 740, f"Total: {commande.total} FC")
    p.drawString(100, 720, f"Statut: {commande.statut}")

    p.showPage()
    p.save()

    return response

GEN_PERC = {1: 0.10, 2: 0.06, 3: 0.03}

def get_generations_users(user, max_gen=3):
    """
    Retourne dict {1: [User,...], 2: [...], 3: [...]}
    """
    from collections import defaultdict
    gens = defaultdict(list)
    current_users = [user]
    for gen in range(1, max_gen + 1):
        next_users = []
        for u in current_users:
            # u is User instance
            for p in getattr(u, 'filleuls').all():
                next_users.append(p)
        # next_users are User objects (parrain's filleuls)
        gens[gen] = next_users
        current_users = next_users
    return gens
