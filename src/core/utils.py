# core/utils.py
from .models import Profil, Achat  # adapte Achat model

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
