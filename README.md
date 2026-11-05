TreeLab est une application de bureau pédagogique dédiée à l’apprentissage des arbres binaires et des arbres binaires de recherche. Elle associe une représentation graphique interactive à des animations pas à pas pour rendre visibles les opérations habituellement étudiées à travers du code ou des schémas statiques.

L’application s’adresse notamment aux étudiants en algorithmique et en structures de données. Elle permet de construire un arbre, de lancer une opération et d’observer son effet sur les nœuds, les liens et les résultats affichés.


Fonctionnalités
Construction et manipulation des arbres
- Créer un arbre binaire en ajoutant une racine, puis des fils gauches ou droits.
- Construire un arbre à partir d’une série de valeurs.
- Générer des arbres à partir d’exemples ou de configurations prédéfinies.
- Insérer et supprimer des valeurs dans un arbre binaire de recherche.
- Modifier la valeur d’un nœud et réorganiser les nœuds sur la surface de dessin.
- Annuler ou rétablir les dernières modifications.
- Enregistrer un arbre dans un fichier JSON et le rouvrir ultérieurement.


Parcours d’arbres
TreeLab permet de visualiser plusieurs parcours et l’ordre dans lequel ils visitent les nœuds :
- Préfixe (RGD) : racine, sous-arbre gauche, sous-arbre droit.
- Infixe (GRD) : sous-arbre gauche, racine, sous-arbre droit.
- Postfixe (GDR) : sous-arbre gauche, sous-arbre droit, racine.
- Infixe inversé (DRG) : sous-arbre droit, racine, sous-arbre gauche.
- Parcours en largeur : visite des nœuds niveau par niveau.
Les animations peuvent montrer les appels récursifs et les étapes de l’exécution afin de relier le parcours affiché à son algorithme.


Mesures et propriétés
L’application aide à explorer les propriétés d’un arbre et de ses nœuds, notamment :
- le nombre de nœuds, de feuilles et de nœuds internes ;
- la hauteur et la largeur de l’arbre ;
- le niveau d’un nœud et ses liens avec son parent ou ses enfants ;
- la somme, la moyenne, les valeurs minimales et maximales ;
- des propriétés de forme et d’équilibre ;
- la validité d’un arbre binaire de recherche.
Les résultats sont accompagnés d’une représentation visuelle et, selon l’opération, d’une trace de son déroulement.


Conversion d’un arbre n-aire
TreeLab inclut un convertisseur d’arbre n-aire vers arbre binaire fondé sur la représentation fils gauche – frère droit :
1. Le premier enfant d’un nœud devient son fils gauche.
2. Chaque enfant suivant est relié comme fils droit de son frère précédent.
Un simulateur pas à pas permet de suivre la création de chaque lien et de comparer la structure d’origine avec sa représentation binaire.


Autres ateliers
- Création et exploration d’arbres d’expression.
- Exemples d’arbres rouge-noir.
- Exercices sous forme de quiz et défis de difficulté progressive.
- Panneau présentant le pseudo-code ou le code associé à certains arbres et opérations.


Surface de dessin interactive
La surface de dessin permet de manipuler la représentation de l’arbre :
- déplacer les nœuds à la souris ;
- zoomer et déplacer la vue ;
- afficher l’arbre en plein écran ;
- utiliser les menus contextuels pour accéder aux actions disponibles sur un nœud ou sur la surface.


Interface
L’interface regroupe la surface de dessin et des panneaux complémentaires pour consulter les résultats, la trace d’exécution, les cours et les représentations de code. Les animations et les commandes d’affichage peuvent être adaptées à l’exploration de chaque opération.
Prérequis
- Python 3.8 ou ultérieur
- Tkinter, généralement inclus dans les distributions standard de Python
Lancer l’application
Depuis le dossier du projet :
python treelab.py
Sous certaines distributions Linux, Tkinter peut devoir être installé séparément à l’aide du gestionnaire de paquets de la distribution.


Exemple de notation d’un arbre n-aire
Les enfants d’un nœud sont indiqués entre parenthèses. Les définitions sont séparées par des points-virgules :
A(B,C,D); B(E,F); C(G)
Dans cet exemple, A est la racine ; B, C et D sont ses enfants. Le simulateur montre comment représenter ces relations dans un arbre binaire.
Public visé
TreeLab est conçu comme un support d’apprentissage et de démonstration pour les cours d’algorithmique et de structures de données, en particulier pour l’étude des arbres, des parcours et des opérations sur les arbres binaires.
