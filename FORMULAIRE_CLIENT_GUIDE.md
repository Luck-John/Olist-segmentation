# Guide du Formulaire Client - Olist Segmentation

## 🎯 Objectif

Vous avez maintenant une interface utilisateur intuitive pour saisir les données brutes d'un client et obtenir une prédiction de segment automatiquement !

## 🚀 Accès aux Formulaires

Votre API dispose maintenant de 3 interfaces :

### 1. Interface Originelle (JSON/CSV)
- **URL** : `http://localhost:8002/ui`
- **Usage** : Pour les utilisateurs techniques qui préfèrent coller des données JSON/CSV

### 2. Formulaire Complet (Alpine.js)
- **URL** : `http://localhost:8002/form`
- **Usage** : Interface complète avec tous les champs et interactions avancées

### 3. **Formulaire Simple ⭐ (Recommandé)**
- **URL** : `http://localhost:8002/simple`
- **Usage** : Interface épurée, facile à utiliser, parfaite pour les démonstrations

## 📝 Comment utiliser le Formulaire Simple

### Étape 1 : Saisir les informations essentielles
Ces champs sont **obligatoires** (marqués d'un *) :

- **ID Client Unique** : Identifiant unique du client
- **ID Commande** : Identifiant de la commande
- **Statut Commande** : Livrée, Expédiée, En traitement, Annulée
- **Montant (R$)** : Valeur totale de la commande
- **Date Achat** : Date et heure de l'achat

### Étape 2 : Ajouter les informations optionnelles
Ces champs améliorent la précision de la prédiction :

- **Dates de livraison** : Estimée et réelle
- **Review** : Score (1-5) et date de création
- **Localisation** : Latitude et longitude du client

### Étape 3 : Obtenir la prédiction
Cliquez sur **"Calculer + Prédire"** et l'API va :

1. **Feature Engineering** : Calculer automatiquement :
   - Récence, Fréquence, Montant (RFM)
   - Délais de livraison
   - Scores de review
   - Distance géographique
   - Valeur vie client (CLV)

2. **Prédiction** : Appliquer le modèle de clustering pour déterminer :
   - Le cluster du client (0-5)
   - Le segment marketing
   - L'action recommandée
   - Le niveau de confiance

## 🎨 Résultats Affichés

### Prédiction Principale
- **Cluster** : Numéro du cluster identifié
- **Segment** : Nom du segment (ex: "Premium Actifs")
- **Action** : Action marketing recommandée
- **Confiance** : Pourcentage de confiance dans la prédiction

### Features Calculées
Toutes les features utilisées par le modèle sont affichées :
- Recency, Frequency, Monetary
- avg_delivery_days, late_delivery_rate
- avg_review_score, has_full_review
- CLV, dist_sao_paulo
- etc.

## 🔧 Fonctionnalités Techniques

### Validation Automatique
- Vérification des champs obligatoires
- Conversion automatique des types (nombres, dates)
- Gestion des erreurs avec messages clairs

### Interface Responsive
- Fonctionne sur desktop et mobile
- Design moderne avec Tailwind CSS
- Animations et transitions fluides

### Integration API
- Utilise l'endpoint `/predict-raw` existant
- Compatible avec tous les navigateurs modernes
- Gestion asynchrone des requêtes

## 🌐 Déploiement Railway

Pour déployer avec le nouveau formulaire :

1. **Push les modifications** :
   ```bash
   git add .
   git commit -m "Add customer form UI"
   git push origin main
   ```

2. **Déployer sur Railway** :
   - Le déploiement inclut automatiquement les nouveaux templates
   - L'URL Railway sera : `https://votre-domaine.railway.app/simple`

3. **Tester** :
   - `https://votre-domaine.railway.app/health`
   - `https://votre-domaine.railway.app/simple`

## 📊 Exemple d'Utilisation

### Données de Test
```
ID Client Unique: c123456
ID Commande: order_001
Statut: Livrée
Montant: 150.50
Date Achat: 2024-01-15T10:30:00
Date Livraison Estimée: 2024-01-20T10:30:00
Date Livraison Réelle: 2024-01-19T15:45:00
Score Review: 5
Date Review: 2024-01-20T09:00:00
Latitude: -23.550520
Longitude: -46.633308
```

### Résultat Attendu
- **Cluster** : 5
- **Segment** : "Premium Actifs"
- **Action** : "VIP"
- **Confiance** : ~85%

## 🎉 Avantages

1. **Facilité d'utilisation** : Plus besoin de connaître le format JSON
2. **Productivité** : Saisie rapide des données client
3. **Transparence** : Features calculées affichées
4. **Professionnel** : Interface moderne pour démonstrations
5. **Déployable** : Prêt pour la production sur Railway

Votre API est maintenant équipée d'une interface utilisateur complète et professionnelle ! 🚀
