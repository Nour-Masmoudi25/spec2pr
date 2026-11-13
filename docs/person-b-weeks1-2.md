# Partie B — semaines 1 et 2

Mise à jour : 3 novembre 2026. Répartition confirmée : **B = tests, évaluation
et preuves** ; Nour développe les agents, le planner et les hooks.

## Le contexte en quelques mots

`tasklib` est le petit projet sur lequel on évalue l'agent. Chaque exercice
demande une fonctionnalité absente. L'agent travaille sur une copie propre,
puis notre évaluateur contrôle sa réponse avec les tests visibles et cachés.
Les corrections de référence servent à vérifier que les exercices sont faisables.
Elles ne doivent pas être données à l'agent ni ajoutées à la bibliothèque de base.

La semaine 1 mesure un seul agent. La semaine 2 prépare plusieurs rôles qui
s'échangent des documents JSON. Tes contrats et tes tests vérifient que ces
échanges sont complets avant de poursuivre le travail.

## Semaine 1 : preuves disponibles

- La bibliothèque de départ et ses 127 tests sont conservés.
- Les cinq exercices originaux ont 65 cas cachés et des corrections validées.
- Nour a publié les 15 essais officiels : **12/15 réussites**, quatre exercices
  résolus sur cinq. Le résultat est dans [RESULTS.md](../RESULTS.md).
- Les résultats ont été réagrégés depuis les vrais fichiers : médiane des pas
  enregistrés = 6, médiane du coût connu = 0,004149 USD. Ce coût est une borne
  inférieure, car certaines réponses API n'ont pas de consommation connue.
- La recherche de noms de tests cachés donne zéro occurrence dans 15 traces,
  soit 79 lignes JSON. Elle complète les vérifications de la sandbox.
- [Deux traces sont maintenant annotées](annotated-traces.md) : T01-1 réussie,
  T05-1 en échec, avec les numéros de ligne et les résultats exacts.

Limite conservée explicitement : l'agent historique ne journalise pas chaque
tentative HTTP interne de reprise. On ne peut donc pas affirmer que la règle
« une ligne par appel physique API » est entièrement satisfaite. Une évolution
de cette journalisation relève de A et doit conserver les résultats historiques.

## Semaine 2 : travail B livré

| Élément | Contenu |
|---|---|
| T06 | Copie indépendante d'une tâche et d'un gestionnaire ; modèles + store. |
| T07 | Classement stable par priorité ; modèles + store. |
| T08 | Sérialisation JSON en mémoire ; storage + exports publics. |
| T09 | Renommage groupé atomique. |
| T10 | Pagination avec validation des arguments. |
| Contrats | Six schémas JSON, validation des types, champs, références, chemins et couverture des AC. |
| Entrées planner | Dix `spec.json`, comprenant le texte complet et les critères numérotés. |
| Contrôle des plans | `bench/check_plans.py` refuse les plans absents, invalides ou incomplets. |
| Contrôle des hooks | `bench/check_hooks.py` teste dix situations contrôlées et conserve les décisions et empreintes des scripts. |
| Architecture | [ARCHITECTURE.md](../ARCHITECTURE.md) définit qui vérifie chaque document et quoi faire en cas d'erreur. |

Les nouveaux exercices ajoutent **70 cas cachés**, soit **135 au total**.
Trois corrections touchent deux fichiers. Les dix exercices sont indépendants
et utilisent la même base Git figée. Les fonctionnalités restent absentes du
code cible ; seules les corrections de référence les implémentent.

Preuves : [validation locale](../evals/week2/validation-local.json) et
[validation Docker](../evals/week2/validation-docker.json) : **10/10** chacune.
La suite complète donne **311 tests réussis**, dont **119 tests des contrats
et contrôles de passation** ; le [rapport pytest](../evals/week2/tests.xml)
est conservé avec les preuves.
Les tests des contrats et des outils utilisent des exemples simulés ; ils ne
représentent pas des plans réellement produits par un modèle.

## Ce que Nour doit fournir pour fermer la semaine 2 ensemble

1. Les quatre rôles configurés, le planner et ses reprises limitées à une.
2. Dix plans réellement produits, avec les traces des appels et des rejets.
3. Les deux hooks branchés et une preuve réelle de refus d'édition d'un test.
4. Les cinq transcriptions de l'équipe sur T01–T05 et les ambiguïtés de passation
   observées pendant ces essais.

À ce stade ces fichiers ne sont pas présents dans `main` récupéré. Les contrôles
B sont prêts à les recevoir. **La semaine 2 commune reste à intégrer** ; aucun
plan ni résultat d'agent n'est inventé pour cocher les cases. Aucun crédit API
n'a été consommé par les validations de cette livraison.

## Commandes à refaire

Depuis la racine du clone, avec l'environnement Python activé :

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m pytest tests/contracts -q
python bench/validate.py bench/tasks
python bench/validate.py bench/tasks --backend docker
```

Les deux dernières commandes doivent afficher `10/10 tasks valid`.
Les commandes d'intégration des plans et hooks sont décrites dans l'architecture.
Le plafond proposé de 1 USD dans les specs peut être ajusté ensemble avant les
appels réels ; c'est un paramètre de contrat, pas une dépense réalisée.

Attention au changement de taille : `--tasks bench/tasks --n 3` sélectionne
maintenant **30 essais**. La ligne historique de semaine 1 reste à 15 essais.
