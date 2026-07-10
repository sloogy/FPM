# Test manuel GUI smoke v0.2.77

Ce test est obligatoire avant une version publique, car les tests unitaires ne remplacent pas une vraie interaction Qt sous Windows/Linux.

## Préparation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows : .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

Pour un test propre, utiliser un dossier de données temporaire :

```bash
FPM_DATA_DIR=/tmp/fpm-smoke-data python main.py
```


## Contrôle automatique rapide

Avant le test manuel, exécuter aussi :

```bash
python tools/gui_smoke_test.py
```

Le code retour `77` signifie que PySide6/Qt n’est pas installé dans cet environnement ; le test manuel GUI sur un vrai système cible est alors obligatoire.

## Contrôles obligatoires

1. L’application démarre sans deuxième fenêtre principale et sans traceback.
2. L’application démarre en mode simple : Tableau de bord, Stylos, Encres, Rotation, Aide et Paramètres sont visibles.
3. Les quatre actions du tableau de bord sont visibles : Ajouter un stylo, Ajouter une encre, Remplir un stylo, Noter un nettoyage.
4. Activer l’espace expert via le bouton de la barre latérale : tous les groupes réapparaissent.
5. `Ctrl+1` à `Ctrl+9` et `Alt+1` à `Alt+5` ouvrent les modules attendus en mode expert.
6. Revenir au mode simple : les modules experts sont à nouveau masqués.
7. Créer une nouvelle base ou utiliser une base de test vide.
8. Ajouter un stylo : marque, modèle, système de remplissage et plume sont sauvegardés.
9. Ajouter une encre : marque, nom, couleur et niveau sont sauvegardés.
10. Remplir un stylo avec une encre.
11. Ouvrir la rotation et générer des suggestions.
12. Nettoyer le remplissage et éventuellement recharger directement.
13. Activer le mode expert, ouvrir les règles et activer/désactiver au moins une règle.
14. Passer en anglais, redémarrer, vérifier les textes rotation/règles.
15. Passer en français, redémarrer, vérifier les textes rotation/règles.
16. Créer un élément wishlist et le transférer en dépense.
17. Ouvrir les dépenses, vérifier l’entrée, tester l’export CSV.
18. Ouvrir les paramètres, modifier l’échelle UI, redémarrer.
19. Créer une sauvegarde et la restaurer dans un dossier de données temporaire propre.
20. Ouvrir l’aide et démarrer/annuler la visite.
21. Fermer et relancer l’app : pas de perte de données, pas d’erreur de démarrage.

## Critère de validation

La version ne doit être publiée que si tous les contrôles fonctionnent sans crash, message incompréhensible ou perte de données.

Chemin de release GitHub en v0.2.77 : https://github.com/sloogy/FPM/releases. L'updater utilise latest.json via /releases/latest/download/latest.json.
