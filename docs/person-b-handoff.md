# Partie B — état et passage à la suite

## Pourquoi ces fichiers ?

1. `target_repo` est le petit projet que l'agent doit améliorer. Il contient
   déjà la gestion des tâches et la sauvegarde JSON, avec 127 tests visibles.
2. Chaque `spec.md` est une consigne donnée à l'agent : ajouter une fonctionnalité.
3. Les tests cachés vérifient si l'agent respecte cette consigne. Ils ne sont
   placés dans aucun dossier accessible à l'agent pendant son travail.
4. La correction de référence est notre solution connue. Elle prouve que
   l'exercice est réalisable, mais elle n'est pas donnée à l'agent.
5. `validate.py` vérifie la qualité des cinq exercices.
6. `run.py` lance chaque exercice depuis zéro et mesure le résultat de l'agent.

## Corrections d'intégration

Les fichiers B manquants sur main sont réunis avec le travail récent de Nour
dans la branche de la PR. La double définition de filter_by_priority dans
l'ancien exemple a été supprimée. Les nouveaux essais démarrent depuis une
copie propre, ce qui évite d'ajouter plusieurs fois la même méthode.

La journalisation de l'agent a été adaptée pour compter un appel au modèle une
seule fois, même si cet appel demande plusieurs commandes. Le scorer peut
ainsi calculer les étapes et les coûts sans doublons. Les outils et le modèle
de la binôme restent les mêmes.

## Travail à faire ensemble

- Démarrer le moteur Docker Linux, construire sandbox:py312 et valider les cinq
  exercices sous Python 3.12.
- Installer requirements.txt, configurer GROQ_API_KEY localement.
- Exécuter les 15 essais réels et reporter les résultats avec le commit utilisé.
- Vérifier qu'au moins deux tâches sont résolues au moins une fois.
- Annoter une trace réellement réussie et une trace réellement échouée.

Les contrôles reference/noop ne remplacent jamais ces essais de l'agent.
Les anciens comptes rendus Day 1/Day 2 sont historiques. Pour l'état actuel,
consulter RESULTS.md, bench/README.md et les rapports benchmark-validation-*.
