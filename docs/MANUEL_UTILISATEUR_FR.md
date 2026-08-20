# FountainPen Manager – Manuel utilisateur

**Version : v0.3.05 · Langue : français**

Ce manuel est le guide détaillé de FountainPen Manager. Le wiki intégré fournit des réponses courtes et consultables ; ce document décrit plus précisément les flux de travail, la logique de sécurité, les calculs, le stockage et le dépannage.

---

## Sommaire

1. [Philosophie générale](#1-philosophie-générale)
2. [Démarrage, répertoire de données et mode portable](#2-démarrage-répertoire-de-données-et-mode-portable)
3. [Premiers pas](#3-premiers-pas)
4. [Interface, modes et navigation](#4-interface-modes-et-navigation)
5. [Tableau de bord](#5-tableau-de-bord)
6. [Gestion des stylos](#6-gestion-des-stylos)
7. [Gestion des encres](#7-gestion-des-encres)
8. [Plumes et papier](#8-plumes-et-papier)
9. [Rotation et suggestions](#9-rotation-et-suggestions)
10. [Moteur de règles](#10-moteur-de-règles)
11. [Mode Full Auto](#11-mode-full-auto)
12. [Ink Safety Timer](#12-ink-safety-timer)
13. [Dépenses et valeur de la collection](#13-dépenses-et-valeur-de-la-collection)
14. [Wishlist](#14-wishlist)
15. [Statistiques et échantillons d’écriture](#15-statistiques-et-échantillons-décriture)
16. [Laboratoire passionné](#16-laboratoire-passionné)
17. [Recherche et données de référence](#17-recherche-et-données-de-référence)
18. [Réglages](#18-réglages)
19. [Langues](#19-langues)
20. [Mises à jour](#20-mises-à-jour)
21. [Sauvegarde et migration](#21-sauvegarde-et-migration)
22. [Dépannage et FAQ](#22-dépannage-et-faq)
23. [Référence](#23-référence)
24. [Glossaire](#24-glossaire)

---

## 1. Philosophie générale

FountainPen Manager n’est pas une simple base d’inventaire. L’application réunit usage quotidien, entretien, rotation, dépenses et préservation de la collection.

Trois principes guident le fonctionnement :

1. **Le moteur recommande, l’utilisateur décide.** Les scores et avertissements ne retirent jamais le contrôle manuel.
2. **La sécurité est prioritaire.** Les combinaisons susceptibles d’endommager un stylo sont clairement signalées et exclues des choix automatiques, sauf override volontaire.
3. **La profondeur reste facultative.** La collection fonctionne sans renseigner tous les champs experts. Le suivi de consommation, les règles détaillées et les analyses peuvent être activés selon les besoins.

---

## 2. Démarrage, répertoire de données et mode portable

### 2.1 Emplacement des données

L’application conserve la base SQLite, les réglages, les médias, les caches locaux et les sauvegardes dans un même répertoire de données. L’emplacement est choisi dans cet ordre :

1. Variable d’environnement `FPM_DATA_DIR`, si définie.
2. Répertoire portable `data/` avec le lanceur fourni.
3. Répertoire utilisateur propre au système pour une installation normale.

Les fichiers du programme et les données sont séparés. Une mise à jour ne doit donc pas écraser la collection.

### 2.2 Mode portable

Sous Windows, utilise `start-windows.cmd`. Sous Linux, utilise `start-linux.sh`. Le lanceur crée le dossier `data/` et configure la gestion HiDPI de Qt. L’exécutable et le dossier `_internal/` doivent rester ensemble.

### 2.3 Utilisation hors ligne

Collection, rotation, règles, statistiques et entretien fonctionnent hors ligne. Seules la recherche en ligne, le téléchargement d’images et la vérification des mises à jour nécessitent Internet.

---

## 3. Premiers pas

Ordre conseillé :

1. Ajouter les encres avec famille de couleur, propriétés et taille du flacon.
2. Ajouter une plume séparée ou saisir ses détails pendant la création du stylo.
3. Ajouter les stylos avec système de remplissage et dimensions facultatives.
4. Remplir un stylo avec une encre.
5. Ouvrir Rotation et générer des suggestions.
6. Examiner les avertissements du tableau de bord et les entretiens dus.

Sur une base vide, le tableau de bord affiche un panneau d’accueil et la page Aide propose une visite guidée. Dans **Réglages → Réinitialiser**, la visite peut être lancée immédiatement, forcée au prochain démarrage ou l’**assistant de configuration** en quatre étapes peut être rouvert à tout moment. Les données existantes ne sont pas modifiées.

---

## 4. Interface, modes et navigation

### 4.1 Mode simple et mode expert

Le **mode simple** montre six zones principales : Tableau de bord, Stylos, Encres, Rotation, Aide et Réglages.

Le **mode expert** active les 14 modules :

| # | Module | Rôle |
|---|---|---|
| 1 | Tableau de bord | Vue compacte et centre d’alertes |
| 2 | Stylos | Collection, valeurs, dimensions et médias |
| 3 | Encres | Flacons, propriétés et quantité restante |
| 4 | Plumes | Objets plume, grinds et compatibilité |
| 5 | Papier | Profils de papier et carnets |
| 6 | Rotation | Remplissages actuels et suggestions |
| 7 | Dépenses | Achats, livraison, douane et valeurs |
| 8 | Wishlist | Achats prévus et conversion en objets de collection |
| 9 | Règles | Moteur de règles, minuteries et Full Auto |
| 10 | Aide | Wiki intégré consultable et visite guidée |
| 11 | Réglages | Configuration de l’application |
| 12 | Statistiques | Analyse de la collection et de l’usage |
| 13 | Échantillons | Échantillons liés au stylo, à l’encre et au papier |
| 14 | Laboratoire passionné | Lacunes, entretien et analyses avancées |

Le mode ne change que la navigation visible. Il ne supprime ni ne désactive les données enregistrées.

### 4.2 Recherche et aide contextuelle

La recherche de la barre d’outils est transmise au module actif lorsque celui-ci possède un champ de recherche. `Ctrl+F` place le focus dans ce champ.

L’action **❔ Aide pour cet onglet** ouvre le module Aide et sélectionne directement le chapitre pertinent. Le wiki recherche dans toutes les cartes ; plusieurs mots sont pris en compte ensemble.

Le bouton **📖 Ouvrir le manuel** ouvre le document correspondant à la langue sélectionnée :

- allemand : `docs/BENUTZERHANDBUCH_DE.md`
- anglais : `docs/USER_MANUAL_EN.md`
- français : `docs/MANUEL_UTILISATEUR_FR.md`

### 4.3 Ordinateur portable et mode fenêtré

Qt travaille déjà en pixels logiques. FountainPen Manager évite donc de multiplier une seconde fois toutes les dimensions par le facteur DPI du système.

Au démarrage, la fenêtre principale reste dans la zone de travail disponible. Sur les écrans portables plus petits :

- les tuiles du tableau de bord passent sur moins de colonnes ;
- les pages longues disposent de leur propre défilement vertical ;
- la taille minimale est plafonnée par l’espace disponible ;
- les dialogues utilisent des zones défilantes au lieu de masquer les contrôles sous le bord de l’écran.

Le réglage **Réglages → Apparence → Auto** est recommandé pour la plupart des portables et les configurations multi-écrans.

### 4.4 Raccourcis essentiels

- `Ctrl+N` : ajouter un élément sur la page active, si disponible.
- `Ctrl+F` : focaliser la recherche.
- `Ctrl+1 … Ctrl+9` : navigation rapide.
- `Suppr` : supprimer la ligne sélectionnée uniquement lorsque le tableau a le focus.
- Les menus contextuels donnent accès aux actions fréquentes sans surcharger l’écran de boutons.

---

## 5. Tableau de bord

Le tableau de bord est un centre de focus compact, pas un inventaire complet.

### 5.1 Tuiles

- **Collection & état** : nombre de stylos et d’encres, valeur, archives et indications du conseiller.
- **Rotation & durée** : remplissages actifs, en retard ou bientôt dus.
- **Service & blocages** : stylos problématiques, cas de service et blocages.
- **Activité récente** : derniers remplissages et changements.
- **Objectifs d’épargne** : visible uniquement lorsque des objectifs BudgetManager sont disponibles.

### 5.2 Utilisation

- Un clic focalise la tuile et agrandit son tableau détaillé.
- Un seul tableau détaillé reste ouvert à la fois.
- Un nouveau clic sur la même tuile le replie.
- Le bouton visible **« Ouvrir l’onglet »** ouvre le module associé.
- Le double-clic sur une tuile ou une ligne reste disponible comme raccourci.
- `Entrée` ou `Espace` agrandit ; `Ctrl+Entrée` ouvre le module associé.

Le tableau du Safety Timer montre volontairement uniquement les remplissages en retard ou bientôt dus. « Bientôt dû » commence à **80 %** de la durée autorisée. La liste complète se trouve dans Rotation → Remplissages actuels.

---

## 6. Gestion des stylos

### 6.1 Dialogue du stylo et saisie sûre

Le dialogue est divisé en quatre pages :

1. Données de base
2. Plume
3. Détails / valeur
4. Notes

Les valeurs restent dans le dialogue lors du passage d’une page à l’autre. Seul **Enregistrer** écrit dans SQLite. **Annuler** ou fermer la fenêtre demande confirmation avant d’abandonner des données modifiées.

Les champs numériques acceptent le séparateur décimal régional et les unités visibles, par exemple :

- `143,5 mm`
- `24,8 g`
- `0,8 ml`
- `CHF 39.95`

Le parseur retire les unités et symboles monétaires de manière sûre. Changer de page ne remet plus une valeur correcte à zéro.

### 6.2 Champs principaux

Les champs habituels comprennent marque, modèle, couleur, système de remplissage, date et prix d’achat, valeur de marché, valeur d’assurance, dimensions, capacité d’encre, rôle, thème, tags et notes.

Les systèmes pris en charge comprennent piston, vacuum, convertisseur, cartouche et eyedropper.

### 6.3 Tags et statut

Les tags peuvent identifier un Grail, un stylo problématique, une pièce de collection, un vintage ou un autre rôle. Ils influencent les suggestions, les délais de sécurité et les analyses.

Un stylo peut être disponible, en service, bloqué ou archivé. Les stylos en service ou bloqués restent visibles dans l’historique, mais ne sont pas choisis pour une nouvelle rotation.

### 6.4 Appariement fixe et stylo obligatoire

- **Appariement fixe 💍** : affecte une encre précise à un stylo. Rotation, reroll et hasard le respectent.
- **Stylo obligatoire ⭐** : reçoit un slot avant les candidats ordinaires ; son encre reste sélectionnable.

### 6.5 Dimensions et comparaison

L’application stocke les longueurs fermé, sans capuchon et posté, le diamètre maximal, le diamètre de section, le poids et la capacité.

La comparaison visuelle peut superposer les stylos ou les afficher en lignes avec une échelle. Les stylos sans mesure appropriée sont ignorés plutôt qu’estimés.

### 6.6 Images et médias gérés

Les images sont copiées dans le stockage géré sous le répertoire de données. Elles restent valides même si le fichier original est déplacé ou renommé. Les fichiers sont limités en taille et les chemins sont contrôlés.

Sauvegarde le répertoire complet, et pas seulement la base SQLite, pour conserver images et échantillons.

---

## 7. Gestion des encres

### 7.1 Propriétés

Enregistre marque, nom, famille de couleur, taille du flacon, données d’achat, wetness, flow, saturation, shading, sheen, shimmer, pigment, résistance à l’eau, tendance au feathering et effort de nettoyage.

Ces propriétés alimentent le moteur de règles, le Safety Timer et le score de rotation.

### 7.2 Quantité restante

Le suivi de quantité est facultatif. Lorsqu’il est actif, le remplissage soustrait la capacité enregistrée du stylo. La quantité ne devient jamais négative. Les flacons vides ou archivés sont exclus des suggestions mais restent dans l’historique.

### 7.3 Même encre dans plusieurs stylos

Par défaut, une encre déjà active n’est pas proposée pour un second stylo. Cette règle peut être assouplie dans les réglages. Les appariements fixes restent une exception volontaire.

---

## 8. Plumes et papier

### 8.1 Plumes

Une plume peut stocker fabricant, taille physique, largeur d’écriture, matériau, grind, nibmeister, flexibilité, rigidité, feedback et compatibilité.

Une installation précise stylo–plume–feed peut posséder ses propres notes. La même plume peut ainsi être documentée différemment selon le stylo et le feed.

### 8.2 Historique

Les changements de plume peuvent être documentés par stylo, avec provenance, grind personnalisé et impression d’écriture.

### 8.3 Papier

Les profils de papier et carnets stockent grammage, surface, aptitude au sheen et shading, feathering et bleed-through. Un contexte papier sélectionné influence le score de rotation.

---

## 9. Rotation et suggestions

### 9.1 Flux de travail

Le moteur crée une combinaison stylo–encre pour les stylos vides et disponibles. Tu choisis le nombre de slots et peux ajouter un contexte papier ou thème.

Les stylos en service, bloqués, déjà remplis et les flacons vides sont exclus automatiquement.

### 9.2 Score

Le score combine :

- bonus et malus des règles ;
- rôle du stylo et adéquation de l’encre ;
- compatibilité plume / flow ;
- adéquation au papier ;
- diversité des couleurs ;
- durée depuis la dernière utilisation ;
- priorités de collection ;
- hasard facultatif.

Une explication du score montre pourquoi une combinaison est bien ou mal classée.

### 9.3 Attribution en deux passages

1. Stylos obligatoires et appariements fixes sont traités en premier.
2. Les slots restants vont aux meilleurs candidats admissibles.

### 9.4 Reroll

Les exécutions successives évitent les paires stylo–encre déjà montrées pendant la session. Quand le pool d’un stylo est épuisé, un nouveau tour commence pour lui. Les appariements fixes sont exemptés.

### 9.5 Hasard

Le hasard est réglable de 0 à 100 %. Les filtres de sécurité restent actifs à toute valeur. Les règles dures bloquantes et les refus Full Auto ne sont jamais tirés au hasard, sauf appariement fixe volontaire.

---

## 10. Moteur de règles

Les règles sont dures ou souples :

- **Règle souple** : modifie le score et fournit un conseil.
- **Règle dure** : protège le stylo et peut bloquer la sélection automatique.

Niveaux : Info, Avertissement, Critique, Bloqué.

Chaque règle peut être désactivée individuellement ou via son groupe. Les overrides manuels sont journalisés.

Exemple : vacuum filler + shimmer peut être bloqué car les particules peuvent se déposer dans un système plus difficile à nettoyer.

---

## 11. Mode Full Auto

Full Auto est facultatif et doit être activé explicitement. Il peut :

- refuser les combinaisons risquées ;
- préférer une alternative plus sûre ;
- ignorer les stylos bloqués ou indisponibles ;
- appliquer des seuils de score.

Il ne doit jamais décider silencieusement. Chaque action reste explicable par règle, raison, score, risque et alternative choisie.

---

## 12. Ink Safety Timer

La durée de base est réduite par les facteurs de risque. Valeurs d’usine typiques :

- encre normale : **28 jours** ;
- encre shimmer : **14 jours** ;
- pigment / waterproof : limite configurée plus courte ;
- stylo Grail : maximum **21 jours**.

La limite effective est la plus courte applicable. Exemple : shimmer dans un Grail utilise `min(28, 14, 21) = 14 jours`, sauf règle encore plus restrictive.

État du tableau de bord :

- sous 80 % : normal, non affiché dans la table d’alertes ;
- dès 80 % : bientôt dû ;
- au-dessus de 100 % : en retard.

Tous les remplissages restent visibles dans Rotation.

---

## 13. Dépenses et valeur de la collection

Une dépense peut inclure prix d’achat, livraison, douane, vendeur, date et moyen de paiement. Les stylos peuvent aussi stocker valeur de marché et valeur d’assurance.

L’application calcule totaux et évolution avec le format régional et la devise choisis. Les achats en devise étrangère peuvent utiliser les taux enregistrés.

---

## 14. Wishlist

Les souhaits peuvent concerner stylos, encres, plumes, papier, accessoires ou services. Enregistre statut, prix cible, notes et médias facultatifs.

Le flux d’achat transforme un souhait en objet de collection et en dépense, ce qui évite une seconde saisie.

---

## 15. Statistiques et échantillons d’écriture

Les statistiques couvrent répartition des marques, systèmes de remplissage, familles de couleurs, usage, dépenses et évolution de valeur.

Les échantillons peuvent relier stylo, encre et papier. Ils permettent des comparaisons côte à côte et documentent le comportement d’une combinaison dans le temps.

---

## 16. Laboratoire passionné

Le laboratoire propose des analyses facultatives :

- lacunes dans les familles de couleurs ;
- santé de la collection ;
- effort de nettoyage par encre ;
- quantité restante et signal de rachat ;
- historique des changements de plume ;
- observations de collection et d’entretien.

Ces fonctions ne bloquent pas la gestion quotidienne.

---

## 17. Recherche et données de référence

### 17.1 Dimensions

La recherche suit plusieurs étapes prudentes et affiche les propositions avant application. Seuls les champs vides sont remplis ; les valeurs manuelles ne sont jamais écrasées.

Les résultats confirmés sont mis en cache localement.

### 17.2 Sources

Chaque proposition indique sa source :

- `manufacturer:<domaine>` : source officielle ;
- `online:<domaine>` : web ouvert ;
- `cache` : résultat local déjà confirmé.

### 17.3 Domaines fabricants

Les fabricants connus possèdent des domaines intégrés. Ajoute ou remplace des marques avec `manufacturer_domains.json` dans le répertoire de données. Une valeur peut être un domaine ou une liste de domaines.

### 17.4 Images

La recherche d’images privilégie les résultats officiels du fabricant, puis une recherche plus large. Les images importées sont copiées dans le stockage média géré.

---

## 18. Réglages

| Page | Contenu |
|---|---|
| Général | Langue et comportement général |
| Rotation & suggestions | Hasard, même encre active et comportement de rotation |
| Apparence | Échelle responsive et mode simple / expert |
| Devise & région | Devise, nombres, dates et taux de change |
| Base & sauvegarde | Emplacement des données et sauvegardes |
| Import / export | Transfert de données et exports disponibles |
| Reset / zone dangereuse | Remises à zéro protégées |
| Mises à jour | Vérification manuelle |
| À propos | Version et build |

Le réglage Auto est recommandé pour que l’interface reste dans la surface d’écran disponible.

---

## 19. Langues

Les textes visibles sont stockés hors du code Python dans des fichiers JSON allemand, anglais et français. La parité des clés est contrôlée automatiquement.

Des termes techniques tels que Sheen, Shimmer ou Reroll peuvent rester invariants lorsqu’ils sont plus clairs pour les passionnés.

Depuis v0.2.97, le wiki intégré et le manuel complet existent dans les trois langues.

---

## 20. Mises à jour

L’application vérifie les mises à jour uniquement sur demande dans Réglages. Elle lit le manifeste officiel et ne lance pas de connexion cachée en arrière-plan.

En mode portable, remplace le dossier du programme tout en conservant les données. Fais une sauvegarde auparavant.

---

## 21. Sauvegarde et migration

Une sauvegarde complète comprend :

- base SQLite ;
- réglages ;
- images et échantillons ;
- cache de recherche ;
- overlay des domaines fabricants ;
- historique de sauvegarde souhaité.

La méthode la plus sûre consiste à fermer l’app puis copier tout le répertoire de données.

Pour changer d’ordinateur, copie ce répertoire et utilise `FPM_DATA_DIR` ou l’emplacement standard du système.

---

## 22. Dépannage et FAQ

**Je ne vois qu’une partie de la page sur mon portable.**
Utilise Réglages → Apparence → Auto, maximise temporairement la fenêtre et utilise le défilement propre à la page. Le tableau de bord n’ouvre volontairement qu’un seul tableau détaillé à la fois.

**Des dimensions ou prix disparaissent lorsque je change de page dans le dialogue du stylo.**
Ce défaut a été corrigé dans v0.2.95. Les unités `mm`, `g`, `ml` et les symboles monétaires sont correctement lus. v0.2.97 avertit aussi avant d’abandonner un dialogue modifié.

**Le tableau de bord ne montre pas tous les remplissages actifs.**
La table d’alertes montre uniquement les remplissages ayant atteint 80 % de leur limite. La liste complète se trouve dans Rotation → Remplissages actuels.

**La même encre est toujours proposée.**
Vérifie l’existence d’un appariement fixe. Sinon, relance les suggestions : le reroll évite les paires déjà montrées pendant la session.

**Un stylo n’apparaît jamais.**
Vérifie s’il est déjà rempli, en service, bloqué, exclu de la rotation ou archivé.

**Comment trouver l’aide de la page actuelle ?**
Utilise ❔ Aide pour cet onglet, puis affine avec la recherche du wiki ou `Ctrl+F`.

**La recherche en ligne ne trouve rien.**
Elle nécessite Internet. Vérifie l’orthographe de la marque et les domaines optionnels. Les fonctions locales continuent de fonctionner.

**Une alerte est trop stricte.**
Désactive la règle ou son groupe, baisse le niveau d’une règle personnelle ou utilise un override ponctuel documenté.

---

## 23. Référence

| Concept | Valeur typique |
|---|---:|
| Intervalle normal de nettoyage | 28 jours |
| Intervalle shimmer | 14 jours |
| Maximum Grail | 21 jours |
| Seuil « bientôt dû » | 80 % |
| Devise par défaut | CHF |
| Modules en mode simple | 6 |
| Modules en mode expert | 14 |

Les valeurs effectivement configurées dans Règles et Réglages ont toujours priorité sur ce manuel.

---

## 24. Glossaire

**EDC** – Every Day Carry, petit groupe de stylos utilisés quotidiennement.

**Feathering** – Diffusion de l’encre le long des fibres du papier.

**Appariement fixe** – Association volontaire stylo–encre toujours respectée par la rotation.

**Grail** – Stylo particulièrement précieux ou important émotionnellement.

**Règle dure** – Règle de sécurité pouvant bloquer une sélection automatique.

**Ink Safety Timer** – Suit la durée pendant laquelle une encre reste dans un stylo.

**Override** – Acceptation consciente et journalisée d’un avertissement ou blocage.

**Reroll** – Nouvelle génération de suggestions évitant les paires déjà montrées.

**Sheen** – Reflet de surface métallique visible sur un papier adapté.

**Shimmer** – Particules scintillantes suspendues demandant davantage de nettoyage.

**Règle souple** – Recommandation modifiant le score sans bloquer l’usage.

**Vac / vacuum filler** – Système à grande capacité généralement plus difficile à nettoyer.
