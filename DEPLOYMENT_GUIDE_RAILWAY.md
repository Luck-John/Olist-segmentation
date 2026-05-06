# Guide de Déploiement Railway - API Olist Segmentation

## État Actuel ✅

Votre API est prête pour le déploiement sur Railway. Voici ce qui a été optimisé :

### Fichiers Optimisés
- ✅ **Dockerfile** : Optimisé pour Railway avec meilleur cache et gestion d'erreurs
- ✅ **.dockerignore** : Exclut les fichiers lourds mais garde les modèles essentiels
- ✅ **railway.toml** : Configuration Railway pour health checks et variables d'environnement

### Tests Locaux Réussis
- ✅ API démarre correctement sur `http://localhost:8000`
- ✅ Health check `/health` fonctionne
- ✅ Endpoint `/model-info` retourne les informations du modèle
- ✅ Endpoint `/predict` fonctionne avec données de test

## Étapes de Déploiement

### 1. Push sur GitHub
```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### 2. Déploiement Railway
1. Connectez-vous à [Railway](https://railway.app)
2. Cliquez sur **New Project**
3. Choisissez **Deploy from GitHub Repo**
4. Sélectionnez votre repository
5. Railway détectera automatiquement le `Dockerfile`

### 3. Configuration
- Railway utilisera le port `$PORT` automatiquement
- Health check configuré sur `/health`
- Variables d'environnement définies dans `railway.toml`

### 4. Vérification
Une fois déployé, testez :
- `https://votre-domaine.railway.app/health`
- `https://votre-domaine.railway.app/docs` (Swagger UI)
- `https://votre-domaine.railway.app/model-info`

## Fichiers Essentiels Inclus

Les fichiers suivants sont garantis d'être inclus dans le déploiement :

### Modèles et Rapports
- `notebooks/models/final_pipeline.pkl` ✅
- `notebooks/reports/cluster_profiles_mean.csv` ✅
- `notebooks/reports/cluster_profiles_median.csv` ✅
- `notebooks/reports/clustering_comparison.csv` ✅
- `notebooks/reports/segmentation_finale_olist.csv` ✅

### Code Source
- `src/` - Code de feature engineering
- `scripts/api.py` - API FastAPI
- `config/` - Configuration
- `templates/` - Templates UI

## Dépannage

### Si l'API ne démarre pas :
1. Vérifiez les logs Railway pour les erreurs
2. Assurez-vous que tous les fichiers requis sont dans le repo
3. Vérifiez que les dépendances dans `requirements.txt` sont correctes

### Si le health check échoue :
1. L'API a besoin de 30 secondes pour démarrer (configuré dans healthcheck)
2. Vérifiez que le port `$PORT` est bien utilisé
3. Consultez les logs pour voir les erreurs de chargement de modèle

## Performance

L'API est optimisée pour :
- **Démarrage rapide** : Chargement des modèles au startup
- **Mémoire efficace** : Exclusion des fichiers lourds
- **Monitoring** : Health checks et logs détaillés

## Prochaines Étapes

1. **Déployer** sur Railway en suivant les étapes ci-dessus
2. **Tester** les endpoints avec l'URL Railway
3. **Monitorer** les performances via les logs Railway
4. **Mettre à jour** si nécessaire avec `git push`

Votre API est prête pour la production ! 🚀
