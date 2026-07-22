"""
Database configuration for Backstage scanner
"""

# Configuration pour la base MariaDB
BACKSTAGE_DB = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'your_password',  # À mettre à jour
    'db': 'backstage_scans',
}

# Clé optionnelle pour Lighthouse API
LIGHTHOUSE_API_KEY = None  # À ajouter si disponible
