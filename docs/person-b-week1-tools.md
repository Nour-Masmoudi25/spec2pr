# Partie B après le compte rendu du 27 octobre

Le travail B consiste à préparer la clôture de la semaine 1 pendant que Nour
termine les essais officiels. Les nouveaux outils sont indépendants du moteur
de l'agent : ils lisent des fichiers existants et ne consomment aucun crédit API.

## État récupéré

La branche de travail part du commit
`834104fcf4b11b687a336b0e633daa1b6948be83`, récupéré depuis `main` le
30 octobre 2026. La PR #1 est déjà fusionnée. Le dépôt contient le nouveau prompt,
les reprises après limitation API, les métriques de coût connu et le rapport de
validation Docker fourni par Nour.

Le compte rendu annonce T01 à 3/3 et demande de relancer tout le lot T02 après
épuisement du quota. Ce sont des informations du compte rendu : les rapports
officiels correspondants et les traces ne sont pas présents dans ce checkout.
`runs/benchmarks/` est ignoré par Git, donc un pull ne les récupère pas.

Les essais locaux précédents `reference-check` et `noop-check` sont des contrôles
sans modèle. Ils ne doivent pas remplacer les résultats officiels manquants.

## Travail parallèle et gel du code

Cette livraison ajoute seulement de nouveaux fichiers sur
`codex/person-b-week1-tools`. Elle ne change pas `agent/`, `bench/run.py`,
`bench/prompt.py`, les tâches du benchmark ou les résultats historiques.
Ne pas fusionner cette branche dans `main` avant la fin de la campagne officielle.
Ne pas lancer les essais officiels depuis cette branche : elle a un autre hash.

Nour peut continuer les essais depuis son checkout propre au commit gelé.
L'agrégation peut être faite ensuite depuis la branche B : elle compare les
commits enregistrés dans les rapports, pas le commit courant de l'outil.

## 1 Vérifier la base récupérée

Depuis la racine du clone, avec son environnement Python activé :

```powershell
python -m pytest -q
python bench/validate.py bench/tasks
python bench/validate.py bench/tasks --backend docker
```

Avant les ajouts B, les vérifications locales ont donné 153 tests réussis et
5/5 exercices valides sous Python 3.13.1. La troisième commande nécessite un
moteur Docker Linux actif et l'image `sandbox:py312`. Le rapport Docker déjà
versionné décrit une vérification de Nour, pas une nouvelle exécution locale.

## 2 Agréger les cinq lots officiels

Récupérer les cinq dossiers complets approuvés : chacun contient son
`summary.json` et trois sous-dossiers avec `result.json`, `trace.jsonl` et
`submission.json`. Conserver à part le lot T02 écarté avec sa raison d'exclusion.
Les scripts ne choisissent ni le meilleur essai ni le dernier dossier à votre place.

Remplacer les chemins d'exemple suivants par les cinq vrais rapports :

```powershell
$reports = @(
    'runs/benchmarks/<lot-T01>/summary.json'
    'runs/benchmarks/<lot-T02-relance-complete>/summary.json'
    'runs/benchmarks/<lot-T03>/summary.json'
    'runs/benchmarks/<lot-T04>/summary.json'
    'runs/benchmarks/<lot-T05>/summary.json'
)
python bench/aggregate.py @reports --output RESULTS.generated.md --json-output aggregate-results.json
```

Le script refuse un checkout déclaré sale, des commits d'évaluation différents,
des baselines ou noms d'image différents, un lot incomplet, une tâche répétée, un
contrôle sans modèle ou des métriques manquantes/incohérentes. Les quinze essais
sont inclus, y compris les échecs. Les médianes sont calculées sur les quinze
valeurs individuelles, jamais sur les cinq médianes des lots.

La sortie contient la ligne 0, le taux de réussite sur 15, la médiane des étapes
enregistrées, la médiane du coût connu comme borne inférieure, les erreurs API
enregistrées, le nombre de tâches résolues au moins une fois, pass^3 et le commit.
La médiane du coût total reste inconnue si au moins un essai a un coût inconnu.

Sans `--output`, le tableau apparaît uniquement dans le terminal. Les fichiers
de sortie doivent être nouveaux : aucun `RESULTS.md` existant n'est écrasé.
Après les quinze essais et la revue des preuves, remplacer le tableau de la
ligne 0 dans `RESULTS.md` par le tableau généré et actualiser son texte de statut.

L'outil vérifie les métadonnées déclarées, pas la facturation Groq, l'état réel
d'un ancien checkout ou l'authenticité des fichiers. Examiner les traces pour
décider si un lot doit être exclu pour quota : cette information n'est pas
suffisamment détaillée dans `summary.json` pour automatiser cette décision.

## 3 Chercher une fuite de tests cachés

Passer les mêmes cinq dossiers officiels au contrôle, sans mélanger les anciens
contrôles dont les traces sont volontairement vides :

```powershell
$batches = $reports | ForEach-Object { Split-Path -Parent $_ }
python bench/check_leaks.py @batches --report official-leak-check.json
```

Le script cherche `test_filter_priority.py` et `test_acceptance.py` dans chaque
`trace.jsonl`, y compris les valeurs JSON imbriquées et les noms échappés en
Unicode. Les résultats affichent le fichier, la ligne et le nom trouvé, sans
recopier le contenu potentiellement sensible de la trace.

- Code de sortie 0 : aucun nom trouvé et tous les fichiers sélectionnés lisibles.
- Code 1 : au moins une occurrence trouvée.
- Code 2 : vérification incomplète, par exemple chemin absent, trace vide ou JSON invalide.

Le rapport indique les fichiers inspectés : vérifier qu'il couvre bien les
quinze traces officielles. Zéro occurrence est un contrôle textuel ; il ne
prouve pas à lui seul l'isolation de tous les tests et de leurs contenus.

## 4 Annoter une réussite et un échec

Compléter [le modèle d'annotation](annotated-traces.md) avec les fichiers réels,
les numéros de lignes et les résultats de l'évaluateur. Le document distingue
un échec de code d'une interruption API ou d'un quota épuisé, et explique les
limites du comptage des reprises API dans la version gelée.

Ne pas modifier les traces brutes. Si les quinze essais réussissent, une ancienne
trace de débogage peut illustrer un échec, à condition de la signaler comme
historique et de ne pas l'intégrer aux métriques officielles.

## Vérifier les nouveaux outils

```powershell
python -m pytest bench/tests/test_finish_tools.py -q
python -m pytest -q
```

Les tests des outils créent de petits rapports synthétiques dans des dossiers
temporaires. Ces données ne sont jamais publiées comme performances de l'agent.

Vérification locale du 30 octobre 2026 sous Python 3.13.1 : 39 tests des nouveaux
outils réussis, 192 tests réussis pour la suite complète. La validation des tâches
reste à 5/5. Le premier lancement restreint avait échoué sur les permissions des
dossiers temporaires Windows ; le relancement avec les permissions nécessaires
a réussi. Après démarrage de Docker Desktop, la sonde du moteur Docker a dépassé
son délai de 20 secondes : aucune nouvelle validation Docker n'est revendiquée ici.

Une [proposition pour la semaine 2](week2-multi-agent-design.md) décrit aussi les
rôles planner, tester, implementer et reviewer, avec un budget total partagé.
Il s'agit uniquement d'une conception pour après le gel de la semaine 1.
