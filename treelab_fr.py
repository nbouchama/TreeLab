#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==========================================================================
 TreeLab — Arbres binaires : outil pédagogique (Algorithmique, ISIL 2)
 by Nadir BOUCHAMA
==========================================================================
 Lancer :  python treelab.py   (placer logo.png à côté du script)        (Python 3.8+, Tkinter inclus)

 Fonctionnalités
 ---------------
 * Construction : arbre binaire quelconque (clic sur un nœud + ajout de fils),
   ABR (insertion / suppression), génération aléatoire, exemples, miroir.
 * Parcours animés : préfixé (RGD), infixé (GRD), postfixé (GDR),
   en largeur, infixé inversé (DRG) + trace des appels récursifs.
 * Mesures animées : nombre de nœuds, feuilles, nœuds internes, nœuds à 1 ou
   2 fils, hauteur, largeur, somme, moyenne, minimum, maximum, occurrences,
   pairs/impairs, occurrences, filtrage des paires/multiples, nombres premiers,
   infos sur un nœud (niveau, père, frère, ancêtres...).
 * Tests : ABR ?, localement complet ?, parfait ?, complet (tas) ?,
   dégénéré ?, équilibré (AVL) ?  + diagnostic complet.
 * ABR : recherche, min, max, successeur, prédécesseur, équilibrage.
 * Quiz : questions aléatoires avec correction animée.
 * Panneau « Algorithme » : le pseudo-code de l'opération en cours.

 Guide de lecture du fichier
 ---------------------------
 1. Les classes Noeud et NoeudNAire définissent les structures en mémoire.
 2. Les fonctions situées avant ALGOS sont des outils de calcul indépendants
    de l'interface : parcours, mesures, propriétés et conversions.
 3. ALGOS, EXEMPLES et les blocs de code pédagogique fournissent le contenu
    affiché dans les différents ateliers.
 4. Application construit l'interface Tkinter et relie les boutons aux
    opérations sur l'arbre.
 5. Le canevas dessine les nœuds ; Ev et le moteur d'animation pilotent les
    étapes, le journal, les couleurs et les cadres de récursion.
 6. Les méthodes de construction, parcours, mesures, tests, ABR et quiz sont
    séparées par des titres de section dans Application.

 Convention générale : un arbre vide est représenté par None ; les liens
 gauche et droite sont des références vers d'autres objets Noeud. Les
 fonctions qui reçoivent un arbre ne le modifient que si leur nom décrit une
 opération de modification (insertion, suppression, miroir, conversion).
==========================================================================
"""
import os
import json
import random
import re
import math
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont

# ----------------------------------------------------------------------
#  STRUCTURE DE DONNÉES
# ----------------------------------------------------------------------


class Noeud:
    """Nœud binaire : valeur, liens vers les enfants et couleur éventuelle.

    Les arbres ordinaires n'utilisent pas couleur_rn ; l'atelier rouge-noir
    s'en sert pour dessiner les nœuds rouges et noirs.
    """

    def __init__(self, valeur):
        self.valeur = valeur
        self.gauche = None
        self.droite = None
        self.couleur_rn = "N"


class NoeudNAire:
    """Nœud n-aire dont la liste enfants peut contenir un nombre quelconque de fils."""
    def __init__(self, valeur):
        self.valeur = valeur
        self.enfants = []


def parser_arbre_naire(texte):
    """Valide la notation parent-enfants et renvoie la racine et les listes de fils.

    Chaque nœud peut être défini une seule fois. Les feuilles peuvent être
    implicites. Les cycles, références partagées et éléments inaccessibles
    sont rejetés par ValueError.
    """
    enfants_par_noeud = {}
    definitions = set()
    racine = None
    for morceau in texte.split(";"):
        morceau = morceau.strip()
        if not morceau:
            continue
        m = re.fullmatch(r"([^()\s,]+)(?:\(([^()]*)\))?", morceau)
        if not m:
            raise ValueError(f"Notation invalide : {morceau}")
        nom, liste = m.group(1), m.group(2)
        if nom in definitions:
            raise ValueError(f"Le nœud {nom} est défini plusieurs fois.")
        definitions.add(nom)
        if racine is None:
            racine = nom
        elements = (liste or "").split(",") if liste else []
        if any(not x.strip() for x in elements):
            raise ValueError(f"Liste d’enfants incomplète pour {nom}.")
        enfants = [x.strip() for x in elements]
        if len(enfants) != len(set(enfants)):
            raise ValueError(f"Le nœud {nom} cite plusieurs fois le même enfant.")
        enfants_par_noeud[nom] = enfants
        for enfant in enfants:
            enfants_par_noeud.setdefault(enfant, [])
    if racine is None:
        raise ValueError("Saisissez une notation d’arbre.")

    vus, actifs, parent_de_noeud = set(), set(), {}
    def verifier(nom):
        """Parcourt les descendants pour détecter cycles et parents multiples."""
        if nom in actifs:
            raise ValueError(f"Cycle détecté au nœud {nom}.")
        if nom in vus:
            raise ValueError(f"Le nœud {nom} est partagé par plusieurs parents.")
        vus.add(nom)
        actifs.add(nom)
        for enfant in enfants_par_noeud[nom]:
            if enfant in parent_de_noeud:
                raise ValueError(f"Le nœud {enfant} a plusieurs parents.")
            parent_de_noeud[enfant] = nom
            verifier(enfant)
        actifs.remove(nom)
    verifier(racine)
    if len(vus) != len(enfants_par_noeud):
        raise ValueError("La notation contient des nœuds inaccessibles depuis la racine.")
    return racine, enfants_par_noeud


def arbre_expression(expression):
    """Transforme une expression infixe en arbre binaire d'opérateurs.

    Le tri des opérateurs utilise leurs priorités, puis une pile postfixée
    construit les nœuds. Les erreurs de syntaxe sont signalées par ValueError.
    """
    tokens = re.findall(r"\d+(?:\.\d+)?|[A-Za-z_]\w*|[()+\-*/^]", expression.replace(" ", ""))
    if "".join(tokens) != expression.replace(" ", "") or not tokens:
        raise ValueError("Expression invalide : utilisez nombres, variables, + - * / ^ et parenthèses.")
    precedent = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
    sortie, ops = [], []
    attendu = True
    for tok in tokens:
        if re.fullmatch(r"\d+(?:\.\d+)?|[A-Za-z_]\w*", tok):
            if not attendu: raise ValueError("Opérande manquant entre deux valeurs.")
            sortie.append(tok); attendu = False
        elif tok == "(":
            if not attendu: raise ValueError("Opérateur attendu avant la parenthèse.")
            ops.append(tok)
        elif tok == ")":
            while ops and ops[-1] != "(": sortie.append(ops.pop())
            if not ops: raise ValueError("Parenthèses déséquilibrées.")
            ops.pop(); attendu = False
        else:
            if attendu: raise ValueError("Opérande manquant.")
            while ops and ops[-1] in precedent and (precedent[ops[-1]] > precedent[tok] or
                    (precedent[ops[-1]] == precedent[tok] and tok != "^")):
                sortie.append(ops.pop())
            ops.append(tok); attendu = True
    if attendu: raise ValueError("L'expression se termine par un opérateur.")
    while ops:
        op = ops.pop()
        if op == "(": raise ValueError("Parenthèses déséquilibrées.")
        sortie.append(op)
    pile = []
    for tok in sortie:
        if tok in precedent:
            if len(pile) < 2: raise ValueError("Expression incomplète.")
            droite, gauche = pile.pop(), pile.pop()
            n = Noeud(tok); n.gauche, n.droite = gauche, droite; pile.append(n)
        else: pile.append(Noeud(tok))
    if len(pile) != 1: raise ValueError("Expression invalide.")
    return pile[0]


def texte_notations(notation, racine, enfants):
    """Construit le texte des cinq notations à partir de la table parent -> enfants.

    notation est la notation parent-enfants brute, racine le nom de la racine et
    enfants un dictionnaire {nom: [noms des fils]} dont l'ordre est conservé.
    """
    def imbrique(nom):
        fils = enfants[nom]
        return nom if not fils else f"{nom}({', '.join(imbrique(f) for f in fils)})"

    lignes = ["1) NOTATION PARENT-ENFANTS", notation.strip(), "",
              "2) NOTATION PARENTHÉSÉE IMBRIQUÉE", imbrique(racine), "",
              "3) REPRÉSENTATION INDENTÉE"]

    def dessiner_indente(nom, prefixe="", dernier=True, racine_locale=False):
        if racine_locale:
            lignes.append(nom)
        else:
            lignes.append(prefixe + ("└── " if dernier else "├── ") + nom)
        fils = enfants[nom]
        suite = "" if racine_locale else prefixe + ("    " if dernier else "│   ")
        for i, fils_nom in enumerate(fils):
            dessiner_indente(fils_nom, suite, i == len(fils) - 1)
    dessiner_indente(racine, racine_locale=True)
    lignes += ["", "4) LISTE DES ENFANTS"]
    for nom, fils in enfants.items():
        lignes.append(f"{nom} : {', '.join(fils) if fils else 'aucun'}")
    lignes += ["", "5) CODAGE BINAIRE (fils gauche / frère droit)"]
    for nom, fils in enfants.items():
        gauche = fils[0] if fils else "NULL"
        lignes.append(f"{nom} : gauche = {gauche}")
        for i in range(1, len(fils)):
            lignes.append(f"{fils[i]} : droite = frère {fils[i - 1]}")
    return "\n".join(lignes)


def notations_depuis_arbre_binaire(r):
    """Produit les cinq notations de l'arbre binaire dessiné.

    Les valeurs en double sont rendues uniques par un suffixe (_1, _2...) afin
    que chaque nœud garde un nom distinct dans les notations.
    """
    if r is None:
        return "Arbre vide : aucune notation à afficher."
    ns = noeuds(r, "RGD")
    freq = {}
    for n in ns:
        freq[str(n.valeur)] = freq.get(str(n.valeur), 0) + 1
    vus, noms = {}, {}
    for n in ns:
        base = str(n.valeur)
        if freq[base] > 1:
            vus[base] = vus.get(base, 0) + 1
            noms[n] = f"{base}_{vus[base]}"
        else:
            noms[n] = base
    enfants = {}
    for niveau in niveaux(r):
        for n in niveau:
            enfants[noms[n]] = [noms[f] for f in (n.gauche, n.droite) if f is not None]
    morceaux = [f"{noms[n]}({','.join(noms[f] for f in (n.gauche, n.droite) if f is not None)})"
                for n in ns if nb_fils(n) > 0]
    notation = "; ".join(morceaux) if morceaux else noms[r]
    texte = texte_notations(notation, noms[r], enfants)
    if any(c > 1 for c in freq.values()):
        texte += ("\n\nNote : certaines valeurs apparaissent plusieurs fois ; elles sont "
                  "numérotées (_1, _2...) pour distinguer les nœuds.")
    return texte


def code_structure_python(r):
    """Sérialise l'arbre en code Python recréant ses valeurs et ses liens."""
    lignes = ["class Noeud:", "    def __init__(self, valeur):", "        self.valeur = valeur",
              "        self.gauche = None", "        self.droite = None", "", "# Arbre courant"]
    if r is None: return "\n".join(lignes + ["racine = None"])
    lignes += ["", "def construire(t):", "    if t is None: return None",
               "    n = Noeud(t[0])",
               "    n.gauche = construire(t[1])",
               "    n.droite = construire(t[2])",
               "    return n",
               "", "racine = construire(" + repr(_tuple_arbre(r)) + ")"]
    return "\n".join(lignes)


def _tuple_arbre(r):
    """Convertit récursivement un arbre en triplets (valeur, gauche, droite)."""
    return None if r is None else (r.valeur, _tuple_arbre(r.gauche), _tuple_arbre(r.droite))


def code_structure_c(r):
    """Produit un exemple C autonome avec allocation et affectation des fils."""
    entete = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n"
              "typedef struct Noeud {\n    char *valeur;\n"
              "    struct Noeud *gauche, *droite;\n} Noeud;\n\n"
              "Noeud *creer(const char *v) {\n"
              "    Noeud *n = malloc(sizeof *n);\n"
              "    if (!n) return NULL;\n"
              "    n->valeur = malloc(strlen(v) + 1);\n"
              "    if (!n->valeur) { free(n); return NULL; }\n"
              "    strcpy(n->valeur, v);\n"
              "    n->gauche = n->droite = NULL;\n    return n;\n}\n\n")
    if r is None:
        return entete + "int main(void) {\n    Noeud *racine = NULL;\n    return 0;\n}\n"
    ns = noeuds(r, "RGD")
    ids = {n: f"n{i}" for i, n in enumerate(ns)}
    lignes = ["int main(void) {"]
    for n in ns:
        valeur = str(n.valeur).replace("\\", "\\\\").replace('"', '\\"')
        lignes.append(f'    Noeud *{ids[n]} = creer("{valeur}");')
    for n in ns:
        if n.gauche:
            lignes.append(f"    {ids[n]}->gauche = {ids[n.gauche]};")
        if n.droite:
            lignes.append(f"    {ids[n]}->droite = {ids[n.droite]};")
    lignes += [f"    Noeud *racine = {ids[r]};", "    (void)racine;", "    return 0;", "}"]
    return entete + "\n".join(lignes) + "\n"


def code_structure_java(r):
    """Génère une classe Java autonome qui reconstruit l'arbre courant.

    Les nœuds sont d'abord créés, puis leurs liens sont affectés afin que
    l'ordre des allocations ne dépende pas de la forme de l'arbre.
    """
    lignes = ["public class TreeLabTree {",
              "    static class Noeud {",
              "        String valeur;",
              "        Noeud gauche, droite;",
              "        Noeud(String valeur) { this.valeur = valeur; }",
              "    }", "", "    public static void main(String[] args) {"]
    if r is None:
        lignes += ["        Noeud racine = null;"]
    else:
        ns = noeuds(r, "RGD")
        ids = {n: f"n{i}" for i, n in enumerate(ns)}
        for n in ns:
            valeur = str(n.valeur).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lignes.append(f'        Noeud {ids[n]} = new Noeud("{valeur}");')
        for n in ns:
            if n.gauche:
                lignes.append(f"        {ids[n]}.gauche = {ids[n.gauche]};")
            if n.droite:
                lignes.append(f"        {ids[n]}.droite = {ids[n.droite]};")
        lignes.append(f"        Noeud racine = {ids[r]};")
    lignes += ["        System.out.println(\"Arbre construit\");", "    }", "}"]
    return "\n".join(lignes) + "\n"


class Ev:
    """Une étape prévue par un algorithme avant son animation.

    noeud désigne la cible visuelle ; kind décrit le type d'étape ; msg est
    affiché dans la trace ; out ajoute éventuellement une valeur à la séquence.
    Les kinds call et return gèrent les cadres des appels récursifs.
    """
    __slots__ = ("noeud", "kind", "msg", "out")

    def __init__(self, noeud, kind, msg="", out=None):
        self.noeud = noeud   # nœud à mettre en évidence (ou None)
        self.kind = kind     # enter | visit | skip | found | bad | path | empty
        self.msg = msg       # ligne affichée dans la trace
        self.out = out       # valeur ajoutée à la séquence affichée (parcours)


# ----------------------------------------------------------------------
#  FONCTIONS « PURES » SUR LES ARBRES
# ----------------------------------------------------------------------

def est_feuille(n):
    """Indique si n existe et ne possède aucun enfant."""
    return n is not None and n.gauche is None and n.droite is None


def nb_fils(n):
    """Compte les liens gauche et droit non vides du nœud."""
    return (n.gauche is not None) + (n.droite is not None)


def taille(n):
    """Compte récursivement les nœuds du sous-arbre, racine comprise."""
    return 0 if n is None else 1 + taille(n.gauche) + taille(n.droite)


def hauteur(n):
    """Hauteur en arêtes : arbre vide = -1, feuille = 0."""
    return -1 if n is None else 1 + max(hauteur(n.gauche), hauteur(n.droite))


def nb_feuilles(n):
    """Compte les nœuds terminaux, c'est-à-dire ceux sans enfants."""
    if n is None:
        return 0
    if est_feuille(n):
        return 1
    return nb_feuilles(n.gauche) + nb_feuilles(n.droite)


def noeuds(n, ordre="RGD"):
    """Liste des nœuds dans l'ordre de parcours demandé (lettres R, G, D)."""
    res = []

    def rec(x):
        if x is None:
            return
        for lettre in ordre:
            if lettre == "R":
                res.append(x)
            elif lettre == "G":
                rec(x.gauche)
            else:
                rec(x.droite)
    rec(n)
    return res


def valeurs(n, ordre="RGD"):
    """Retourne les valeurs selon l'ordre de visite demandé."""
    return [x.valeur for x in noeuds(n, ordre)]


def niveaux(racine):
    """Renvoie les nœuds sous forme de listes, un groupe par niveau."""
    res = []
    courant = [racine] if racine else []
    while courant:
        res.append(courant)
        suivant = []
        for x in courant:
            if x.gauche:
                suivant.append(x.gauche)
            if x.droite:
                suivant.append(x.droite)
        courant = suivant
    return res


def somme(n):
    """Additionne les valeurs numériques de l'arbre."""
    return sum(valeurs(n))


def minimum(n):
    """Renvoie la plus petite valeur, ou None si l'arbre est vide."""
    v = valeurs(n)
    return min(v) if v else None


def maximum(n):
    """Renvoie la plus grande valeur, ou None si l'arbre est vide."""
    v = valeurs(n)
    return max(v) if v else None


def est_premier(n):
    """Teste si un entier est premier (les entiers négatifs, 0 et 1 ne le sont pas)."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def chemin_vers(n, cible):
    """Renvoie le chemin d'identités de n à cible, ou None si elle est absente."""
    if n is None:
        return None
    if n is cible:
        return [n]
    for f in (n.gauche, n.droite):
        c = chemin_vers(f, cible)
        if c:
            return [n] + c
    return None


def parent_de(racine, cible):
    """Renvoie le parent de cible ; la racine et les nœuds absents n'ont pas de parent."""
    ch = chemin_vers(racine, cible)
    if ch and len(ch) >= 2:
        return ch[-2]
    return None


def est_strict(racine):
    """Vérifie que chaque nœud a zéro ou deux enfants."""
    return all(nb_fils(x) != 1 for x in noeuds(racine))


def est_degenere(racine):
    """Vérifie que chaque nœud a au plus un enfant."""
    return all(nb_fils(x) <= 1 for x in noeuds(racine))


def est_equilibre(racine):
    """Vérifie localement la condition AVL sur la différence des hauteurs."""
    return all(abs(hauteur(x.gauche) - hauteur(x.droite)) <= 1 for x in noeuds(racine))


def est_parfait(racine):
    """Vérifie qu'un arbre contient tous les nœuds de chacun de ses niveaux."""
    if racine is None:
        return True
    return taille(racine) == 2 ** (hauteur(racine) + 1) - 1


def est_presque_complet(racine):
    """Vérifie la forme d'un arbre de tas : dernier niveau rempli à gauche."""
    if racine is None:
        return True
    file = [racine]
    vu_vide = False
    while file:
        n = file.pop(0)
        if n is None:
            vu_vide = True
        else:
            if vu_vide:
                return False
            file.append(n.gauche)
            file.append(n.droite)
    return True


def est_abr(racine):
    """Teste l'ordre ABR en vérifiant que le parcours infixé est strictement croissant."""
    v = valeurs(racine, "GRD")
    return all(a < b for a, b in zip(v, v[1:]))


def construire_equilibre(vals):
    """Construit un ABR équilibré depuis une séquence déjà triée."""
    if not vals:
        return None
    m = len(vals) // 2
    n = Noeud(vals[m])
    n.gauche = construire_equilibre(vals[:m])
    n.droite = construire_equilibre(vals[m + 1:])
    return n


def depuis_tuple(t):
    """Reconstruit un arbre depuis la forme imbriquée valeur/gauche/droite."""
    if t is None:
        return None
    n = Noeud(t[0])
    n.gauche = depuis_tuple(t[1])
    n.droite = depuis_tuple(t[2])
    return n


def fmt(v):
    """Formate les résultats d'algorithme, notamment les valeurs absentes et flottantes."""
    if v is None:
        return "∅"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def enveloppe_convexe(points):
    """Calcule le contour extérieur des points avec l'algorithme monotone."""
    points = sorted(set(points))
    if len(points) <= 1:
        return points

    def produit_croise(o, a, b):
        """Mesure le virage orienté entre trois points du contour."""
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    bas = []
    for point in points:
        while len(bas) >= 2 and produit_croise(bas[-2], bas[-1], point) <= 0:
            bas.pop()
        bas.append(point)
    haut = []
    for point in reversed(points):
        while len(haut) >= 2 and produit_croise(haut[-2], haut[-1], point) <= 0:
            haut.pop()
        haut.append(point)
    return bas[:-1] + haut[:-1]


# ----------------------------------------------------------------------
#  TEXTES PÉDAGOGIQUES
# ----------------------------------------------------------------------

# ALGOS regroupe le pseudo-code affiché à droite ; COURS, EXEMPLES et les
# chaînes de code plus bas alimentent les fiches et ateliers de l'interface.

ALGOS = {
    "prefixe": ("Parcours PRÉFIXÉ  (R G D)", """\
Procédure Préfixe(A : ^Noeud)
Début
  Si A ≠ NIL Alors
     Traiter(A^.valeur)      // R : la Racine d'abord
     Préfixe(A^.gauche)      // G : puis le sous-arbre Gauche
     Préfixe(A^.droit)       // D : puis le sous-arbre Droit
  FinSi
Fin

Idée : « on traite le nœud AVANT ses fils ».
Usage : copier un arbre, écrire une expression en notation préfixée."""),
    "infixe": ("Parcours INFIXÉ  (G R D)", """\
Procédure Infixe(A : ^Noeud)
Début
  Si A ≠ NIL Alors
     Infixe(A^.gauche)       // G : d'abord le sous-arbre Gauche
     Traiter(A^.valeur)      // R : puis la Racine
     Infixe(A^.droit)        // D : enfin le sous-arbre Droit
  FinSi
Fin

Idée : « le nœud est traité ENTRE ses deux fils ».
Propriété : sur un ABR, le parcours infixé donne les valeurs
triées dans l'ordre croissant."""),
    "postfixe": ("Parcours POSTFIXÉ  (G D R)", """\
Procédure Postfixe(A : ^Noeud)
Début
  Si A ≠ NIL Alors
     Postfixe(A^.gauche)     // G : sous-arbre Gauche
     Postfixe(A^.droit)      // D : sous-arbre Droit
     Traiter(A^.valeur)      // R : la Racine en dernier
  FinSi
Fin

Idée : « le nœud est traité APRÈS ses fils ».
Usage : libérer un arbre, calculer hauteur / taille (on a besoin
des résultats des fils avant de traiter le père)."""),
    "inverse": ("Parcours infixé INVERSÉ  (D R G)", """\
Procédure InfixeInverse(A : ^Noeud)
Début
  Si A ≠ NIL Alors
     InfixeInverse(A^.droit)    // D
     Traiter(A^.valeur)         // R
     InfixeInverse(A^.gauche)   // G
  FinSi
Fin

Sur un ABR : valeurs dans l'ordre DÉCROISSANT."""),
    "largeur": ("Parcours en LARGEUR (niveau par niveau)", """\
Procédure Largeur(A : ^Noeud)
Var F : File de ^Noeud ; P : ^Noeud
Début
  Si A ≠ NIL Alors
     Enfiler(F, A)
     TantQue non FileVide(F) Faire
        P ← Défiler(F)
        Traiter(P^.valeur)
        Si P^.gauche ≠ NIL Alors Enfiler(F, P^.gauche) FinSi
        Si P^.droit  ≠ NIL Alors Enfiler(F, P^.droit)  FinSi
     FinTQ
  FinSi
Fin

Contrairement aux 3 autres parcours (récursifs / pile),
celui-ci utilise une FILE (FIFO)."""),
    "nb_noeuds": ("Nombre de nœuds", """\
Fonction NbNoeuds(A : ^Noeud) : Entier
Début
  Si A = NIL Alors
     Retourner 0
  Sinon
     Retourner 1 + NbNoeuds(A^.gauche) + NbNoeuds(A^.droit)
  FinSi
Fin"""),
    "feuilles": ("Nombre de feuilles", """\
Fonction NbFeuilles(A : ^Noeud) : Entier
Début
  Si A = NIL Alors
     Retourner 0
  Sinon Si (A^.gauche = NIL) ET (A^.droit = NIL) Alors
     Retourner 1                        // c'est une feuille
  Sinon
     Retourner NbFeuilles(A^.gauche) + NbFeuilles(A^.droit)
  FinSi
Fin"""),
    "internes": ("Nombre de nœuds internes", """\
Fonction NbInternes(A : ^Noeud) : Entier
Début
  Si (A = NIL) OU ((A^.gauche = NIL) ET (A^.droit = NIL)) Alors
     Retourner 0                        // vide ou feuille
  Sinon
     Retourner 1 + NbInternes(A^.gauche) + NbInternes(A^.droit)
  FinSi
Fin

Relation : NbNoeuds = NbFeuilles + NbInternes"""),
    "un_fils": ("Nombre de nœuds à UN seul fils", """\
Fonction NbUnFils(A : ^Noeud) : Entier
Var c : Entier
Début
  Si A = NIL Alors Retourner 0 FinSi
  c ← 0
  Si (A^.gauche = NIL) XOR (A^.droit = NIL) Alors c ← 1 FinSi
  Retourner c + NbUnFils(A^.gauche) + NbUnFils(A^.droit)
Fin"""),
    "deux_fils": ("Nombre de nœuds à DEUX fils", """\
Fonction NbDeuxFils(A : ^Noeud) : Entier
Var c : Entier
Début
  Si A = NIL Alors Retourner 0 FinSi
  c ← 0
  Si (A^.gauche ≠ NIL) ET (A^.droit ≠ NIL) Alors c ← 1 FinSi
  Retourner c + NbDeuxFils(A^.gauche) + NbDeuxFils(A^.droit)
Fin

Propriété : dans un arbre binaire,
   NbFeuilles = NbDeuxFils + 1"""),
    "hauteur": ("Hauteur", """\
Fonction Hauteur(A : ^Noeud) : Entier
Début
  Si A = NIL Alors
     Retourner -1             // convention : arbre vide = -1
  Sinon
     Retourner 1 + Max( Hauteur(A^.gauche), Hauteur(A^.droit) )
  FinSi
Fin

Convention : hauteur(feuille) = 0 (en arêtes).
Si votre cours compte en nœuds : arbre vide = 0, feuille = 1."""),
    "largeur_niv": ("Largeur (nombre de nœuds par niveau)", """\
Procédure Largeur(A)         // variante du parcours en largeur
Début
  Enfiler(F, A) ; niveau ← 0
  TantQue non FileVide(F) Faire
     n ← Taille(F)            // nombre de nœuds du niveau courant
     Écrire("niveau", niveau, ":", n, "nœuds")
     Pour i ← 1 à n Faire
        P ← Défiler(F)
        Enfiler(F, fils de P non NIL)
     FinPour
     niveau ← niveau + 1
  FinTQ
Fin"""),
    "somme": ("Somme des valeurs", """\
Fonction Somme(A : ^Noeud) : Entier
Début
  Si A = NIL Alors
     Retourner 0
  Sinon
     Retourner A^.valeur + Somme(A^.gauche) + Somme(A^.droit)
  FinSi
Fin

Moyenne = Somme(A) / NbNoeuds(A)"""),
    "min": ("Minimum (arbre quelconque)", """\
Fonction Min(A : ^Noeud) : Entier
Var m : Entier
Début
  // précondition : A ≠ NIL
  m ← A^.valeur
  Si A^.gauche ≠ NIL Alors m ← MinEntiers(m, Min(A^.gauche)) FinSi
  Si A^.droit  ≠ NIL Alors m ← MinEntiers(m, Min(A^.droit))  FinSi
  Retourner m
Fin

Dans un arbre quelconque il faut visiter TOUS les nœuds : O(n).
(Dans un ABR, on descend simplement à gauche : O(h).)"""),
    "max": ("Maximum (arbre quelconque)", """\
Fonction Max(A : ^Noeud) : Entier
Var m : Entier
Début
  // précondition : A ≠ NIL
  m ← A^.valeur
  Si A^.gauche ≠ NIL Alors m ← MaxEntiers(m, Max(A^.gauche)) FinSi
  Si A^.droit  ≠ NIL Alors m ← MaxEntiers(m, Max(A^.droit))  FinSi
  Retourner m
Fin

Dans un arbre quelconque il faut visiter TOUS les nœuds : O(n)."""),
    "occurrences": ("Nombre d'occurrences d'une valeur", """\
Fonction Occ(A : ^Noeud ; x : Entier) : Entier
Début
  Si A = NIL Alors Retourner 0 FinSi
  Si A^.valeur = x Alors
     Retourner 1 + Occ(A^.gauche, x) + Occ(A^.droit, x)
  Sinon
     Retourner Occ(A^.gauche, x) + Occ(A^.droit, x)
  FinSi
Fin"""),
    "premiers": ("Nombres premiers de l'arbre", """\
Fonction EstPremier(n : Entier) : Booléen
Début
  Si n < 2 Alors Retourner Faux FinSi
  Pour d ← 2 à ⌊√n⌋ Faire
    Si n MOD d = 0 Alors Retourner Faux FinSi
  FinPour
  Retourner Vrai
Fin

Fonction NbPremiers(A : ^Noeud) : Entier
Début
  Si A = NIL Alors Retourner 0 FinSi
  c ← 0
  Si EstPremier(A^.valeur) Alors c ← 1 FinSi
  Retourner c + NbPremiers(A^.gauche) + NbPremiers(A^.droit)
Fin"""),
    "parite": ("Valeurs paires / impaires", """\
Fonction NbPairs(A : ^Noeud) : Entier
Début
  Si A = NIL Alors Retourner 0 FinSi
  Si A^.valeur MOD 2 = 0 Alors
     Retourner 1 + NbPairs(A^.gauche) + NbPairs(A^.droit)
  Sinon
     Retourner NbPairs(A^.gauche) + NbPairs(A^.droit)
  FinSi
Fin"""),
    "recherche": ("Recherche dans un arbre quelconque", """\
Fonction Recherche(A : ^Noeud ; x : Entier) : ^Noeud
Var P : ^Noeud
Début
  Si A = NIL Alors Retourner NIL FinSi
  Si A^.valeur = x Alors Retourner A FinSi
  P ← Recherche(A^.gauche, x)
  Si P ≠ NIL Alors Retourner P FinSi
  Retourner Recherche(A^.droit, x)
Fin

Il faut explorer les deux sous-arbres : O(n) dans le pire cas."""),
    "recherche_abr": ("Recherche dans un ABR", """\
Fonction RechercheABR(A : ^Noeud ; x : Entier) : ^Noeud
Début
  Si (A = NIL) OU (A^.valeur = x) Alors
     Retourner A
  Sinon Si x < A^.valeur Alors
     Retourner RechercheABR(A^.gauche, x)
  Sinon
     Retourner RechercheABR(A^.droit, x)
  FinSi
Fin

On élimine un sous-arbre à chaque comparaison : O(h)
(O(log n) si l'arbre est équilibré, O(n) s'il est dégénéré)."""),
    "min_abr": ("Minimum d'un ABR", """\
Fonction MinABR(A : ^Noeud) : ^Noeud
Début
  Si A^.gauche = NIL Alors
     Retourner A                 // plus de fils gauche : c'est le min
  Sinon
     Retourner MinABR(A^.gauche)
  FinSi
Fin

Le minimum est le nœud le plus à GAUCHE : O(h)."""),
    "max_abr": ("Maximum d'un ABR", """\
Fonction MaxABR(A : ^Noeud) : ^Noeud
Début
  Si A^.droit = NIL Alors
     Retourner A                 // plus de fils droit : c'est le max
  Sinon
     Retourner MaxABR(A^.droit)
  FinSi
Fin

Le maximum est le nœud le plus à DROITE : O(h)."""),
    "insertion": ("Insertion dans un ABR", """\
Procédure InsérerABR(VAR A : ^Noeud ; x : Entier)
Début
  Si A = NIL Alors
     Allouer(A) ; A^.valeur ← x
     A^.gauche ← NIL ; A^.droit ← NIL
  Sinon Si x < A^.valeur Alors
     InsérerABR(A^.gauche, x)
  Sinon Si x > A^.valeur Alors
     InsérerABR(A^.droit, x)
  FinSi                          // x = A^.valeur : déjà présent
Fin

Toute nouvelle valeur devient une FEUILLE. Complexité O(h)."""),
    "suppression": ("Suppression dans un ABR", """\
Procédure SupprimerABR(VAR A : ^Noeud ; x : Entier)
Var T : ^Noeud
Début
  Si A = NIL Alors                           // x absent
  Sinon Si x < A^.valeur Alors SupprimerABR(A^.gauche, x)
  Sinon Si x > A^.valeur Alors SupprimerABR(A^.droit, x)
  Sinon                                      // nœud à supprimer trouvé
     Si A^.gauche = NIL Alors                // 0 ou 1 fils (droit)
        T ← A ; A ← A^.droit ; Libérer(T)
     Sinon Si A^.droit = NIL Alors           // 1 fils (gauche)
        T ← A ; A ← A^.gauche ; Libérer(T)
     Sinon                                   // 2 fils
        A^.valeur ← Min(A^.droit)            // successeur infixé
        SupprimerABR(A^.droit, A^.valeur)
     FinSi
  FinSi
Fin"""),
    "successeur": ("Successeur / prédécesseur infixé (ABR)", """\
Fonction Successeur(A, x : ^Noeud) : ^Noeud
Var S : ^Noeud
Début
  Si x^.droit ≠ NIL Alors
     Retourner MinABR(x^.droit)        // min du sous-arbre droit
  FinSi
  S ← NIL
  TantQue A ≠ x Faire                  // on descend depuis la racine
     Si x^.valeur < A^.valeur Alors
        S ← A ; A ← A^.gauche          // A est un candidat
     Sinon
        A ← A^.droit
     FinSi
  FinTQ
  Retourner S                          // dernier ancêtre « à gauche »
Fin

Le prédécesseur est symétrique (gauche ↔ droit)."""),
    "miroir": ("Miroir d'un arbre", """\
Procédure Miroir(A : ^Noeud)
Var T : ^Noeud
Début
  Si A ≠ NIL Alors
     Miroir(A^.gauche)
     Miroir(A^.droit)
     T ← A^.gauche ; A^.gauche ← A^.droit ; A^.droit ← T
  FinSi
Fin"""),
    "est_abr": ("Test : est-ce un ABR ?", """\
Un arbre binaire est un ABR  ⇔  son parcours INFIXÉ est
strictement croissant.

Fonction EstABR(A) : Booléen
Début
  Infixe(A) dans un tableau T[1..n]
  Pour i ← 2 à n Faire
     Si T[i-1] ≥ T[i] Alors Retourner Faux FinSi
  FinPour
  Retourner Vrai
Fin

(Attention : vérifier seulement « fils gauche < père < fils droit »
ne suffit PAS !)"""),
    "strict": ("Arbre localement complet (strict)", """\
Fonction EstStrict(A : ^Noeud) : Booléen
Début
  Si A = NIL Alors Retourner Vrai FinSi
  Si (A^.gauche = NIL) XOR (A^.droit = NIL) Alors
     Retourner Faux             // un nœud avec UN seul fils
  FinSi
  Retourner EstStrict(A^.gauche) ET EstStrict(A^.droit)
Fin

Chaque nœud a 0 ou 2 fils  ⇒  n = 2·f − 1  (f = nb de feuilles)."""),
    "parfait": ("Arbre parfait (tous les niveaux pleins)", """\
Fonction EstParfait(A : ^Noeud) : Booléen
Début
  h ← Hauteur(A)
  Retourner NbNoeuds(A) = 2^(h+1) − 1
Fin

Autrement dit : le niveau k contient exactement 2^k nœuds,
pour tout k de 0 à h."""),
    "complet": ("Arbre complet (presque complet / « tas »)", """\
Fonction EstComplet(A : ^Noeud) : Booléen
Var F : File ; P : ^Noeud ; videVu : Booléen
Début
  videVu ← Faux ; Enfiler(F, A)
  TantQue non FileVide(F) Faire
     P ← Défiler(F)
     Si P = NIL Alors
        videVu ← Vrai
     Sinon
        Si videVu Alors Retourner Faux FinSi
        Enfiler(F, P^.gauche) ; Enfiler(F, P^.droit)
     FinSi
  FinTQ
  Retourner Vrai
Fin

Tous les niveaux sont pleins sauf éventuellement le dernier,
rempli de gauche à droite."""),
    "degenere": ("Arbre dégénéré (filiforme)", """\
Fonction EstDégénéré(A : ^Noeud) : Booléen
Début
  Si A = NIL Alors Retourner Vrai FinSi
  Si (A^.gauche ≠ NIL) ET (A^.droit ≠ NIL) Alors
     Retourner Faux             // un nœud a deux fils
  FinSi
  Retourner EstDégénéré(A^.gauche) ET EstDégénéré(A^.droit)
Fin

Chaque nœud a au plus 1 fils : l'arbre est une liste chaînée.
Hauteur = n − 1 (le pire cas pour un ABR : recherche en O(n))."""),
    "equilibre": ("Arbre équilibré (AVL)", """\
Fonction EstÉquilibré(A : ^Noeud) : Booléen
Début
  Si A = NIL Alors Retourner Vrai FinSi
  Si |Hauteur(A^.gauche) − Hauteur(A^.droit)| > 1 Alors
     Retourner Faux
  FinSi
  Retourner EstÉquilibré(A^.gauche) ET EstÉquilibré(A^.droit)
Fin

Facteur d'équilibre de chaque nœud ∈ {−1, 0, +1}."""),
    "infos": ("Informations sur un nœud", """\
Niveau(x)      = nombre d'arêtes entre la racine et x (racine : 0)
Profondeur(x)  = Niveau(x)
Hauteur(x)     = hauteur du sous-arbre de racine x
Degré(x)       = nombre de fils de x (0, 1 ou 2)
Ancêtres(x)    = nœuds du chemin racine → père de x
Descendants(x) = tous les nœuds du sous-arbre de x, sauf x"""),
    "equilibrer": ("Équilibrer un ABR", """\
Fonction Construire(T[g..d]) : ^Noeud
Var m : Entier
Début
  Si g > d Alors Retourner NIL FinSi
  m ← (g + d) DIV 2                    // valeur médiane
  Allouer(P) ; P^.valeur ← T[m]
  P^.gauche ← Construire(T[g..m-1])
  P^.droit  ← Construire(T[m+1..d])
  Retourner P
Fin

On range les valeurs en ordre croissant (parcours infixé)
puis on prend toujours la valeur MÉDIANE comme racine."""),
}


PSEUDO_MOTS = ["Procédure", "Fonction", "Début", "Fin", "Si", "Alors", "Sinon", "FinSi",
               "TantQue", "FinTQ", "Faire", "Pour", "FinPour", "Retourner", "Var", "VAR",
               "ET", "OU", "XOR", "non", "MOD", "DIV", "NIL", "Vrai", "Faux", "Allouer",
               "Libérer", "Enfiler", "Défiler", "Écrire", "à"]
PY_MOTS = ["def", "class", "return", "if", "elif", "else", "while", "for", "in", "and", "or",
           "not", "is", "None", "True", "False", "lambda", "from", "import", "yield"]

# Versions Python des algorithmes (même clés que ALGOS)
ALGOS_PY = {
    "prefixe": """\
def prefixe(a):
    if a is not None:
        print(a.valeur)        # R : la racine d'abord
        prefixe(a.gauche)      # G : puis le sous-arbre gauche
        prefixe(a.droite)      # D : puis le sous-arbre droit

# Idée : on traite le nœud AVANT ses fils.""",
    "infixe": """\
def infixe(a):
    if a is not None:
        infixe(a.gauche)       # G
        print(a.valeur)        # R
        infixe(a.droite)       # D

# Sur un ABR : valeurs triées dans l'ordre croissant.""",
    "postfixe": """\
def postfixe(a):
    if a is not None:
        postfixe(a.gauche)     # G
        postfixe(a.droite)     # D
        print(a.valeur)        # R en dernier

# Idée : le nœud est traité APRÈS ses fils.""",
    "inverse": """\
def infixe_inverse(a):
    if a is not None:
        infixe_inverse(a.droite)   # D
        print(a.valeur)            # R
        infixe_inverse(a.gauche)   # G

# Sur un ABR : valeurs dans l'ordre décroissant.""",
    "largeur": """\
from collections import deque

def largeur(a):
    if a is None:
        return
    file = deque([a])
    while file:
        p = file.popleft()         # défiler
        print(p.valeur)
        if p.gauche is not None:
            file.append(p.gauche)  # enfiler
        if p.droite is not None:
            file.append(p.droite)

# Utilise une FILE (FIFO), pas la récursivité.""",
    "nb_noeuds": """\
def nb_noeuds(a):
    if a is None:
        return 0
    return 1 + nb_noeuds(a.gauche) + nb_noeuds(a.droite)""",
    "feuilles": """\
def nb_feuilles(a):
    if a is None:
        return 0
    if a.gauche is None and a.droite is None:
        return 1                   # c'est une feuille
    return nb_feuilles(a.gauche) + nb_feuilles(a.droite)""",
    "internes": """\
def nb_internes(a):
    if a is None or (a.gauche is None and a.droite is None):
        return 0                   # vide ou feuille
    return 1 + nb_internes(a.gauche) + nb_internes(a.droite)

# nb_noeuds = nb_feuilles + nb_internes""",
    "un_fils": """\
def nb_un_fils(a):
    if a is None:
        return 0
    c = 1 if (a.gauche is None) != (a.droite is None) else 0
    return c + nb_un_fils(a.gauche) + nb_un_fils(a.droite)""",
    "deux_fils": """\
def nb_deux_fils(a):
    if a is None:
        return 0
    c = 1 if a.gauche is not None and a.droite is not None else 0
    return c + nb_deux_fils(a.gauche) + nb_deux_fils(a.droite)

# Propriété : nb_feuilles = nb_deux_fils + 1""",
    "hauteur": """\
def hauteur(a):
    if a is None:
        return -1                  # convention : arbre vide = -1
    return 1 + max(hauteur(a.gauche), hauteur(a.droite))

# hauteur(feuille) = 0 (en arêtes).""",
    "largeur_niv": """\
from collections import deque

def largeur_par_niveau(a):
    file = deque([a]) if a else deque()
    niveau = 0
    while file:
        n = len(file)              # nœuds du niveau courant
        print("niveau", niveau, ":", n, "nœuds")
        for _ in range(n):
            p = file.popleft()
            if p.gauche: file.append(p.gauche)
            if p.droite: file.append(p.droite)
        niveau += 1""",
    "somme": """\
def somme(a):
    if a is None:
        return 0
    return a.valeur + somme(a.gauche) + somme(a.droite)

# moyenne = somme(a) / nb_noeuds(a)""",
    "min": """\
def minimum(a):
    # précondition : a n'est pas None
    m = a.valeur
    if a.gauche is not None:
        m = min(m, minimum(a.gauche))
    if a.droite is not None:
        m = min(m, minimum(a.droite))
    return m

# Arbre quelconque : on visite TOUS les nœuds, O(n).""",
    "max": """\
def maximum(a):
    # précondition : a n'est pas None
    m = a.valeur
    if a.gauche is not None:
        m = max(m, maximum(a.gauche))
    if a.droite is not None:
        m = max(m, maximum(a.droite))
    return m

# Arbre quelconque : on visite TOUS les nœuds, O(n).""",
    "occurrences": """\
def occurrences(a, x):
    if a is None:
        return 0
    c = 1 if a.valeur == x else 0
    return c + occurrences(a.gauche, x) + occurrences(a.droite, x)""",
    "premiers": """\
def est_premier(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True

def nombres_premiers(a):
    if a is None:
        return []
    ici = [a.valeur] if est_premier(a.valeur) else []
    return ici + nombres_premiers(a.gauche) + nombres_premiers(a.droite)""",
    "parite": """\
def nb_pairs(a):
    if a is None:
        return 0
    c = 1 if a.valeur % 2 == 0 else 0
    return c + nb_pairs(a.gauche) + nb_pairs(a.droite)

# impairs = nb_noeuds(a) - nb_pairs(a)""",
    "recherche": """\
def recherche(a, x):
    if a is None:
        return None
    if a.valeur == x:
        return a
    p = recherche(a.gauche, x)
    if p is not None:
        return p
    return recherche(a.droite, x)

# On explore les deux sous-arbres : O(n) au pire.""",
    "recherche_abr": """\
def recherche_abr(a, x):
    if a is None or a.valeur == x:
        return a
    if x < a.valeur:
        return recherche_abr(a.gauche, x)
    return recherche_abr(a.droite, x)

# O(h) : O(log n) si équilibré, O(n) si dégénéré.""",
    "min_abr": """\
def min_abr(a):
    while a.gauche is not None:    # on descend toujours à gauche
        a = a.gauche
    return a

# Le minimum est le nœud le plus à GAUCHE : O(h).""",
    "max_abr": """\
def max_abr(a):
    while a.droite is not None:    # on descend toujours à droite
        a = a.droite
    return a

# Le maximum est le nœud le plus à DROITE : O(h).""",
    "insertion": """\
def inserer(a, x):
    if a is None:
        return Noeud(x)            # la nouvelle valeur devient une FEUILLE
    if x < a.valeur:
        a.gauche = inserer(a.gauche, x)
    elif x > a.valeur:
        a.droite = inserer(a.droite, x)
    return a                       # x déjà présent : rien à faire

# racine = inserer(racine, 42)    -  complexité O(h)""",
    "suppression": """\
def supprimer(a, x):
    if a is None:
        return None                # x absent
    if x < a.valeur:
        a.gauche = supprimer(a.gauche, x)
    elif x > a.valeur:
        a.droite = supprimer(a.droite, x)
    else:                          # nœud à supprimer trouvé
        if a.gauche is None:       # 0 ou 1 fils (droit)
            return a.droite
        if a.droite is None:       # 1 fils (gauche)
            return a.gauche
        s = min_abr(a.droite)      # 2 fils : successeur infixé
        a.valeur = s.valeur
        a.droite = supprimer(a.droite, s.valeur)
    return a""",
    "successeur": """\
def successeur(racine, x):
    if x.droite is not None:
        return min_abr(x.droite)   # min du sous-arbre droit
    s, a = None, racine
    while a is not x:              # on descend depuis la racine
        if x.valeur < a.valeur:
            s, a = a, a.gauche     # a est un candidat
        else:
            a = a.droite
    return s                       # dernier ancêtre « à gauche »

# Le prédécesseur est symétrique (gauche <-> droite).""",
    "miroir": """\
def miroir(a):
    if a is not None:
        miroir(a.gauche)
        miroir(a.droite)
        a.gauche, a.droite = a.droite, a.gauche""",
    "est_abr": """\
def infixe_liste(a):
    if a is None:
        return []
    return infixe_liste(a.gauche) + [a.valeur] + infixe_liste(a.droite)

def est_abr(a):
    t = infixe_liste(a)
    return all(t[i - 1] < t[i] for i in range(1, len(t)))

# ABR  <=>  parcours infixé strictement croissant.""",
    "strict": """\
def est_strict(a):
    if a is None:
        return True
    if (a.gauche is None) != (a.droite is None):
        return False               # un nœud avec UN seul fils
    return est_strict(a.gauche) and est_strict(a.droite)

# Chaque nœud a 0 ou 2 fils  =>  n = 2*f - 1""",
    "parfait": """\
def est_parfait(a):
    h = hauteur(a)
    return nb_noeuds(a) == 2 ** (h + 1) - 1

# Le niveau k contient exactement 2**k nœuds.""",
    "complet": """\
from collections import deque

def est_complet(a):
    file = deque([a])
    vide_vu = False
    while file:
        p = file.popleft()
        if p is None:
            vide_vu = True
        else:
            if vide_vu:
                return False       # un nœud après un emplacement vide
            file.append(p.gauche)
            file.append(p.droite)
    return True""",
    "degenere": """\
def est_degenere(a):
    if a is None:
        return True
    if a.gauche is not None and a.droite is not None:
        return False               # un nœud a deux fils
    return est_degenere(a.gauche) and est_degenere(a.droite)

# Arbre filiforme : hauteur = n - 1.""",
    "equilibre": """\
def est_equilibre(a):
    if a is None:
        return True
    if abs(hauteur(a.gauche) - hauteur(a.droite)) > 1:
        return False
    return est_equilibre(a.gauche) and est_equilibre(a.droite)

# Facteur d'équilibre de chaque nœud dans {-1, 0, +1}.""",
    "infos": """\
def chemin(a, cible):
    if a is None:
        return None
    if a is cible:
        return [a]
    for f in (a.gauche, a.droite):
        c = chemin(f, cible)
        if c:
            return [a] + c
    return None

# ch = chemin(racine, x)
# niveau = len(ch) - 1          # profondeur
# ancêtres = ch[:-1]            # père = ch[-2]
# degré = (x.gauche is not None) + (x.droite is not None)""",
    "equilibrer": """\
def construire(t):
    # t : liste triée (parcours infixé de l'ABR)
    if not t:
        return None
    m = len(t) // 2                # valeur médiane = racine
    n = Noeud(t[m])
    n.gauche = construire(t[:m])
    n.droite = construire(t[m + 1:])
    return n

# racine = construire(infixe_liste(racine))""",
}


C_FOND = "#FBF8F0"
C_OR = "#C49A3A"
C_OR_CLAIR = "#E8D39A"
C_ENCRE = "#302719"


def _rgb(h):
    """Convertit une couleur hexadécimale #RRGGBB en triplet entier RGB."""
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def melange(c1, c2, u):
    """Mélange deux couleurs pour créer les nuances du dessin des nœuds.

    u=0 renvoie c1, u=1 renvoie c2 ; les valeurs intermédiaires sont
    interpolées canal par canal et renvoyées au format #rrggbb.
    """
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(a[i] + (b[i] - a[i]) * u))) for i in range(3))


C_MOTS = ["include", "typedef", "struct", "int", "void", "char", "return", "if", "else", "while",
          "for", "NULL", "sizeof", "malloc", "free", "printf", "true", "false"]

STRUCT_C = """\
#include <stdio.h>
#include <stdlib.h>

typedef struct Noeud {
    int valeur;
    struct Noeud *gauche, *droite;
} Noeud;"""

# Versions C des algorithmes (même clés que ALGOS)
ALGOS_C = {
    "prefixe": """\
void prefixe(Noeud *a) {
    if (a != NULL) {
        printf("%d ", a->valeur);   // R : la racine d'abord
        prefixe(a->gauche);         // G
        prefixe(a->droite);         // D
    }
}""",
    "infixe": """\
void infixe(Noeud *a) {
    if (a != NULL) {
        infixe(a->gauche);          // G
        printf("%d ", a->valeur);   // R
        infixe(a->droite);          // D
    }
}

// Sur un ABR : valeurs triées dans l'ordre croissant.""",
    "postfixe": """\
void postfixe(Noeud *a) {
    if (a != NULL) {
        postfixe(a->gauche);        // G
        postfixe(a->droite);        // D
        printf("%d ", a->valeur);   // R en dernier
    }
}""",
    "inverse": """\
void infixe_inverse(Noeud *a) {
    if (a != NULL) {
        infixe_inverse(a->droite);  // D
        printf("%d ", a->valeur);   // R
        infixe_inverse(a->gauche);  // G
    }
}

// Sur un ABR : valeurs dans l'ordre décroissant.""",
    "largeur": """\
// n = nombre de nœuds ; la file est un simple tableau
void largeur(Noeud *a, int n) {
    if (a == NULL) return;
    Noeud *file[n];
    int debut = 0, fin = 0;
    file[fin++] = a;                  // enfiler
    while (debut < fin) {
        Noeud *p = file[debut++];     // défiler
        printf("%d ", p->valeur);
        if (p->gauche) file[fin++] = p->gauche;
        if (p->droite) file[fin++] = p->droite;
    }
}""",
    "nb_noeuds": """\
int nb_noeuds(Noeud *a) {
    if (a == NULL) return 0;
    return 1 + nb_noeuds(a->gauche) + nb_noeuds(a->droite);
}""",
    "feuilles": """\
int nb_feuilles(Noeud *a) {
    if (a == NULL) return 0;
    if (a->gauche == NULL && a->droite == NULL)
        return 1;                     // c'est une feuille
    return nb_feuilles(a->gauche) + nb_feuilles(a->droite);
}""",
    "internes": """\
int nb_internes(Noeud *a) {
    if (a == NULL || (a->gauche == NULL && a->droite == NULL))
        return 0;                     // vide ou feuille
    return 1 + nb_internes(a->gauche) + nb_internes(a->droite);
}""",
    "un_fils": """\
int nb_un_fils(Noeud *a) {
    if (a == NULL) return 0;
    int c = ((a->gauche == NULL) != (a->droite == NULL)) ? 1 : 0;
    return c + nb_un_fils(a->gauche) + nb_un_fils(a->droite);
}""",
    "deux_fils": """\
int nb_deux_fils(Noeud *a) {
    if (a == NULL) return 0;
    int c = (a->gauche != NULL && a->droite != NULL) ? 1 : 0;
    return c + nb_deux_fils(a->gauche) + nb_deux_fils(a->droite);
}

// Propriété : nb_feuilles = nb_deux_fils + 1""",
    "hauteur": """\
int hauteur(Noeud *a) {
    if (a == NULL) return -1;         // convention : arbre vide = -1
    int hg = hauteur(a->gauche);
    int hd = hauteur(a->droite);
    return 1 + (hg > hd ? hg : hd);
}""",
    "largeur_niv": """\
void largeur_par_niveau(Noeud *a, int n) {
    if (a == NULL) return;
    Noeud *file[n];
    int debut = 0, fin = 0, niveau = 0;
    file[fin++] = a;
    while (debut < fin) {
        int k = fin - debut;          // nœuds du niveau courant
        printf("niveau %d : %d noeuds\\n", niveau, k);
        for (int i = 0; i < k; i++) {
            Noeud *p = file[debut++];
            if (p->gauche) file[fin++] = p->gauche;
            if (p->droite) file[fin++] = p->droite;
        }
        niveau++;
    }
}""",
    "somme": """\
int somme(Noeud *a) {
    if (a == NULL) return 0;
    return a->valeur + somme(a->gauche) + somme(a->droite);
}

// moyenne = (double) somme(a) / nb_noeuds(a)""",
    "min": """\
int minimum(Noeud *a) {
    // précondition : a != NULL
    int m = a->valeur;
    if (a->gauche) { int g = minimum(a->gauche); if (g < m) m = g; }
    if (a->droite) { int d = minimum(a->droite); if (d < m) m = d; }
    return m;
}

// Arbre quelconque : on visite TOUS les nœuds, O(n).""",
    "max": """\
int maximum(Noeud *a) {
    // précondition : a != NULL
    int m = a->valeur;
    if (a->gauche) { int g = maximum(a->gauche); if (g > m) m = g; }
    if (a->droite) { int d = maximum(a->droite); if (d > m) m = d; }
    return m;
}

// Arbre quelconque : on visite TOUS les nœuds, O(n).""",
    "occurrences": """\
int occurrences(Noeud *a, int x) {
    if (a == NULL) return 0;
    int c = (a->valeur == x) ? 1 : 0;
    return c + occurrences(a->gauche, x) + occurrences(a->droite, x);
}""",
    "premiers": """\
int est_premier(int n) {
    if (n < 2) return 0;
    for (int d = 2; d * d <= n; d++)
        if (n % d == 0) return 0;
    return 1;
}

int nb_premiers(Noeud *a) {
    if (a == NULL) return 0;
    int ici = est_premier(a->valeur) ? 1 : 0;
    return ici + nb_premiers(a->gauche) + nb_premiers(a->droite);
}""",
    "parite": """\
int nb_pairs(Noeud *a) {
    if (a == NULL) return 0;
    int c = (a->valeur % 2 == 0) ? 1 : 0;
    return c + nb_pairs(a->gauche) + nb_pairs(a->droite);
}

// impairs = nb_noeuds(a) - nb_pairs(a)""",
    "recherche": """\
Noeud *recherche(Noeud *a, int x) {
    if (a == NULL) return NULL;
    if (a->valeur == x) return a;
    Noeud *p = recherche(a->gauche, x);
    if (p != NULL) return p;
    return recherche(a->droite, x);
}

// On explore les deux sous-arbres : O(n) au pire.""",
    "recherche_abr": """\
Noeud *recherche_abr(Noeud *a, int x) {
    if (a == NULL || a->valeur == x) return a;
    if (x < a->valeur) return recherche_abr(a->gauche, x);
    return recherche_abr(a->droite, x);
}

// O(h) : O(log n) si équilibré, O(n) si dégénéré.""",
    "min_abr": """\
Noeud *min_abr(Noeud *a) {
    while (a->gauche != NULL)         // on descend toujours à gauche
        a = a->gauche;
    return a;
}""",
    "max_abr": """\
Noeud *max_abr(Noeud *a) {
    while (a->droite != NULL)         // on descend toujours à droite
        a = a->droite;
    return a;
}""",
    "insertion": """\
Noeud *inserer(Noeud *a, int x) {
    if (a == NULL) {                  // la nouvelle valeur devient une FEUILLE
        Noeud *p = malloc(sizeof(Noeud));
        p->valeur = x;
        p->gauche = p->droite = NULL;
        return p;
    }
    if (x < a->valeur)      a->gauche = inserer(a->gauche, x);
    else if (x > a->valeur) a->droite = inserer(a->droite, x);
    return a;                         // x déjà présent : rien à faire
}

// racine = inserer(racine, 42);   complexité O(h)""",
    "suppression": """\
Noeud *supprimer(Noeud *a, int x) {
    if (a == NULL) return NULL;       // x absent
    if (x < a->valeur)
        a->gauche = supprimer(a->gauche, x);
    else if (x > a->valeur)
        a->droite = supprimer(a->droite, x);
    else {                            // nœud à supprimer trouvé
        if (a->gauche == NULL) {      // 0 ou 1 fils (droit)
            Noeud *t = a->droite;
            free(a);
            return t;
        }
        if (a->droite == NULL) {      // 1 fils (gauche)
            Noeud *t = a->gauche;
            free(a);
            return t;
        }
        Noeud *s = min_abr(a->droite);  // 2 fils : successeur infixé
        a->valeur = s->valeur;
        a->droite = supprimer(a->droite, s->valeur);
    }
    return a;
}""",
    "successeur": """\
Noeud *successeur(Noeud *racine, Noeud *x) {
    if (x->droite != NULL)
        return min_abr(x->droite);    // min du sous-arbre droit
    Noeud *s = NULL, *a = racine;
    while (a != x) {                  // on descend depuis la racine
        if (x->valeur < a->valeur) { s = a; a = a->gauche; }  // a est candidat
        else                         a = a->droite;
    }
    return s;                         // dernier ancêtre « à gauche »
}

// Le prédécesseur est symétrique (gauche <-> droite).""",
    "miroir": """\
void miroir(Noeud *a) {
    if (a != NULL) {
        miroir(a->gauche);
        miroir(a->droite);
        Noeud *t = a->gauche;         // échange des deux fils
        a->gauche = a->droite;
        a->droite = t;
    }
}""",
    "est_abr": """\
// parcours infixé en mémorisant le nœud précédent
int est_abr(Noeud *a, Noeud **prec) {
    if (a == NULL) return 1;
    if (!est_abr(a->gauche, prec)) return 0;
    if (*prec != NULL && (*prec)->valeur >= a->valeur) return 0;
    *prec = a;
    return est_abr(a->droite, prec);
}

// appel :  Noeud *prec = NULL;  est_abr(racine, &prec);""",
    "strict": """\
int est_strict(Noeud *a) {
    if (a == NULL) return 1;
    if ((a->gauche == NULL) != (a->droite == NULL))
        return 0;                     // un nœud avec UN seul fils
    return est_strict(a->gauche) && est_strict(a->droite);
}""",
    "parfait": """\
int est_parfait(Noeud *a) {
    int h = hauteur(a);
    return nb_noeuds(a) == (1 << (h + 1)) - 1;   // 2^(h+1) - 1
}""",
    "complet": """\
int est_complet(Noeud *a, int n) {
    Noeud *file[2 * n + 2];           // la file contient aussi des NULL
    int debut = 0, fin = 0, vide_vu = 0;
    file[fin++] = a;
    while (debut < fin) {
        Noeud *p = file[debut++];
        if (p == NULL) {
            vide_vu = 1;
        } else {
            if (vide_vu) return 0;    // un nœud après un emplacement vide
            file[fin++] = p->gauche;
            file[fin++] = p->droite;
        }
    }
    return 1;
}""",
    "degenere": """\
int est_degenere(Noeud *a) {
    if (a == NULL) return 1;
    if (a->gauche != NULL && a->droite != NULL)
        return 0;                     // un nœud a deux fils
    return est_degenere(a->gauche) && est_degenere(a->droite);
}""",
    "equilibre": """\
#include <stdlib.h>   // abs

int est_equilibre(Noeud *a) {
    if (a == NULL) return 1;
    if (abs(hauteur(a->gauche) - hauteur(a->droite)) > 1)
        return 0;
    return est_equilibre(a->gauche) && est_equilibre(a->droite);
}""",
    "infos": """\
// remplit ch[] avec le chemin racine -> cible ; retourne sa longueur (0 si absent)
int chemin(Noeud *a, Noeud *cible, Noeud **ch, int prof) {
    if (a == NULL) return 0;
    ch[prof] = a;
    if (a == cible) return prof + 1;
    int l = chemin(a->gauche, cible, ch, prof + 1);
    if (l) return l;
    return chemin(a->droite, cible, ch, prof + 1);
}

// niveau = longueur - 1 ;  père = ch[longueur - 2]""",
    "equilibrer": """\
// t[g..d] : valeurs triées (parcours infixé de l'ABR)
Noeud *construire(int t[], int g, int d) {
    if (g > d) return NULL;
    int m = (g + d) / 2;              // valeur médiane = racine
    Noeud *p = malloc(sizeof(Noeud));
    p->valeur = t[m];
    p->gauche = construire(t, g, m - 1);
    p->droite = construire(t, m + 1, d);
    return p;
}""",
}

COURS = """\
VOCABULAIRE
-----------
Arbre binaire : chaque nœud a au plus 2 fils (gauche, droit).
Racine        : nœud sans père (niveau 0).
Feuille       : nœud sans fils.        Nœud interne : nœud avec ≥ 1 fils.
Niveau / profondeur d'un nœud : nb d'arêtes depuis la racine.
Hauteur d'un arbre : niveau maximal  (feuille seule = 0 ; arbre vide = −1).
Taille : nombre de nœuds n.   Degré d'un nœud : nombre de ses fils.

RELATIONS UTILES (arbre binaire à n nœuds, hauteur h)
-----------------------------------------------------
  h + 1  ≤  n  ≤  2^(h+1) − 1      soit      ⌊log2 n⌋ ≤ h ≤ n − 1
  niveau k : au plus 2^k nœuds
  f = d2 + 1    (f feuilles, d2 nœuds à deux fils)
  n = f + d1 + d2     (d1 : nœuds à un seul fils)

PARCOURS EN PROFONDEUR  (R = racine, G = sous-arbre gauche, D = sous-arbre droit)
  Préfixé  : R G D        Infixé : G R D        Postfixé : G D R
PARCOURS EN LARGEUR : niveau par niveau, de gauche à droite (file).

TYPES D'ARBRES
--------------
Localement complet (strict) : tout nœud a 0 ou 2 fils.
Parfait (plein)  : tous les niveaux sont complètement remplis (n = 2^(h+1) − 1).
Complet          : tous les niveaux pleins sauf le dernier, rempli de gauche à droite.
Dégénéré (peigne): tout nœud a au plus 1 fils (h = n − 1).
Équilibré (AVL)  : |h(gauche) − h(droit)| ≤ 1 pour TOUT nœud.

ARBRE BINAIRE DE RECHERCHE (ABR)
--------------------------------
Pour tout nœud x : valeurs du sous-arbre gauche < x < valeurs du sous-arbre droit.
  * Le parcours infixé donne les valeurs triées.
  * Min = nœud le plus à gauche ; Max = nœud le plus à droite.
  * Recherche / insertion / suppression : O(h).

STRUCTURE EN PYTHON
-------------------
class Noeud:
    def __init__(self, valeur):
        self.valeur = valeur
        self.gauche = None
        self.droite = None

def infixe(a):
    if a is not None:
        infixe(a.gauche)
        print(a.valeur)
        infixe(a.droite)

STRUCTURE EN C
--------------
typedef struct Noeud {
    int valeur;
    struct Noeud *gauche, *droite;
} Noeud;

void infixe(Noeud *a) {
    if (a != NULL) {
        infixe(a->gauche);
        printf("%d ", a->valeur);
        infixe(a->droite);
    }
}

COMMENT UTILISER L'APPLICATION
------------------------------
* Cliquez sur un nœud pour le sélectionner (clic droit = menu contextuel).
* Glissez-déposez un nœud pour le déplacer ; « Réinitialiser la disposition »
  remet l'arbre en place.
* En bas à gauche, choisissez d'afficher l'algorithme en pseudo-code, en Python ou en C.
* Onglet « Arbre » : construire à la main (ajouter fils gauche / droit au nœud
  sélectionné) ou insérer dans un ABR, générer, charger un exemple.
* Les autres onglets lancent des animations ; l'algorithme est affiché en bas à
  gauche, la trace des appels récursifs en bas à droite.
* « Pas à pas » + bouton ⏭ pour avancer étape par étape.
"""

EXEMPLES = {
    "ABR classique (9 nœuds)": ("liste", [8, 3, 10, 1, 6, 14, 4, 7, 13]),
    "Arbre binaire quelconque": ("tuple", (
        12,
        (5, (18, None, None), (7, (15, None, None), None)),
        (9, None, (3, (4, None, None), (11, None, None))))),
    "ABR parfait (15 nœuds)": ("liste", [8, 4, 12, 2, 6, 10, 14, 1, 3, 5, 7, 9, 11, 13, 15]),
    "ABR dégénéré (peigne)": ("liste", [1, 2, 3, 4, 5, 6]),
}

COULEURS = {
    "visit": "#7BD389", "skip": "#D0D0D0", "found": "#FFE45E",
    "bad": "#FF8A8A", "path": "#C8A2F2", "enter": "#FFE0B2",
}
C_ENTETE = "#352817"
C_NORMAL = "#A8D4FF"
C_FEUILLE = "#F4B6D2"
C_COURANT = "#FF9F1C"
RAYON = 20


# ----------------------------------------------------------------------
#  APPLICATION
# ----------------------------------------------------------------------

class Application(tk.Tk):
    """Fenêtre principale et contrôleur de TreeLab.

    L'état central est self.racine. Les opérations produisent des événements
    Ev ; le moteur les joue ensuite sur le canevas afin de séparer calcul et
    animation pédagogique.
    """

    def __init__(self):
        """Initialise l'état du programme, les variables Tkinter et les widgets."""
        super().__init__()
        self.title("TreeLab by Nadir BOUCHAMA — Arbres binaires (Algorithmique ISIL 2)")
        self.configure(bg="#F7F2E7")
        self.geometry("1400x880")
        self.minsize(1120, 720)

        # --- état de l'arbre
        self.racine = None
        self.vue_pointeurs = tk.BooleanVar(value=False)
        self.afficher_manquants = tk.BooleanVar(value=False)
        self.selection = None
        self.positions = {}
        self.emplacements_vides = []
        self.positions_vides_base = {}
        self.infos = {}
        self.base = {}          # positions calculées automatiquement
        self.decalages = {}     # décalages dus au glisser-déposer
        self.decalages_vides = {}  # déplacements des cases NULL dessinées
        self.drag = None
        self.drag_emplacement = None
        self.drag_emplacement_deplace = False
        self.drag_depart = (0, 0, 0, 0)
        self.logo_img = None
        self.zoom = 1.0
        self.historique = [None]
        self.historique_index = 0
        self._plein_ecran_window = None
        self._canvas_normal = None
        self._suspendre_historique = False

        # --- état de l'animation
        self.marques = {}
        self.courant = None
        self.events = []
        self.ev_i = 0
        self.appels_recursifs = []
        self.en_cours = False
        self.pause = False
        self.job = None
        self.on_finish = None
        self.titre_anim = ""
        self.sequence = []

        # --- variables Tk
        self.valeur_var = tk.StringVar()
        self.n_var = tk.StringVar(value="10")
        self.liste_var = tk.StringVar(value="50, 30, 70, 20, 40, 60, 80")
        self.exemple_var = tk.StringVar(value=list(EXEMPLES)[0])
        self.animer = tk.BooleanVar(value=True)
        self.pas_a_pas = tk.BooleanVar(value=False)
        self.details = tk.BooleanVar(value=False)
        self.colorier_feuilles = tk.BooleanVar(value=False)
        self.show_info = tk.BooleanVar(value=False)
        self.vitesse = tk.DoubleVar(value=5)
        self.quiz_nouvel_arbre = tk.BooleanVar(value=True)
        self.quiz_rep = tk.StringVar()
        self.quiz_idx = None
        self.quiz_repondu = False
        self.score = [0, 0]
        self.defi_niveau = tk.StringVar(value="Débutant")
        self.defi_reponse = tk.StringVar()
        self.defi_attendu = None
        self.defi_explication = ""
        self.defi_score = [0, 0]
        self.mode_pourquoi = tk.BooleanVar(value=False)
        self.construction_valeurs = []
        self.construction_index = 0
        self.dessin_manuel = tk.BooleanVar(value=False)
        self.dessin_cote = tk.StringVar(value="gauche")
        self.dessin_valeur = tk.StringVar(value="")
        self.na_var = tk.StringVar(value="A(B,C,D); B(E,F); C(G)")
        self.sim_na_actions = []
        self.sim_na_index = 0
        self.sim_na_nodes = {}
        self.sim_na_actif = False
        self.notation_var = tk.StringVar(value="A(B,C); B(E,T)")
        self.calcul_expression = tk.StringVar(value="3 5 + 4 * 2 -")
        self.calcul_format = tk.StringVar(value="Postfixe (polonaise inversée)")
        self.calcul_notation = tk.StringVar(value="Postfixe (polonaise inversée)")
        self.calcul_pile = tk.StringVar(value="Pile : []")
        self.qcm_n_var = tk.StringVar(value="9")
        self.qcm_type_var = tk.StringVar(value="ABR équilibré")
        self.qcm_reponse_var = tk.StringVar(value="")
        self.qcm_questions = []
        self.qcm_index = -1
        self.qcm_reponses = {}
        self.qcm_statuts = {}
        self.qcm_score = [0, 0]

        self.QUIZ = [
            ("Donnez le parcours PRÉFIXÉ (RGD) — valeurs séparées par des espaces :",
             lambda r: valeurs(r, "RGD"),
             lambda: self.parcours("RGD", "Parcours préfixé (RGD)", "prefixe")),
            ("Donnez le parcours INFIXÉ (GRD) — valeurs séparées par des espaces :",
             lambda r: valeurs(r, "GRD"),
             lambda: self.parcours("GRD", "Parcours infixé (GRD)", "infixe")),
            ("Donnez le parcours POSTFIXÉ (GDR) — valeurs séparées par des espaces :",
             lambda r: valeurs(r, "GDR"),
             lambda: self.parcours("GDR", "Parcours postfixé (GDR)", "postfixe")),
            ("Donnez le parcours en LARGEUR — valeurs séparées par des espaces :",
             lambda r: [x.valeur for lv in niveaux(r) for x in lv],
             lambda: self.parcours_largeur()),
            ("Quel est le NOMBRE DE NŒUDS de l'arbre ?", taille, lambda: self.op_nb_noeuds()),
            ("Quel est le NOMBRE DE FEUILLES de l'arbre ?", nb_feuilles, lambda: self.op_feuilles()),
            ("Quel est le NOMBRE DE NŒUDS INTERNES ?",
             lambda r: taille(r) - nb_feuilles(r), lambda: self.op_internes()),
            ("Quelle est la HAUTEUR de l'arbre (feuille = 0) ?", hauteur, lambda: self.op_hauteur()),
            ("Quelle est la SOMME des valeurs de l'arbre ?", somme, lambda: self.op_somme()),
            ("Quel est le MINIMUM des valeurs ?", minimum, lambda: self.op_min()),
            ("Quel est le MAXIMUM des valeurs ?", maximum, lambda: self.op_max()),
        ]

        self.construire_interface()
        self.charger_exemple()

    # ==================================================================
    #  INTERFACE
    # ==================================================================

    def construire_interface(self):
        """Crée le bandeau, les notebooks, le canevas et les panneaux de code."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background="#F7F2E7", foreground=C_ENCRE, font=("Arial", 10))
        style.configure("TFrame", background="#F7F2E7")
        style.configure("TLabel", background="#F7F2E7", foreground=C_ENCRE)
        style.configure("Titre.TLabel", background="#F7F2E7", foreground="#805B12",
                        font=("Arial", 11, "bold"))
        style.configure("TButton", padding=(9, 5), background="#E8D39A", foreground="#352817",
                        bordercolor="#C49A3A", focusthickness=2, focuscolor=C_OR)
        style.map("TButton", background=[("active", "#D9BC72"), ("pressed", "#C49A3A")],
                  foreground=[("pressed", "#FFFFFF")])
        style.configure("TNotebook", background="#F7F2E7", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(11, 7), background="#EAE2D1",
                         foreground="#5C5140")
        style.map("TNotebook.Tab", background=[("selected", "#C49A3A"), ("active", "#F0E2BD")],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("TLabelframe", background="#F7F2E7", bordercolor="#D8C89F")
        style.configure("TLabelframe.Label", background="#F7F2E7", foreground="#805B12",
                        font=("Arial", 10, "bold"))
        style.configure("TEntry", fieldbackground="#FFFEFA", foreground=C_ENCRE,
                        bordercolor="#D8C89F")
        style.configure("TCheckbutton", background="#F7F2E7", foreground=C_ENCRE)
        style.map("TCheckbutton", background=[("active", "#F7F2E7")])

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # ----- bandeau TreeLab
        entete = tk.Frame(self, bg=C_ENTETE)
        entete.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.logo_img = self.charger_logo()
        if self.logo_img is not None:
            tk.Label(entete, image=self.logo_img, bg=C_ENTETE).pack(side="left", padx=(8, 6), pady=4)
        else:
            tk.Label(entete, text="🌳", font=("Arial", 26), bg=C_ENTETE, fg="white").pack(
                side="left", padx=(12, 6), pady=4)
        bloc = tk.Frame(entete, bg=C_ENTETE)
        bloc.pack(side="left", padx=6)
        tk.Label(bloc, text="TreeLab", font=("Arial", 24, "bold"), bg=C_ENTETE,
                 fg="white").pack(anchor="w")
        tk.Label(bloc, text="by Nadir BOUCHAMA", font=("Arial", 11, "italic"), bg=C_ENTETE,
                 fg="#E8D39A").pack(anchor="w")
        tk.Button(entete, text="À propos", command=self.a_propos, bg="#E8D39A", fg="#352817",
                  activebackground="#D9BC72", relief="flat", padx=10, pady=3,
                  cursor="hand2").pack(side="right", padx=(0, 14))
        tk.Label(entete, text="Arbres binaires · Algorithmique ISIL 2", font=("Arial", 11),
                 bg=C_ENTETE, fg="#E8D39A").pack(side="right", padx=14)

        # ----- colonne gauche
        gauche = ttk.Frame(self, padding=6)
        gauche.grid(row=1, column=0, sticky="ns")
        self.nb_gauche = ttk.Notebook(gauche, width=390, height=500)
        self.nb_gauche.pack(fill="both", expand=True)
        self.onglet_arbre()
        self.onglet_construction()
        self.onglet_parcours()
        self.onglet_mesures()
        self.onglet_tests()
        self.onglet_abr()
        self.onglet_qcm()
        self.onglet_defis()
        self.onglet_avance()
        self.onglet_conversion_naire()
        self.onglet_notations()
        self.onglet_calculatrice()
        self.panneau_animation(gauche)

        # ----- partie droite
        droite = ttk.Frame(self)
        droite.grid(row=1, column=1, sticky="nsew")
        # PanedWindow classique : séparateur épais, facile à saisir et à déplacer.
        paned = tk.PanedWindow(droite, orient="vertical", sashwidth=9, sashrelief="raised",
                               sashcursor="sb_v_double_arrow", opaqueresize=True,
                               bg="#C49A3A", bd=0)
        paned.pack(fill="both", expand=True)

        haut = ttk.Frame(paned)
        paned.add(haut, stretch="always", minsize=160)
        barre = ttk.Frame(haut, padding=(6, 4))
        barre.pack(fill="x")
        self.lbl_seq = ttk.Label(barre, text="", font=("Arial", 13, "bold"),
                                 foreground="#0B5394", wraplength=900)
        self.lbl_seq.pack(anchor="w")
        outils = ttk.Frame(barre)
        outils.pack(anchor="e", pady=(2, 0))
        self.btn_annuler = ttk.Button(outils, text="↶ Annuler", command=self.annuler, state="disabled")
        self.btn_annuler.pack(side="left", padx=2)
        self.btn_retablir = ttk.Button(outils, text="↷ Rétablir", command=self.retablir, state="disabled")
        self.btn_retablir.pack(side="left", padx=2)
        ttk.Separator(outils, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(outils, text="Ouvrir…", command=self.ouvrir_arbre).pack(side="left", padx=2)
        ttk.Button(outils, text="Enregistrer…", command=self.sauvegarder_arbre).pack(side="left", padx=2)
        ttk.Separator(outils, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(outils, text="−", width=3, command=lambda: self.modifier_zoom(1 / 1.15)).pack(side="left", padx=1)
        ttk.Button(outils, text="100%", command=self.zoom_initial).pack(side="left", padx=1)
        ttk.Button(outils, text="⛶ Plein écran", command=self.ouvrir_plein_ecran).pack(side="left", padx=3)
        ttk.Button(outils, text="+", width=3, command=lambda: self.modifier_zoom(1.15)).pack(side="left", padx=1)
        ligne = ttk.Frame(barre)
        ligne.pack(fill="x", pady=(2, 0))
        self.lbl_sel = ttk.Label(ligne, text="Aucun nœud sélectionné (cliquez sur un nœud)")
        self.lbl_sel.pack(side="left")
        ttk.Checkbutton(ligne, text="Vue valeur / pointeurs", variable=self.vue_pointeurs,
                        command=self.dessiner).pack(side="left", padx=8)
        leg = ttk.Frame(ligne)
        leg.pack(side="right")
        for txt, col in (("en cours", C_COURANT), ("parcouru", COULEURS["enter"]),
                         ("traité", COULEURS["visit"]), ("ignoré", COULEURS["skip"]),
                         ("trouvé", COULEURS["found"]), ("erreur", COULEURS["bad"]),
                         ("chemin", COULEURS["path"]), ("feuille", C_FEUILLE)):
            tk.Label(leg, text=txt, bg=col, font=("Arial", 8), padx=4).pack(side="left", padx=1)

        cadre = ttk.Frame(haut)
        cadre.pack(fill="both", expand=True)
        cadre.rowconfigure(0, weight=1)
        cadre.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(cadre, bg=C_FOND, highlightthickness=1,
                                highlightbackground="#D8C89F")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        sbx = ttk.Scrollbar(cadre, orient="horizontal", command=self.canvas.xview)
        sby = ttk.Scrollbar(cadre, orient="vertical", command=self.canvas.yview)
        sbx.grid(row=1, column=0, sticky="ew")
        sby.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=sbx.set, yscrollcommand=sby.set)
        self.canvas.bind("<Button-1>", self.clic)
        self.canvas.bind("<B1-Motion>", self.deplacer)
        self.canvas.bind("<ButtonRelease-1>", self.relacher)
        self.canvas.bind("<Button-3>", self.menu_contextuel)
        self.canvas.bind("<ButtonPress-2>", self.commencer_pan)
        self.canvas.bind("<B2-Motion>", self.deplacer_pan)
        self.canvas.bind("<ButtonRelease-2>", self.fin_pan)
        self.canvas.bind("<Control-MouseWheel>", self.zoom_roulette)
        self.canvas.bind("<MouseWheel>", self.roulette_canvas)
        self.canvas.bind("<Configure>", lambda e: self.dessiner())

        bas = tk.PanedWindow(paned, orient="horizontal", sashwidth=9, sashrelief="raised",
                             sashcursor="sb_h_double_arrow", opaqueresize=True,
                             bg="#C49A3A", bd=0)
        paned.add(bas, stretch="never", minsize=120, height=300)

        cadre_algo = ttk.LabelFrame(bas, text="Algorithme")
        bas.add(cadre_algo, stretch="always", minsize=200)
        self.mode_code = tk.StringVar(value="pseudo")
        self.algo_courant = None
        barre_code = ttk.Frame(cadre_algo)
        barre_code.pack(fill="x")
        ttk.Label(barre_code, text="Afficher en :").pack(side="left", padx=(4, 2))
        ttk.Radiobutton(barre_code, text="Pseudo-code", value="pseudo",
                        variable=self.mode_code, command=self.afficher_algo).pack(side="left", padx=4)
        ttk.Radiobutton(barre_code, text="Python", value="python",
                        variable=self.mode_code, command=self.afficher_algo).pack(side="left", padx=4)
        ttk.Radiobutton(barre_code, text="C", value="c",
                        variable=self.mode_code, command=self.afficher_algo).pack(side="left", padx=4)
        self.txt_algo = self.creer_texte(cadre_algo)
        self.txt_algo.configure(bg="black", fg="#E8E8E8", insertbackground="white",
                                font=("Courier New", 11))
        self.txt_algo.tag_configure("titre", font=("Arial", 11, "bold"), foreground="#6CB6FF")
        self.txt_algo.tag_configure("kw", foreground="#C792EA", font=("Courier New", 11, "bold"))
        self.txt_algo.tag_configure("num", foreground="#F2B880")
        self.txt_algo.tag_configure("com", foreground="#7EC27E")

        self.res_notebook = ttk.Notebook(bas)
        bas.add(self.res_notebook, stretch="always", minsize=200)
        f_res = ttk.Frame(self.res_notebook)
        f_trace = ttk.Frame(self.res_notebook)
        f_cours = ttk.Frame(self.res_notebook)
        f_notations = ttk.Frame(self.res_notebook)
        self.res_notebook.add(f_res, text="Résultat")
        self.res_notebook.add(f_trace, text="Trace d'exécution")
        self.res_notebook.add(f_notations, text="Notations de l'arbre")
        self.res_notebook.add(f_cours, text="Cours")
        self.txt_notations_arbre = self.creer_texte(f_notations)
        self.txt_notations_arbre.configure(wrap="none", font=("Consolas", 10))
        sbh = ttk.Scrollbar(f_notations, orient="horizontal", command=self.txt_notations_arbre.xview)
        self.txt_notations_arbre.configure(xscrollcommand=sbh.set)
        sbh.pack(side="bottom", fill="x", before=self.txt_notations_arbre.master)
        self.tab_notations_arbre = f_notations
        f_code = ttk.Frame(self.res_notebook)
        self.res_notebook.add(f_code, text="Code de l'arbre")
        self.tab_code = f_code
        code_pane = ttk.PanedWindow(f_code, orient="horizontal")
        code_pane.pack(fill="both", expand=True)
        left, right, java = (ttk.LabelFrame(code_pane, text="Python — déclaration et construction"),
                             ttk.LabelFrame(code_pane, text="C — structure et déclaration"),
                             ttk.LabelFrame(code_pane, text="Java — déclaration et construction"))
        code_pane.add(left, weight=1); code_pane.add(right, weight=1); code_pane.add(java, weight=1)
        bar_py, bar_c, bar_java = ttk.Frame(left), ttk.Frame(right), ttk.Frame(java)
        bar_py.pack(fill="x", padx=4, pady=3); bar_c.pack(fill="x", padx=4, pady=3)
        bar_java.pack(fill="x", padx=4, pady=3)
        ttk.Label(bar_py, text="Code Python").pack(side="left")
        ttk.Button(bar_py, text="COPIER", width=9,
                   command=lambda: self.copier_code(self.txt_tree_py, "Python")).pack(side="right")
        ttk.Label(bar_c, text="Code C").pack(side="left")
        ttk.Button(bar_c, text="COPIER", width=9,
                   command=lambda: self.copier_code(self.txt_tree_c, "C")).pack(side="right")
        ttk.Label(bar_java, text="Code Java").pack(side="left")
        ttk.Button(bar_java, text="COPIER", width=9,
                   command=lambda: self.copier_code(self.txt_tree_java, "Java")).pack(side="right")
        self.txt_tree_py, self.txt_tree_c = self.creer_texte(left), self.creer_texte(right)
        self.txt_tree_java = self.creer_texte(java)
        for widget in (self.txt_tree_py, self.txt_tree_c, self.txt_tree_java):
            widget.configure(font=("Consolas", 10), bg="#15171C", fg="#E6EDF3", insertbackground="white")
        self.tab_res, self.tab_trace = f_res, f_trace
        self.txt_res = self.creer_texte(f_res)
        self.txt_res.tag_configure("titre", font=("Arial", 11, "bold"), foreground="#0B5394")
        self.txt_res.tag_configure("res", font=("Arial", 15, "bold"), foreground="#B45F06")
        self.txt_res.tag_configure("ok", foreground="#1E8E3E", font=("Courier New", 10, "bold"))
        self.txt_res.tag_configure("ko", foreground="#C5221F", font=("Courier New", 10, "bold"))
        self.txt_trace = self.creer_texte(f_trace)
        txt_cours = self.creer_texte(f_cours)
        txt_cours.config(state="normal")
        txt_cours.insert("1.0", COURS)
        txt_cours.config(state="disabled")

        self.afficher_resultat("Bienvenue dans TreeLab !", [
            "Cliquez sur un nœud pour le sélectionner (clic droit : menu).",
            "Choisissez une opération dans les onglets de gauche :",
            "  • Parcours : préfixé, infixé, postfixé, largeur",
            "  • Mesures : nœuds, feuilles, hauteur, somme, min, max...",
            "  • Tests : ABR ? parfait ? complet ? équilibré ?",
            "  • ABR : recherche, successeur, insertion, suppression",
            "  • Quiz : entraînez-vous !",
            "",
            "Astuce : cochez « Pas à pas » pour avancer étape par étape.",
            "Astuce : glissez-déposez un nœud pour le déplacer.",
        ])

    def creer_texte(self, parent):
        """Crée un champ texte défilant pour les cours, résultats, traces ou codes."""
        cadre = ttk.Frame(parent)
        cadre.pack(fill="both", expand=True)
        t = tk.Text(cadre, wrap="word", font=("Courier New", 10), height=8, width=40,
                    state="disabled", bg="#FFFEFA", fg=C_ENCRE,
                    highlightthickness=1, highlightbackground="#E5D8B8")
        sb = ttk.Scrollbar(cadre, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return t

    def grille_boutons(self, parent, liste, colonnes=2, row0=0):
        """Dispose une liste de boutons en grille et étire les colonnes."""
        for i, (txt, cmd) in enumerate(liste):
            b = ttk.Button(parent, text=txt, command=cmd)
            b.grid(row=row0 + i // colonnes, column=i % colonnes, sticky="ew", padx=2, pady=2)
        for c in range(colonnes):
            parent.columnconfigure(c, weight=1)

    def nouvel_onglet(self, titre):
        """Ajoute un onglet de commandes avec une colonne extensible."""
        f = ttk.Frame(self.nb_gauche, padding=6)
        self.nb_gauche.add(f, text=titre)
        f.columnconfigure(0, weight=1)
        return f

    # ----- onglet « Arbre »
    def onglet_arbre(self):
        """Construit les commandes de création, modification et chargement d'arbres."""
        f = self.nouvel_onglet("Arbre")
        ligne = ttk.Frame(f)
        ligne.grid(row=0, column=0, sticky="ew")
        ttk.Label(ligne, text="Valeur (entier) :", style="Titre.TLabel").pack(side="left")
        e = ttk.Entry(ligne, textvariable=self.valeur_var, width=8)
        e.pack(side="left", padx=6)
        e.bind("<Return>", lambda ev: self.inserer_abr())
        self.entry_valeur = e

        lf = ttk.LabelFrame(f, text="Arbre binaire quelconque (le nœud sélectionné est le père)", padding=4)
        lf.grid(row=1, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Créer la racine", self.creer_racine),
            ("Modifier la valeur", self.modifier_valeur),
            ("＋ Fils gauche", lambda: self.ajouter_fils("gauche")),
            ("＋ Fils droit", lambda: self.ajouter_fils("droite")),
            ("Supprimer le sous-arbre", self.supprimer_sous_arbre),
            ("Miroir (G ↔ D)", self.miroir),
        ])

        lf = ttk.LabelFrame(f, text="Arbre binaire de recherche", padding=4)
        lf.grid(row=2, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Insérer (ABR)", self.inserer_abr),
            ("Supprimer (ABR)", lambda: self.supprimer_abr()),
        ])

        lf = ttk.LabelFrame(f, text="Générer / charger", padding=4)
        lf.grid(row=3, column=0, sticky="ew", pady=4)
        l1 = ttk.Frame(lf)
        l1.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(l1, text="Nombre de nœuds (max. 99) :").pack(side="left")
        ttk.Entry(l1, textvariable=self.n_var, width=5).pack(side="left", padx=4)
        self.grille_boutons(lf, [
            ("ABR aléatoire", self.aleatoire_abr),
            ("Arbre quelconque aléatoire", self.aleatoire_quelconque),
        ], row0=1)

    def onglet_construction(self):
        """Crée l'atelier de construction séquentielle et de dessin manuel."""
        f = self.nouvel_onglet("Construction pas à pas")
        ttk.Label(f, text="Construis ton arbre en mémoire !", style="Titre.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(f, text=("Saisis jusqu’à 31 valeurs séparées par des virgules. "
                           "Elles seront placées niveau par niveau : la première est la racine, "
                           "puis les fils gauche et droit, de gauche à droite."),
                  wraplength=350, justify="left").grid(row=1, column=0, sticky="ew")
        self.construction_var = tk.StringVar(value="8, 3, 10, 1, 6, 9, 14")
        ttk.Entry(f, textvariable=self.construction_var).grid(row=2, column=0, sticky="ew", pady=5)
        self.grille_boutons(f, [("🌱 Démarrer", self.demarrer_construction)], row0=3)
        self.grille_boutons(f, [("⏭ Étape suivante", self.etape_construction)], row0=4)
        self.lbl_construction = ttk.Label(f, text="Prêt ? Démarre pour réserver le premier nœud.",
                                         wraplength=350, justify="left")
        self.lbl_construction.grid(row=5, column=0, sticky="ew", pady=8)
        ttk.Label(f, text="À observer : l’adresse mémoire, puis les pointeurs gauche et droit.",
                  wraplength=350).grid(row=6, column=0, sticky="ew")
        ttk.Separator(f).grid(row=7, column=0, sticky="ew", pady=8)
        ttk.Label(f, text="✏️ Dessin manuel", style="Titre.TLabel").grid(row=8, column=0, sticky="w")
        ttk.Checkbutton(f, text="Activer le dessin sur le canevas", variable=self.dessin_manuel,
                        command=self.activer_dessin_manuel).grid(
            row=9, column=0, sticky="w")
        manuel = ttk.Frame(f)
        manuel.grid(row=10, column=0, sticky="ew", pady=3)
        ttk.Label(manuel, text="Valeur :").pack(side="left")
        ttk.Entry(manuel, textvariable=self.dessin_valeur, width=7).pack(side="left", padx=4)
        ttk.Label(manuel, text="Côté :").pack(side="left", padx=(5, 2))
        ttk.Combobox(manuel, textvariable=self.dessin_cote, values=("gauche", "droite"),
                     state="readonly", width=8).pack(side="left")
        ttk.Label(f, text="Clique sur le canevas pour poser la racine. Ensuite, sélectionne un parent, "
                     "choisis le côté et clique à l’emplacement du nouveau fils.",
                  wraplength=350, justify="left").grid(row=11, column=0, sticky="ew")
        f.columnconfigure(0, weight=1)

    def demarrer_construction(self):
        """Valide la liste de valeurs et remet l'atelier pas à pas à zéro."""
        try:
            valeurs_saisies = [int(x.strip()) for x in self.construction_var.get().split(",") if x.strip()]
            if not valeurs_saisies or len(valeurs_saisies) > 31:
                raise ValueError("Entre 1 à 31 valeurs entières.")
        except ValueError as e:
            messagebox.showerror("Liste invalide", str(e) or "Utilise des entiers séparés par des virgules.")
            return
        self.annuler_job()
        self.en_cours = False
        self.construction_valeurs = valeurs_saisies
        self.construction_index = 0
        self.racine = None
        self.selection = None
        self.marques = {}
        self.decalages = {}
        self.decalages_vides = {}
        self.vue_pointeurs.set(True)
        self.reinitialiser_disposition()
        self.lbl_construction.config(text=f"Objectif : créer {len(valeurs_saisies)} nœud(s). Clique sur « Étape suivante ».")
        self._montrer_code_arbre()
        self.res_notebook.select(self.tab_code)

    def etape_construction(self):
        """Alloue un nœud, le lie au parent attendu et avance d'une étape."""
        i = self.construction_index
        if i >= len(self.construction_valeurs):
            self.lbl_construction.config(text="🎉 Arbre terminé ! Tous les nœuds sont alloués et reliés.")
            return
        valeur = self.construction_valeurs[i]
        n = Noeud(valeur)
        if i == 0:
            self.racine = n
            message = f"Étape {i + 1} : allouer {valeur} à l’adresse 0x{id(n):016X}. C’est la racine."
        else:
            # En parcours par niveaux, parent de l’indice i = (i - 1) // 2.
            parent = self._noeud_par_indice((i - 1) // 2)
            cote = "gauche" if i % 2 else "droite"
            setattr(parent, cote, n)
            message = (f"Étape {i + 1} : allouer {valeur}, puis relier le pointeur {cote} "
                       f"de {parent.valeur} vers 0x{id(n):016X}.")
        self.construction_index += 1
        self.selection = n
        self.reinitialiser_disposition()
        self._montrer_code_arbre()
        self._surligner_construction(i, racine=(i == 0))
        reste = len(self.construction_valeurs) - self.construction_index
        suffixe = "🎉 Construction terminée !" if reste == 0 else f"Il reste {reste} étape(s)."
        self.lbl_construction.config(text=message + "\n\n" + suffixe)
        self.res_notebook.select(self.tab_code)

    def _noeud_par_indice(self, index):
        """Retourne le nœud à l'indice donné dans l'arbre en parcours par niveaux."""
        file = [self.racine]
        for _ in range(index):
            n = file.pop(0)
            if n.gauche: file.append(n.gauche)
            if n.droite: file.append(n.droite)
        return file[0]

    def _surligner_construction(self, index, racine=False):
        """Surligne les lignes d'allocation Python, C et Java correspondant au pas."""
        for widget in (self.txt_tree_py, self.txt_tree_c, self.txt_tree_java):
            widget.tag_configure("etape_active", background="#665B22", foreground="#FFF3B0")
            widget.tag_remove("etape_active", "1.0", "end")
        lignes_py = self.txt_tree_py.get("1.0", "end-1c").splitlines()
        py_line = next((j for j, line in enumerate(lignes_py, 1) if line.startswith("racine = construire(")), None)
        if py_line:
            self.txt_tree_py.tag_add("etape_active", f"{py_line}.0", f"{py_line}.end")
            self.txt_tree_py.see(f"{py_line}.0")
        lignes_c = self.txt_tree_c.get("1.0", "end-1c").splitlines()
        motif = f"Noeud *n{index} = creer(" if racine else None
        if motif is None:
            ns = noeuds(self.racine, "RGD")
            # Le code C numérote en préordre ; trouver l’identifiant du nœud ajouté.
            n = self.selection
            cid = next((j for j, q in enumerate(ns) if q is n), None)
            motif = f"Noeud *n{cid} = creer("
        c_line = next((j for j, line in enumerate(lignes_c, 1) if motif in line), None)
        if c_line:
            self.txt_tree_c.tag_add("etape_active", f"{c_line}.0", f"{c_line}.end")
            self.txt_tree_c.see(f"{c_line}.0")
        java_lines = self.txt_tree_java.get("1.0", "end-1c").splitlines()
        java_motif = f"Noeud n{cid if not racine else 0} = new Noeud("
        java_line = next((j for j, line in enumerate(java_lines, 1) if java_motif in line), None)
        if java_line:
            self.txt_tree_java.tag_add("etape_active", f"{java_line}.0", f"{java_line}.end")
            self.txt_tree_java.see(f"{java_line}.0")

    def onglet_avance(self):
        """Crée l'accès aux ateliers rouge-noir et arbre d'expression."""
        f = self.nouvel_onglet("Ateliers")
        ttk.Label(f, text="Arbres rouge-noir", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(f, text="Un arbre rouge-noir est un ABR équilibré. La génération applique les rotations et recolorations standard.", wraplength=350).grid(row=1, column=0, sticky="w", pady=3)
        self.grille_boutons(f, [("Générer un rouge-noir", self.generer_rouge_noir)], row0=2)
        ttk.Separator(f).grid(row=3, column=0, sticky="ew", pady=8)
        ttk.Label(f, text="Expression → arbre", style="Titre.TLabel").grid(row=4, column=0, sticky="w")
        self.expression_var = tk.StringVar(value="(3 + 5) * x - 2")
        ttk.Entry(f, textvariable=self.expression_var).grid(row=5, column=0, sticky="ew", pady=3)
        self.grille_boutons(f, [("Construire l'arbre d'expression", self.construire_expression)], row0=6)
        f.columnconfigure(0, weight=1)

    def onglet_conversion_naire(self):
        """Crée l'interface de conversion d'un arbre n-aire en arbre binaire."""
        f = self.nouvel_onglet("N-aire → binaire")
        ttk.Label(f, text="Convertisseur d’arbre n-aire", style="Titre.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(f, text=("Décris chaque nœud puis ses enfants entre parenthèses. "
                           "Sépare les définitions par des points-virgules."),
                  wraplength=350, justify="left").grid(row=1, column=0, sticky="ew")
        ttk.Label(f, text="Exemple : A(B,C,D); B(E,F); C(G)",
                  font=("Consolas", 9, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Label(f, text="A est la racine ; B, C et D sont ses enfants. B a les enfants E et F.",
                  wraplength=350, justify="left").grid(row=3, column=0, sticky="ew")
        ttk.Entry(f, textvariable=self.na_var).grid(row=4, column=0, sticky="ew", pady=5)
        self.grille_boutons(f, [("🌿 Convertir immédiatement", self.convertir_na),
                                ("▶ Démarrer la simulation", self.demarrer_simulation_na)],
                           row0=5, colonnes=2)
        navigation = ttk.Frame(f)
        navigation.grid(row=6, column=0, sticky="ew", pady=3)
        self.btn_sim_na_precedent = ttk.Button(navigation, text="◀ Précédent",
                                               command=self.simulation_na_precedent, state="disabled")
        self.btn_sim_na_precedent.pack(side="left", expand=True, fill="x", padx=1)
        self.btn_sim_na_suivant = ttk.Button(navigation, text="Étape suivante ▶",
                                             command=self.simulation_na_suivante, state="disabled")
        self.btn_sim_na_suivant.pack(side="left", expand=True, fill="x", padx=1)
        self.btn_sim_na_terminer = ttk.Button(navigation, text="Tout terminer",
                                              command=self.simulation_na_terminer, state="disabled")
        self.btn_sim_na_terminer.pack(side="left", expand=True, fill="x", padx=1)
        self.lbl_sim_na = ttk.Label(f, text="Démarre la simulation pour suivre chaque lien.",
                                    wraplength=350, justify="left", font=("Arial", 9, "bold"))
        self.lbl_sim_na.grid(row=7, column=0, sticky="ew", pady=3)
        ttk.Label(f, text=("Règle : le premier enfant devient le fils gauche. "
                           "Chaque frère suivant devient le fils droit du frère précédent."),
                  wraplength=350, justify="left").grid(row=8, column=0, sticky="ew", pady=5)
        ttk.Label(f, text="Le résultat se dessine sur le canevas et les correspondances apparaissent dans Résultat.",
                  wraplength=350, justify="left").grid(row=9, column=0, sticky="ew")
        f.columnconfigure(0, weight=1)

    def onglet_notations(self):
        """Crée l'explorateur des représentations textuelles et graphiques d'arbres."""
        f = self.nouvel_onglet("Notations")
        ttk.Label(f, text="Explorer les notations d’arbres", style="Titre.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(f, text="Notation parent-enfants : A(B,C); B(E,T). "
                     "Le premier nœud défini est la racine.",
                  wraplength=350, justify="left").grid(row=1, column=0, sticky="ew")
        ttk.Entry(f, textvariable=self.notation_var).grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Button(f, text="🔄 Afficher les notations équivalentes",
                   command=self.afficher_notations).grid(row=3, column=0, sticky="ew")
        cadre_notations = ttk.Frame(f)
        cadre_notations.grid(row=4, column=0, sticky="nsew", pady=(5, 0))
        self.txt_notations = self.creer_texte(cadre_notations)
        self.txt_notations.configure(wrap="none", font=("Consolas", 10))
        f.rowconfigure(4, weight=1)
        f.columnconfigure(0, weight=1)
        self.afficher_notations()

    def afficher_notations(self):
        """Affiche les notations parent-enfants, imbriquée, indentée et binaire."""
        try:
            racine, enfants = parser_arbre_naire(self.notation_var.get())
        except ValueError as e:
            self.vider_texte(self.txt_notations)
            self.ecrire(self.txt_notations, f"Notation invalide\n\n{e}")
            return

        self.vider_texte(self.txt_notations)
        self.ecrire(self.txt_notations, texte_notations(self.notation_var.get(), racine, enfants))

    def maj_notations_arbre(self):
        """Met à jour le panneau des notations de l'arbre actuellement dessiné."""
        if not hasattr(self, "txt_notations_arbre"):
            return
        self.vider_texte(self.txt_notations_arbre)
        self.ecrire(self.txt_notations_arbre, notations_depuis_arbre_binaire(self.racine))
        self.txt_notations_arbre.see("1.0")

    def a_propos(self):
        """Affiche la fenêtre « À propos » de TreeLab."""
        fen = tk.Toplevel(self)
        fen.title("À propos de TreeLab")
        fen.configure(bg="#F7F2E7")
        fen.resizable(False, False)
        fen.transient(self)
        tk.Label(fen, text="TreeLab", font=("Arial", 22, "bold"), bg="#F7F2E7",
                 fg="#805B12").pack(padx=24, pady=(18, 0))
        tk.Label(fen, text="TreeLab by Nadir BOUCHAMA", font=("Arial", 11, "italic"),
                 bg="#F7F2E7", fg=C_ENCRE).pack(pady=(0, 10))
        tk.Label(fen, justify="left", wraplength=480, bg="#F7F2E7", fg=C_ENCRE,
                 font=("Arial", 10), text=(
            "TreeLab est une application de bureau pédagogique dédiée à l’apprentissage "
            "des arbres binaires et des arbres binaires de recherche. Elle associe une "
            "représentation graphique interactive à des animations pas à pas pour rendre "
            "visibles les opérations habituellement étudiées à travers du code ou des "
            "schémas statiques.\n\n"
            "L’application s’adresse notamment aux étudiants en algorithmique et en "
            "structures de données. Elle permet de construire un arbre, de lancer une "
            "opération et d’observer son effet sur les nœuds, les liens et les résultats "
            "affichés.")).pack(padx=24)
        tk.Label(fen, text="Novembre 2027", bg="#F7F2E7", fg="#5C5140",
                 font=("Arial", 10)).pack(pady=(10, 0))
        mail = tk.Label(fen, text="nadir.bouchama@gmail.com", bg="#F7F2E7", fg="#175CD3",
                        font=("Arial", 10, "underline"), cursor="hand2")
        mail.pack()
        mail.bind("<Button-1>", lambda _e: webbrowser.open("mailto:nadir.bouchama@gmail.com"))
        ttk.Button(fen, text="Fermer", command=fen.destroy).pack(pady=14)
        fen.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - fen.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - fen.winfo_height()) // 3
        fen.geometry(f"+{max(0, x)}+{max(0, y)}")
        fen.grab_set()

    def onglet_calculatrice(self):
        """Crée l'atelier de calcul préfixe/postfixe avec une pile animée."""
        f = self.nouvel_onglet("Calculatrice polonaise")
        ttk.Label(f, text="Calculer une expression", style="Titre.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(f, text="Saisis une formule numérique. Pour une notation polonaise, sépare chaque nombre et opérateur par un espace.",
                  wraplength=350, justify="left").grid(row=1, column=0, sticky="ew")
        ttk.Entry(f, textvariable=self.calcul_expression).grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Label(f, text="Format de la formule saisie :").grid(row=3, column=0, sticky="w")
        ttk.Combobox(f, textvariable=self.calcul_format,
                     values=("Infixe", "Préfixe (polonaise)", "Postfixe (polonaise inversée)"),
                     state="readonly").grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Label(f, text="Notation à simuler :").grid(row=5, column=0, sticky="w")
        ttk.Combobox(f, textvariable=self.calcul_notation,
                     values=("Préfixe (polonaise)", "Postfixe (polonaise inversée)"),
                     state="readonly").grid(row=6, column=0, sticky="ew", pady=3)
        ttk.Button(f, text="▶ Calculer et simuler", command=self.calculer_notation).grid(
            row=7, column=0, sticky="ew", pady=4)
        self.lbl_calcul_notations = ttk.Label(f, text="Préfixe : —\nPostfixe : —",
                                              wraplength=350, justify="left")
        self.lbl_calcul_notations.grid(row=8, column=0, sticky="ew", pady=5)
        ttk.Label(f, text="Pile de calcul · bas → sommet", style="Titre.TLabel").grid(
            row=9, column=0, sticky="w", pady=(8, 2))
        ttk.Label(f, textvariable=self.calcul_pile, wraplength=350, justify="left",
                  font=("Consolas", 10, "bold"), padding=7,
                  relief="groove").grid(row=10, column=0, sticky="ew")
        ttk.Label(f, text=("Préfixe : l’opérateur précède ses nombres et la pile se lit de droite à gauche. "
                           "Postfixe : l’opérateur suit ses nombres et la pile se lit de gauche à droite."),
                  wraplength=350, justify="left").grid(row=11, column=0, sticky="ew", pady=7)
        f.columnconfigure(0, weight=1)

    def calculer_notation(self):
        """Convertit l'expression, calcule sa valeur et anime chaque action de pile."""
        try:
            formule = self.calcul_expression.get().strip()
            format_entree = self.calcul_format.get()
            if format_entree == "Infixe":
                arbre = arbre_expression(formule)
            else:
                operateurs = {"+", "-", "*", "/", "^"}
                tokens_entree = [t for t in re.split(r"[\s,]+", formule) if t]
                if not tokens_entree:
                    raise ValueError("Saisissez une formule polonaise.")
                for token in tokens_entree:
                    if token not in operateurs and not re.fullmatch(r"-?\d+(?:\.\d+)?", token):
                        raise ValueError(f"Symbole invalide : {token}. Utilisez des nombres et + - * / ^.")
                ordre_prefixe = format_entree.startswith("Préfixe")
                parcours_tokens = list(reversed(tokens_entree)) if ordre_prefixe else tokens_entree
                pile_noeuds = []
                for token in parcours_tokens:
                    if token not in operateurs:
                        pile_noeuds.append(Noeud(token))
                        continue
                    if len(pile_noeuds) < 2:
                        raise ValueError(f"Il manque un opérande pour l’opérateur {token}.")
                    if ordre_prefixe:
                        gauche, droite = pile_noeuds.pop(), pile_noeuds.pop()
                    else:
                        droite, gauche = pile_noeuds.pop(), pile_noeuds.pop()
                    n = Noeud(token)
                    n.gauche, n.droite = gauche, droite
                    pile_noeuds.append(n)
                if len(pile_noeuds) != 1:
                    raise ValueError("La formule polonaise est incomplète ou contient trop d’opérandes.")
                arbre = pile_noeuds[0]
            noeuds_prefixes = noeuds(arbre, "RGD")
            noeuds_postfixes = noeuds(arbre, "GDR")
            if any(str(n.valeur) not in ("+", "-", "*", "/", "^") and
                   not re.fullmatch(r"-?\d+(?:\.\d+)?", str(n.valeur)) for n in noeuds(arbre)):
                raise ValueError("La calculatrice attend des nombres, sans variables.")
            prefixe = [str(n.valeur) for n in noeuds_prefixes]
            postfixe = [str(n.valeur) for n in noeuds_postfixes]
            est_prefixe = self.calcul_notation.get().startswith("Préfixe")
            if est_prefixe:
                tokens = list(reversed(prefixe))
                cibles = list(reversed(noeuds_prefixes))
            else:
                tokens, cibles = postfixe, noeuds_postfixes

            pile = []
            evenements = []
            operateurs = {"+", "-", "*", "/", "^"}
            def afficher_nombre(v):
                if isinstance(v, float):
                    return f"{v:.10g}"
                return str(v)

            for i, (token, cible) in enumerate(zip(tokens, cibles), 1):
                if token not in operateurs:
                    valeur = float(token) if "." in token else int(token)
                    pile.append(valeur)
                    action = f"Lire {token} : empiler {token}."
                else:
                    if len(pile) < 2:
                        raise ValueError(f"Pile insuffisante pour l’opérateur {token}.")
                    if est_prefixe:
                        gauche, droite = pile.pop(), pile.pop()
                    else:
                        droite, gauche = pile.pop(), pile.pop()
                    if token == "+": resultat = gauche + droite
                    elif token == "-": resultat = gauche - droite
                    elif token == "*": resultat = gauche * droite
                    elif token == "/":
                        if droite == 0:
                            raise ValueError("Division par zéro : le calcul est impossible.")
                        resultat = gauche / droite
                    else: resultat = gauche ** droite
                    if isinstance(resultat, complex) or (isinstance(resultat, float) and not math.isfinite(resultat)):
                        raise ValueError(f"Le résultat de {gauche} ^ {droite} n’est pas un nombre réel fini.")
                    pile.append(resultat)
                    action = (f"Lire {token} : dépiler {afficher_nombre(gauche)} et "
                              f"{afficher_nombre(droite)}, puis empiler {afficher_nombre(resultat)}.")
                etat = "[" + ", ".join(afficher_nombre(v) for v in pile) + "]"
                evenements.append(Ev(cible, "visit",
                                    f"Étape {i}/{len(tokens)} · {action} Pile (bas → sommet) : {etat}"))
            if len(pile) != 1:
                raise ValueError("L’expression n’a pas produit un résultat unique.")
            resultat_final = pile[0]
            resultat_affiche = afficher_nombre(resultat_final)
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            messagebox.showerror("Calcul impossible", str(e))
            return

        self.preparer()
        self.racine = arbre
        self.selection = None
        self._rn_actif = False
        self.reinitialiser_disposition()
        self._montrer_code_arbre()
        self.lbl_calcul_notations.config(
            text=f"Préfixe : {' '.join(prefixe)}\nPostfixe : {' '.join(postfixe)}")
        self.calcul_pile.set("Prêt : la pile est vide.")

        def fin():
            self.calcul_pile.set(f"Résultat final : {resultat_affiche}")
            self.afficher_resultat("Calcul de l’expression", [
                f"Expression : {self.calcul_expression.get()}",
                f"Préfixe : {' '.join(prefixe)}",
                f"Postfixe : {' '.join(postfixe)}",
                "La pile doit contenir un seul résultat après le dernier opérateur."],
                resultat_affiche)

        self.lancer("Calculatrice polonaise · " + ("préfixe" if est_prefixe else "postfixe"),
                    evenements, fin)

    def _montrer_code_arbre(self):
        if not hasattr(self, "txt_tree_py"): return
        self.vider_texte(self.txt_tree_py); self.vider_texte(self.txt_tree_c)
        self.vider_texte(self.txt_tree_java)
        self.ecrire(self.txt_tree_py, code_structure_python(self.racine))
        self.ecrire(self.txt_tree_c, code_structure_c(self.racine))
        self.ecrire(self.txt_tree_java, code_structure_java(self.racine))
        self.res_notebook.select(self.tab_code)

    def copier_code(self, widget, langage):
        code = widget.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update()
        self.lbl_seq.config(text=f"Code {langage} copié dans le presse-papiers.")

    def generer_rouge_noir(self):
        vals = [int(x) for x in re.findall(r"-?\d+", self.liste_var.get())]
        if not vals: vals = [random.randint(1, 99) for _ in range(9)]
        # Insertion rouge-noir CLRS : rotations et recolorations préservent les invariants.
        class RNode:
            def __init__(self, v): self.valeur=v; self.gauche=self.droite=self.parent=None; self.couleur_rn="R"
        nil = RNode(0); nil.couleur_rn="N"; nil.gauche=nil.droite=nil
        root=nil
        def left(x):
            nonlocal root
            y=x.droite; x.droite=y.gauche
            if y.gauche is not nil: y.gauche.parent=x
            y.parent=x.parent
            if x.parent is None: root=y
            elif x is x.parent.gauche: x.parent.gauche=y
            else: x.parent.droite=y
            y.gauche=x; x.parent=y
        def right(x):
            nonlocal root
            y=x.gauche; x.gauche=y.droite
            if y.droite is not nil: y.droite.parent=x
            y.parent=x.parent
            if x.parent is None: root=y
            elif x is x.parent.droite: x.parent.droite=y
            else: x.parent.gauche=y
            y.droite=x; x.parent=y
        for v in vals:
            z=RNode(v); z.gauche=z.droite=nil; y=None; x=root
            while x is not nil:
                y=x; x=x.gauche if v<x.valeur else x.droite
            z.parent=y
            if y is None: root=z
            elif v<y.valeur: y.gauche=z
            else: y.droite=z
            while z.parent is not None and z.parent.couleur_rn=="R":
                p=z.parent; g=p.parent
                if p is g.gauche:
                    u=g.droite
                    if u.couleur_rn=="R": p.couleur_rn=u.couleur_rn="N"; g.couleur_rn="R"; z=g
                    else:
                        if z is p.droite: z=p; left(z); p=z.parent; g=p.parent
                        p.couleur_rn="N"; g.couleur_rn="R"; right(g)
                else:
                    u=g.gauche
                    if u.couleur_rn=="R": p.couleur_rn=u.couleur_rn="N"; g.couleur_rn="R"; z=g
                    else:
                        if z is p.gauche: z=p; right(z); p=z.parent; g=p.parent
                        p.couleur_rn="N"; g.couleur_rn="R"; left(g)
            root.couleur_rn="N"
        def clone(n):
            if n is nil:return None
            q=Noeud(n.valeur); q.couleur_rn=n.couleur_rn; q.gauche=clone(n.gauche); q.droite=clone(n.droite); return q
        self.racine=clone(root); self._rn_actif=True; self.selection=None; self.reinitialiser_disposition(); self.dessiner(); self._montrer_code_arbre()
        self.afficher_resultat("Arbre rouge-noir construit", [f"Valeurs insérées : {vals}", "La racine est noire ; chaque chemin possède le même nombre de nœuds noirs.", "Les insertions ont appliqué les rotations et recolorations standard."])

    def construire_expression(self):
        # Une animation précédente ne doit pas retarder ni repeindre le nouvel arbre.
        self.annuler_job()
        self.en_cours = False
        self.pause = False
        try: self.racine=arbre_expression(self.expression_var.get())
        except ValueError as e: messagebox.showerror("Expression invalide", str(e)); return
        self.selection=None; self.reinitialiser_disposition(); self.dessiner(); self._montrer_code_arbre()
        self.afficher_resultat("Arbre d'expression", ["Les opérateurs sont les nœuds internes.", "Le parcours postfixé donne la notation polonaise inverse.", f"Postfixée : {' '.join(valeurs(self.racine, 'GDR'))}"])

    def demarrer_simulation_na(self):
        """Valide l’arbre n-aire et prépare la conversion lien par lien."""
        try:
            racine_nom, enfants = parser_arbre_naire(self.na_var.get())
        except ValueError as erreur:
            messagebox.showerror("Simulation impossible", str(erreur))
            return

        ordre = []
        def visiter(nom):
            ordre.append(nom)
            for enfant in enfants[nom]:
                visiter(enfant)
        visiter(racine_nom)

        actions = []
        for parent in ordre:
            fils = enfants[parent]
            for i, enfant in enumerate(fils):
                if i == 0:
                    proprietaire, cote = parent, "gauche"
                    explication = f"{enfant} devient le fils gauche de {parent}."
                else:
                    proprietaire, cote = fils[i - 1], "droite"
                    explication = f"{enfant} devient le frère droit de {fils[i - 1]} (fils de {parent})."
                actions.append((proprietaire, cote, enfant, explication))

        self.preparer()
        self._rn_actif = False
        self.sim_na_actions = actions
        self.sim_na_index = 0
        self.sim_na_nodes = {racine_nom: Noeud(racine_nom)}
        self.sim_na_racine_nom = racine_nom
        self.sim_na_actif = True
        self.racine = self.sim_na_nodes[racine_nom]
        self.selection = self.racine
        self.decalages = {}
        self.decalages_vides = {}
        self.marques = {self.racine: "found"}
        self.dessiner()
        self._montrer_code_arbre()
        self._actualiser_simulation_na()

    def _actualiser_simulation_na(self, explication=None):
        total = len(self.sim_na_actions)
        if explication is None:
            explication = f"Racine {self.sim_na_racine_nom} créée. Le premier fils ira à gauche ; les suivants seront reliés comme frères à droite."
        self.lbl_sim_na.config(text=f"Étape {self.sim_na_index}/{total} — {explication}")
        self.btn_sim_na_precedent.config(
            state="normal" if self.sim_na_actif and self.sim_na_index > 0 else "disabled")
        self.btn_sim_na_suivant.config(
            state="normal" if self.sim_na_actif and self.sim_na_index < total else "disabled")
        self.btn_sim_na_terminer.config(
            state="normal" if self.sim_na_actif and self.sim_na_index < total else "disabled")
        if self.sim_na_index == total:
            lignes = [f"La racine est {self.sim_na_racine_nom}.",
                      "Tous les enfants sont reliés : fils gauche pour le premier, frères à droite."]
            self.afficher_resultat("Simulation n-aire → binaire terminée", lignes)
        else:
            self.afficher_resultat("Simulation n-aire → binaire", [
                f"Progression : {self.sim_na_index}/{total} lien(s).", explication,
                "Utilise Précédent ou Étape suivante pour parcourir la conversion."])

    def simulation_na_suivante(self):
        if not self.sim_na_actif or self.sim_na_index >= len(self.sim_na_actions):
            return
        proprietaire, cote, enfant_nom, explication = self.sim_na_actions[self.sim_na_index]
        enfant = Noeud(enfant_nom)
        self.sim_na_nodes[enfant_nom] = enfant
        setattr(self.sim_na_nodes[proprietaire], cote, enfant)
        self.sim_na_index += 1
        self.selection = enfant
        self.marques = {enfant: "found"}
        self.dessiner()
        self._montrer_code_arbre()
        self._actualiser_simulation_na(explication)

    def simulation_na_precedent(self):
        if not self.sim_na_actif or self.sim_na_index <= 0:
            return
        proprietaire, cote, enfant_nom, _ = self.sim_na_actions[self.sim_na_index - 1]
        setattr(self.sim_na_nodes[proprietaire], cote, None)
        self.sim_na_nodes.pop(enfant_nom, None)
        self.sim_na_index -= 1
        if self.sim_na_index:
            enfant_nom = self.sim_na_actions[self.sim_na_index - 1][2]
            self.selection = self.sim_na_nodes[enfant_nom]
            self.marques = {self.selection: "found"}
            explication = self.sim_na_actions[self.sim_na_index - 1][3]
        else:
            self.selection = self.sim_na_nodes[self.sim_na_racine_nom]
            self.marques = {self.selection: "found"}
            explication = None
        self.dessiner()
        self._montrer_code_arbre()
        self._actualiser_simulation_na(explication)

    def simulation_na_terminer(self):
        while self.sim_na_actif and self.sim_na_index < len(self.sim_na_actions):
            self.simulation_na_suivante()

    def convertir_na(self):
        """Convertit l'arbre n-aire en binaire par fils gauche et frère droit."""
        try:
            root, parents = parser_arbre_naire(self.na_var.get())

            vus = set()
            actifs = set()
            correspondances = []
            def binaire(nom):
                """Encode un nœud et relie son premier fils puis sa chaîne de frères."""
                if nom in actifs:
                    raise ValueError(f"Cycle détecté à partir du nœud {nom}.")
                if nom in vus:
                    raise ValueError(f"Le nœud {nom} est partagé par plusieurs parents.")
                vus.add(nom)
                actifs.add(nom)
                n = Noeud(nom)
                enfants = parents[nom]
                if enfants:
                    n.gauche = binaire(enfants[0])
                    frere = n.gauche
                    correspondances.append(f"{nom} : fils gauche → {enfants[0]}.")
                    for enfant in enfants[1:]:
                        frere.droite = binaire(enfant)
                        correspondances.append(f"{enfant} : frère droit de {frere.valeur}.")
                        frere = frere.droite
                else:
                    correspondances.append(f"{nom} : aucun enfant → pointeur gauche = NULL.")
                actifs.remove(nom)
                return n
            racine_binaire = binaire(root)
            if len(vus) != len(parents):
                orphelins = sorted(set(parents) - vus)
                raise ValueError(f"Nœud(s) inaccessible(s) depuis la racine {root} : {orphelins}.")
        except ValueError as e:
            messagebox.showerror("Conversion impossible", str(e))
            return
        self.sim_na_actif = False
        if hasattr(self, "lbl_sim_na"):
            self.btn_sim_na_precedent.config(state="disabled")
            self.btn_sim_na_suivant.config(state="disabled")
            self.btn_sim_na_terminer.config(state="disabled")
            self.lbl_sim_na.config(text="Conversion directe terminée. Relance la simulation pour revoir les étapes.")
        self.preparer()
        self._rn_actif = False
        self.racine = racine_binaire
        self.selection = None
        self.reinitialiser_disposition()
        self._montrer_code_arbre()
        self.afficher_resultat("Conversion n-aire → binaire",
                               [f"Racine : {root}", "Règle : premier enfant à gauche, frères à droite."]
                               + correspondances)
        self.res_notebook.select(self.tab_res)

    # ----- onglet « Parcours »
    def onglet_parcours(self):
        f = self.nouvel_onglet("Parcours")
        ttk.Label(f, text="R = Racine   G = sous-arbre Gauche   D = sous-arbre Droit",
                  foreground="#555").grid(row=0, column=0, sticky="w", pady=(0, 6))
        lf = ttk.LabelFrame(f, text="En profondeur (récursifs)", padding=4)
        lf.grid(row=1, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Préfixé  (R G D)", lambda: self.parcours("RGD", "Parcours préfixé (RGD)", "prefixe")),
            ("Infixé  (G R D)", lambda: self.parcours("GRD", "Parcours infixé (GRD)", "infixe")),
            ("Postfixé  (G D R)", lambda: self.parcours("GDR", "Parcours postfixé (GDR)", "postfixe")),
            ("Infixé inversé  (D R G)", lambda: self.parcours("DRG", "Parcours infixé inversé (DRG)", "inverse")),
        ])
        lf = ttk.LabelFrame(f, text="En largeur (avec une file)", padding=4)
        lf.grid(row=2, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [("Parcours en largeur", self.parcours_largeur)], colonnes=1)
        lf = ttk.LabelFrame(f, text="Comparer", padding=4)
        lf.grid(row=3, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [("Afficher les 5 parcours (résumé)", self.tous_parcours)], colonnes=1)
        ttk.Label(f, justify="left", foreground="#444", wraplength=360, text=(
            "Moyen mnémotechnique : la position de R dit tout.\n"
            "• R au début → PRÉfixé\n• R au milieu → INfixé\n• R à la fin → POSTfixé\n\n"
            "Cochez « Détailler sous-arbres vides » pour voir chaque appel sur NIL.")
        ).grid(row=4, column=0, sticky="w", pady=8)

    # ----- onglet « Mesures »
    def onglet_mesures(self):
        f = self.nouvel_onglet("Mesures")
        lf = ttk.LabelFrame(f, text="Comptages", padding=4)
        lf.grid(row=0, column=0, sticky="ew", pady=3)
        self.grille_boutons(lf, [
            ("Nombre de nœuds", self.op_nb_noeuds),
            ("Nombre de feuilles", self.op_feuilles),
            ("Nœuds internes", self.op_internes),
            ("Hauteur", self.op_hauteur),
            ("Nœuds à 1 fils", self.op_un_fils),
            ("Nœuds à 2 fils", self.op_deux_fils),
            ("Largeur (par niveau)", self.op_largeur),
            ("Pairs / impairs", self.op_parite),
            ("Nombre de valeurs paires", self.op_nb_pairs),
            ("Nombre de nombres premiers", self.op_nb_premiers),
        ])
        lf = ttk.LabelFrame(f, text="Valeurs", padding=4)
        lf.grid(row=1, column=0, sticky="ew", pady=3)
        self.grille_boutons(lf, [
            ("Somme", self.op_somme),
            ("Moyenne", self.op_moyenne),
            ("Minimum", self.op_min),
            ("Maximum", self.op_max),
            ("Occurrences de x", self.op_occurrences),
            ("Rechercher x", self.op_recherche),
            ("Lister les valeurs paires", self.op_paires),
            ("Lister les nombres premiers", self.op_premiers),
            ("Lister les multiples de x", self.op_multiples),
        ])
        ttk.Label(f, text="(x = valeur saisie dans l'onglet « Arbre »)", foreground="#666").grid(
            row=2, column=0, sticky="w")
        lf = ttk.LabelFrame(f, text="Nœud sélectionné", padding=4)
        lf.grid(row=3, column=0, sticky="ew", pady=3)
        self.grille_boutons(lf, [("ℹ Infos + chemin depuis la racine", self.infos_noeud)], colonnes=1)
        lf = ttk.LabelFrame(f, text="Vue d'ensemble", padding=4)
        lf.grid(row=4, column=0, sticky="ew", pady=3)
        self.grille_boutons(lf, [("Diagnostic complet de l'arbre", self.diagnostic)], colonnes=1)

    # ----- onglet « Tests »
    def onglet_tests(self):
        f = self.nouvel_onglet("Tests")
        ttk.Label(f, text="L'arbre est-il … ?", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        lf = ttk.LabelFrame(f, text="Propriétés de forme", padding=4)
        lf.grid(row=1, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Localement complet (0 ou 2 fils)", self.test_strict),
            ("Parfait (niveaux pleins)", self.test_parfait),
            ("Complet (tas)", self.test_complet),
            ("Dégénéré (filiforme)", self.test_degenere),
            ("Équilibré (AVL)", self.test_equilibre),
            ("ABR", self.test_abr),
        ])
        ttk.Label(f, justify="left", foreground="#444", wraplength=360, text=(
            "• Localement complet : chaque nœud a 0 ou 2 fils.\n"
            "• Parfait : tous les niveaux sont pleins.\n"
            "• Complet : pleins sauf le dernier, rempli à gauche.\n"
            "• Dégénéré : chaque nœud a au plus 1 fils.\n"
            "• Équilibré : |h(G) − h(D)| ≤ 1 en chaque nœud.\n"
            "• ABR : parcours infixé strictement croissant.")
        ).grid(row=2, column=0, sticky="w", pady=8)
        self.grille_boutons(ttk.Frame(f), [])
        b = ttk.Button(f, text="Diagnostic complet de l'arbre", command=self.diagnostic)
        b.grid(row=3, column=0, sticky="ew")
        ttk.Button(f, text="Vérifier les invariants ABR / rouge-noir",
                   command=self.verifier_invariants).grid(row=4, column=0, sticky="ew", pady=(5, 0))

    # ----- onglet « ABR »
    def onglet_abr(self):
        f = self.nouvel_onglet("ABR")
        ttk.Label(f, text="Opérations sur un arbre binaire de recherche",
                  style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        lf = ttk.LabelFrame(f, text="Valeur x (champ de l'onglet « Arbre »)", padding=4)
        lf.grid(row=1, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Rechercher x", self.chercher_abr),
            ("Insérer x", self.inserer_abr),
            ("Supprimer x", lambda: self.supprimer_abr()),
        ], colonnes=3)
        ttk.Button(lf, text="Insertion guidée · pas à pas", command=self.insertion_guidee).grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=2, pady=3)
        lf = ttk.LabelFrame(f, text="Extrêmes", padding=4)
        lf.grid(row=2, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Minimum (⬅ à gauche)", lambda: self.extreme_abr("min")),
            ("Maximum (➡ à droite)", lambda: self.extreme_abr("max")),
        ])
        lf = ttk.LabelFrame(f, text="Nœud sélectionné", padding=4)
        lf.grid(row=3, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Successeur infixé", lambda: self.voisin_abr("succ")),
            ("Prédécesseur infixé", lambda: self.voisin_abr("pred")),
        ])
        lf = ttk.LabelFrame(f, text="Structure", padding=4)
        lf.grid(row=4, column=0, sticky="ew", pady=4)
        self.grille_boutons(lf, [
            ("Est-ce un ABR ?", self.test_abr),
            ("Équilibrer l'ABR", self.equilibrer),
        ])
        ttk.Label(f, justify="left", foreground="#444", wraplength=360, text=(
            "Essayez : insérez 1, 2, 3, 4, 5 dans l'ordre → arbre dégénéré (hauteur 4).\n"
            "Puis « Équilibrer l'ABR » → hauteur 2.\n"
            "Comparez le nombre de comparaisons d'une recherche.")
        ).grid(row=5, column=0, sticky="w", pady=8)

    # ----- onglet « Quiz »
    def onglet_quiz(self):
        f = self.nouvel_onglet("Quiz")
        ttk.Label(f, text="Entraînez-vous !", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        self.lbl_question = ttk.Label(f, text="Cliquez sur « Nouvelle question ».",
                                      wraplength=360, justify="left", font=("Arial", 11))
        self.lbl_question.grid(row=1, column=0, sticky="w", pady=8)
        e = ttk.Entry(f, textvariable=self.quiz_rep, font=("Arial", 12))
        e.grid(row=2, column=0, sticky="ew", pady=4)
        e.bind("<Return>", lambda ev: self.quiz_verifier())
        self.grille_boutons(ttk.Frame(f), [])
        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, sticky="ew", pady=4)
        self.grille_boutons(bf, [
            ("Nouvelle question", self.quiz_nouvelle),
            ("Vérifier", self.quiz_verifier),
            ("Voir la correction animée", self.quiz_correction),
        ], colonnes=3)
        ttk.Checkbutton(f, text="Nouvel arbre aléatoire à chaque question",
                        variable=self.quiz_nouvel_arbre).grid(row=4, column=0, sticky="w")
        self.lbl_feedback = ttk.Label(f, text="", wraplength=360, justify="left",
                                      font=("Arial", 11, "bold"))
        self.lbl_feedback.grid(row=5, column=0, sticky="w", pady=8)
        self.lbl_score = ttk.Label(f, text="Score : 0 / 0", font=("Arial", 11))
        self.lbl_score.grid(row=6, column=0, sticky="w")

    def onglet_qcm(self):
        """Crée le QCM de vingt questions lié à un arbre généré par configuration."""
        f = self.nouvel_onglet("QCM")
        ttk.Label(f, text="QCM sur les arbres", style="Titre.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        config = ttk.Frame(f)
        config.grid(row=1, column=0, sticky="ew")
        ttk.Label(config, text="Nœuds (1–31) :").grid(row=0, column=0, sticky="w")
        ttk.Entry(config, textvariable=self.qcm_n_var, width=5).grid(row=0, column=1, padx=4)
        ttk.Label(config, text="Type :").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(config, textvariable=self.qcm_type_var,
                     values=("ABR équilibré", "ABR aléatoire", "Arbre complet",
                             "Arbre quelconque", "Dégénéré"),
                     state="readonly", width=20).grid(row=1, column=1, sticky="ew", padx=4)
        config.columnconfigure(1, weight=1)
        ttk.Button(f, text="🌳 Générer l’arbre et les 20 questions",
                   command=self.generer_qcm).grid(row=2, column=0, sticky="ew", pady=5)
        self.lbl_qcm_progression = ttk.Label(f, text="Configure l’arbre puis démarre le QCM.",
                                             font=("Arial", 10, "bold"))
        self.lbl_qcm_progression.grid(row=3, column=0, sticky="w", pady=(4, 2))
        self.lbl_qcm_question = ttk.Label(f, text="", wraplength=350, justify="left",
                                          font=("Arial", 11, "bold"))
        self.lbl_qcm_question.grid(row=4, column=0, sticky="ew", pady=4)
        choix = ttk.LabelFrame(f, text="Choisis une réponse", padding=4)
        choix.grid(row=5, column=0, sticky="ew")
        self.qcm_radios = []
        for i in range(4):
            rb = tk.Radiobutton(choix, text="", variable=self.qcm_reponse_var,
                                value="", wraplength=330, anchor="w", justify="left",
                                bg="#F7F2E7", fg=C_ENCRE, activebackground="#F7F2E7",
                                selectcolor="#FFFEFA", highlightthickness=0)
            rb.grid(row=i, column=0, sticky="w", pady=1)
            self.qcm_radios.append(rb)
        ttk.Button(f, text="Vérifier la réponse", command=self.verifier_qcm).grid(
            row=6, column=0, sticky="ew", pady=(5, 2))
        nav = ttk.Frame(f)
        nav.grid(row=7, column=0, sticky="ew")
        ttk.Button(nav, text="← Précédente", command=self.qcm_precedente).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(nav, text="Suivante →", command=self.qcm_suivante).pack(
            side="left", expand=True, fill="x", padx=(2, 0))
        self.lbl_qcm_retour = ttk.Label(f, text="", wraplength=350, justify="left",
                                        font=("Arial", 10, "bold"))
        self.lbl_qcm_retour.grid(row=8, column=0, sticky="ew", pady=5)
        self.lbl_qcm_score = ttk.Label(f, text="Score : 0 / 0")
        self.lbl_qcm_score.grid(row=9, column=0, sticky="w")
        f.columnconfigure(0, weight=1)

    def generer_qcm(self):
        """Génère une structure répondant au réglage puis prépare vingt QCM."""
        try:
            n = int(self.qcm_n_var.get())
            if not 1 <= n <= 31:
                raise ValueError("Choisis un nombre entre 1 et 31.")
        except ValueError as e:
            messagebox.showerror("Configuration invalide", str(e) or "Le nombre de nœuds doit être un entier.")
            return
        valeurs_qcm = random.sample(range(1, 100), n)
        type_qcm = self.qcm_type_var.get()
        if type_qcm == "ABR équilibré":
            racine = construire_equilibre(sorted(valeurs_qcm))
        elif type_qcm == "ABR aléatoire":
            racine = None
            for valeur in random.sample(valeurs_qcm, len(valeurs_qcm)):
                racine = self._inserer_dans(racine, valeur)
        elif type_qcm == "Arbre complet":
            ns = [Noeud(v) for v in valeurs_qcm]
            for i, noeud in enumerate(ns):
                gi, di = 2 * i + 1, 2 * i + 2
                if gi < n: noeud.gauche = ns[gi]
                if di < n: noeud.droite = ns[di]
            racine = ns[0]
        elif type_qcm == "Dégénéré":
            racine = Noeud(valeurs_qcm[0])
            courant = racine
            for valeur in valeurs_qcm[1:]:
                courant.droite = Noeud(valeur)
                courant = courant.droite
        else:
            racine = Noeud(valeurs_qcm[0])
            places = [(racine, "gauche"), (racine, "droite")]
            for valeur in valeurs_qcm[1:]:
                i = random.randrange(len(places))
                parent, cote = places.pop(i)
                enfant = Noeud(valeur)
                setattr(parent, cote, enfant)
                places.extend(((enfant, "gauche"), (enfant, "droite")))

        self.preparer()
        self.racine = racine
        self.selection = None
        self._rn_actif = False
        self.vue_pointeurs.set(False)
        self.reinitialiser_disposition()
        self._montrer_code_arbre()
        self._creer_questions_qcm()
        self.qcm_index = 0
        self.qcm_reponses = {}
        self.qcm_statuts = {}
        self.qcm_score = [0, 0]
        self.lbl_qcm_score.config(text="Score : 0 / 0")
        self.lbl_qcm_retour.config(text="")
        self.afficher_question_qcm()

    def _inserer_dans(self, racine, valeur):
        """Insère récursivement une valeur dans une racine ABR locale au QCM."""
        if racine is None:
            return Noeud(valeur)
        cote = "gauche" if valeur < racine.valeur else "droite"
        setattr(racine, cote, self._inserer_dans(getattr(racine, cote), valeur))
        return racine

    def _creer_questions_qcm(self):
        """Construit les vingt questions et leurs distracteurs pour l'arbre actif."""
        r = self.racine
        tous = noeuds(r)
        seqs = {"préfixé": valeurs(r, "RGD"), "infixé": valeurs(r, "GRD"),
                "postfixé": valeurs(r, "GDR"),
                "largeur": [n.valeur for niveau in niveaux(r) for n in niveau]}
        questions = []

        def ajouter(question, bonne, autres, booleen=False):
            bonne = str(bonne)
            choix = []
            for valeur in autres:
                valeur = str(valeur)
                if valeur != bonne and valeur not in choix:
                    choix.append(valeur)
            if booleen:
                choix = [v for v in ("Oui", "Non") if v != bonne]
            else:
                try:
                    nombre = float(bonne)
                    delta = 1
                    while len(choix) < 3:
                        candidat = str(int(nombre + delta)) if nombre.is_integer() else str(nombre + delta)
                        if candidat != bonne and candidat not in choix:
                            choix.append(candidat)
                        delta += 1
                except (ValueError, OverflowError):
                    pass
            while len(choix) < 3:
                choix.append(f"Réponse {len(choix) + 1}")
            options = [bonne] + choix[:3]
            random.shuffle(options)
            questions.append({"question": question, "bonne": bonne, "options": options})

        ajouter("Quelle est la valeur de la racine ?", r.valeur,
                [n.valeur for n in tous if n is not r])
        ajouter("Combien l’arbre contient-il de nœuds ?", taille(r),
                [nb_feuilles(r), hauteur(r), len(tous) + 1])
        ajouter("Quelle est la hauteur de l’arbre ? (feuille seule = 0)", hauteur(r),
                [taille(r), nb_feuilles(r), hauteur(r) + 1])
        ajouter("Combien l’arbre a-t-il de feuilles ?", nb_feuilles(r),
                [taille(r), nb_fils(r), nb_feuilles(r) + 1])
        internes = sum(1 for n in tous if nb_fils(n) > 0)
        ajouter("Combien y a-t-il de nœuds internes ?", internes,
                [nb_feuilles(r), taille(r), internes + 1])
        un_fils = sum(1 for n in tous if nb_fils(n) == 1)
        ajouter("Combien de nœuds ont exactement un fils ?", un_fils,
                [nb_feuilles(r), taille(r), un_fils + 1])
        deux_fils = sum(1 for n in tous if nb_fils(n) == 2)
        ajouter("Combien de nœuds ont deux fils ?", deux_fils,
                [nb_feuilles(r), internes, deux_fils + 1])
        for nom, ordre in (("préfixé (R-G-D)", "préfixé"), ("infixé (G-R-D)", "infixé"),
                           ("postfixé (G-D-R)", "postfixé"), ("en largeur", "largeur")):
            autres = [" ".join(map(str, vals)) for cle, vals in seqs.items() if cle != ordre]
            ajouter(f"Quel est le parcours {nom} ?", " ".join(map(str, seqs[ordre])), autres)
        ajouter("Quelle est la plus petite valeur ?", minimum(r), [maximum(r), r.valeur, minimum(r) - 1])
        ajouter("Quelle est la plus grande valeur ?", maximum(r), [minimum(r), r.valeur, maximum(r) + 1])
        ajouter("Quelle est la somme des valeurs ?", somme(r), [taille(r), minimum(r), somme(r) + 1])
        ajouter("Cet arbre est-il un ABR ?", "Oui" if est_abr(r) else "Non", [], booleen=True)
        ajouter("Cet arbre est-il parfait ?", "Oui" if est_parfait(r) else "Non", [], booleen=True)
        ajouter("Cet arbre est-il complet ?", "Oui" if est_presque_complet(r) else "Non", [], booleen=True)
        ajouter("Cet arbre est-il dégénéré ?", "Oui" if est_degenere(r) else "Non", [], booleen=True)
        ajouter("Cet arbre est-il équilibré (condition AVL) ?", "Oui" if est_equilibre(r) else "Non", [], booleen=True)

        cible = random.choice(tous)
        pere = parent_de(r, cible)
        def nom_noeud(noeud):
            return "NULL" if noeud is None else str(noeud.valeur)
        def structure(noeud):
            parent = parent_de(r, noeud)
            return f"père={nom_noeud(parent)} ; gauche={nom_noeud(noeud.gauche)} ; droite={nom_noeud(noeud.droite)}"
        distracteurs = [structure(n) for n in tous if n is not cible]
        distracteurs += ["père=NULL ; gauche=NULL ; droite=NULL",
                         f"père={nom_noeud(cible.gauche)} ; gauche={nom_noeud(pere)} ; droite=NULL"]
        ajouter(f"Pour le nœud {cible.valeur}, quels sont son père et ses deux fils ?",
                structure(cible), distracteurs)
        self.qcm_questions = questions

    def afficher_question_qcm(self):
        """Affiche la question courante, les choix, la progression et son statut."""
        if self.qcm_index >= len(self.qcm_questions):
            self.lbl_qcm_progression.config(text=f"QCM terminé · {self.qcm_score[0]} / 20")
            self.lbl_qcm_question.config(text="🎉 Bravo, tu as répondu aux vingt questions !")
            self.lbl_qcm_retour.config(text=f"Score final : {self.qcm_score[0]} / 20")
            for radio in self.qcm_radios:
                radio.config(text="", state="disabled")
            return
        q = self.qcm_questions[self.qcm_index]
        self.lbl_qcm_progression.config(text=f"Question {self.qcm_index + 1} / 20 · Score : {self.qcm_score[0]} / {self.qcm_score[1]}")
        self.lbl_qcm_question.config(text=q["question"])
        self.qcm_reponse_var.set(self.qcm_reponses.get(self.qcm_index, ""))
        est_verifiee = self.qcm_index in self.qcm_statuts
        for i, radio in enumerate(self.qcm_radios):
            if i < len(q["options"]):
                option = q["options"][i]
                radio.config(text=option, value=option, state="disabled" if est_verifiee else "normal")
            else:
                radio.config(text="", value="", state="disabled")
        if est_verifiee:
            correct = self.qcm_statuts[self.qcm_index]
            self.lbl_qcm_retour.config(text=("✅ Bonne réponse !" if correct else
                                             f"❌ Réponse attendue : {q['bonne']}"),
                                       foreground="#1E8E3E" if correct else "#B42318")
        else:
            self.lbl_qcm_retour.config(text="")

    def verifier_qcm(self):
        """Corrige la réponse choisie et compte le résultat une seule fois."""
        if not self.qcm_questions or self.qcm_index < 0 or self.qcm_index >= len(self.qcm_questions):
            return
        if self.qcm_index in self.qcm_statuts:
            self.afficher_question_qcm()
            return
        reponse = self.qcm_reponse_var.get()
        if not reponse:
            self.lbl_qcm_retour.config(text="Choisis une réponse avant de vérifier.", foreground="#B45F06")
            return
        q = self.qcm_questions[self.qcm_index]
        correct = reponse == q["bonne"]
        self.qcm_reponses[self.qcm_index] = reponse
        self.qcm_statuts[self.qcm_index] = correct
        self.qcm_score[1] += 1
        self.qcm_score[0] += int(correct)
        self.lbl_qcm_score.config(text=f"Réponses vérifiées : {self.qcm_score[1]} / 20")
        self.afficher_question_qcm()

    def qcm_precedente(self):
        """Revient à la question précédente sans modifier les réponses corrigées."""
        if self.qcm_questions and self.qcm_index > 0:
            self.qcm_index -= 1
            self.afficher_question_qcm()

    def qcm_suivante(self):
        """Avance seulement après correction de la question courante."""
        if not self.qcm_questions or self.qcm_index >= len(self.qcm_questions):
            return
        if self.qcm_index not in self.qcm_statuts:
            self.lbl_qcm_retour.config(text="Vérifie d’abord ta réponse.", foreground="#B45F06")
            return
        self.qcm_index += 1
        self.afficher_question_qcm()

    def onglet_defis(self):
        f = self.nouvel_onglet("Défis & Pourquoi")
        ttk.Label(f, text="Défis gradués", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
        ligne = ttk.Frame(f)
        ligne.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(ligne, text="Niveau :").pack(side="left")
        ttk.Combobox(ligne, textvariable=self.defi_niveau,
                     values=("Débutant", "Intermédiaire", "Expert"),
                     state="readonly", width=15).pack(side="left", padx=5)
        ttk.Button(f, text="🎲 Nouveau défi", command=self.nouveau_defi).grid(
            row=2, column=0, sticky="ew", pady=3)
        self.lbl_defi = ttk.Label(f, text="Choisis un niveau puis lance un défi.",
                                  wraplength=350, justify="left", font=("Arial", 11))
        self.lbl_defi.grid(row=3, column=0, sticky="ew", pady=7)
        ttk.Entry(f, textvariable=self.defi_reponse).grid(row=4, column=0, sticky="ew", pady=3)
        bf = ttk.Frame(f)
        bf.grid(row=5, column=0, sticky="ew")
        ttk.Button(bf, text="Vérifier", command=self.verifier_defi).pack(side="left", expand=True, fill="x")
        ttk.Button(bf, text="Indice", command=self.indice_defi).pack(side="left", expand=True, fill="x", padx=(4, 0))
        self.lbl_defi_retour = ttk.Label(f, text="", wraplength=350, justify="left",
                                         font=("Arial", 10, "bold"))
        self.lbl_defi_retour.grid(row=6, column=0, sticky="ew", pady=6)
        self.lbl_defi_score = ttk.Label(f, text="Score des défis : 0 / 0")
        self.lbl_defi_score.grid(row=7, column=0, sticky="w")
        ttk.Separator(f).grid(row=8, column=0, sticky="ew", pady=8)
        ttk.Label(f, text="Mode « Pourquoi ? »", style="Titre.TLabel").grid(row=9, column=0, sticky="w")
        ttk.Checkbutton(f, text="Expliquer les clics et les étapes animées",
                        variable=self.mode_pourquoi,
                        command=lambda: self.maj_pourquoi(self.selection)).grid(
                            row=10, column=0, sticky="w")
        self.lbl_pourquoi = ttk.Label(f, text="Active le mode puis clique sur un nœud pour comprendre ses liens.",
                                      wraplength=350, justify="left")
        self.lbl_pourquoi.grid(row=11, column=0, sticky="ew", pady=5)
        f.columnconfigure(0, weight=1)

    def nouveau_defi(self):
        """Génère une question adaptée au niveau choisi et à l'arbre courant."""
        if not self.exiger_arbre():
            return
        niveau = self.defi_niveau.get()
        if niveau == "Débutant":
            ordre = random.choice(("RGD", "GRD", "GDR"))
            nom = {"RGD": "préfixé", "GRD": "infixé", "GDR": "postfixé"}[ordre]
            self.defi_attendu = [str(v) for v in valeurs(self.racine, ordre)]
            self.defi_explication = f"Parcours {nom} : { {'RGD':'racine, gauche, droite','GRD':'gauche, racine, droite','GDR':'gauche, droite, racine'}[ordre] }."
            prompt = f"Débutant · Donne le parcours {nom} (RGD/GRD/GDR), dans l’ordre."
        elif niveau == "Intermédiaire":
            mesure = random.choice(("hauteur", "feuilles"))
            if mesure == "hauteur":
                self.defi_attendu = [str(hauteur(self.racine))]
                self.defi_explication = "La hauteur compte les arêtes du plus long chemin racine-feuille ; une feuille seule a une hauteur de 0."
                prompt = "Intermédiaire · Quelle est la hauteur de l’arbre ? (feuille seule = 0)"
            else:
                self.defi_attendu = [str(nb_feuilles(self.racine))]
                self.defi_explication = "Une feuille est un nœud sans fils. Compte les nœuds qui n’ont ni fils gauche ni fils droit."
                prompt = "Intermédiaire · Combien l’arbre contient-il de feuilles ?"
        else:
            un_fils = sum(1 for n in noeuds(self.racine) if nb_fils(n) == 1)
            self.defi_attendu = [str(un_fils)]
            self.defi_explication = "Un nœud à un seul fils a exactement un pointeur non NULL parmi gauche et droite."
            prompt = "Expert · Combien de nœuds ont exactement un seul fils ?"
        self.defi_reponse.set("")
        self.lbl_defi.config(text=prompt)
        self.lbl_defi_retour.config(text="")

    def verifier_defi(self):
        """Compare la réponse au résultat attendu et met à jour le score."""
        if self.defi_attendu is None:
            self.lbl_defi_retour.config(text="Lance d’abord un défi.", foreground="#B45F06")
            return
        saisi = re.findall(r"-?\d+(?:\.\d+)?|[A-Za-z_]\w*|[()+\-*/^]",
                           self.defi_reponse.get().replace(" ", ""))
        self.defi_score[1] += 1
        correct = saisi == self.defi_attendu
        self.defi_score[0] += int(correct)
        self.lbl_defi_score.config(text=f"Score des défis : {self.defi_score[0]} / {self.defi_score[1]}")
        self.lbl_defi_retour.config(
            text=("✅ Exact ! " if correct else "🔎 Pas encore. ") + self.defi_explication,
            foreground="#1E8E3E" if correct else "#B45F06")

    def indice_defi(self):
        if self.defi_attendu is None:
            self.lbl_defi_retour.config(text="Lance d’abord un défi.", foreground="#B45F06")
        else:
            self.lbl_defi_retour.config(text="💡 Indice : " + self.defi_explication,
                                        foreground="#0B5394")

    def maj_pourquoi(self, n=None, evenement=None):
        """Explique soit un nœud sélectionné, soit l'étape d'animation courante."""
        if not hasattr(self, "lbl_pourquoi"):
            return
        if evenement:
            self.lbl_pourquoi.config(text="▶ " + evenement)
            return
        if not self.mode_pourquoi.get():
            self.lbl_pourquoi.config(text="Active le mode puis clique sur un nœud pour comprendre ses liens.")
            return
        if n is None:
            self.lbl_pourquoi.config(text="Clique sur un nœud : je t’expliquerai son rôle et ses pointeurs.")
            return
        parent = parent_de(self.racine, n)
        lien = "C’est la racine." if parent is None else (
            f"C’est le fils gauche de {parent.valeur}." if parent.gauche is n else
            f"C’est le fils droit de {parent.valeur}.")
        fils = nb_fils(n)
        role = "une feuille" if fils == 0 else ("un nœud à un fils" if fils == 1 else "un nœud à deux fils")
        explication = (f"{n.valeur} est {role}. {lien} "
                       f"Son pointeur gauche vaut {'0x%016X' % id(n.gauche) if n.gauche else 'NULL'} ; "
                       f"son pointeur droit vaut {'0x%016X' % id(n.droite) if n.droite else 'NULL'}. "
                       "Un pointeur NULL signifie qu’aucun enfant n’est relié de ce côté.")
        self.lbl_pourquoi.config(text=explication)

    # ----- panneau d'animation
    def panneau_animation(self, parent):
        """Ajoute les réglages de vitesse, pause, progression et affichage."""
        lf = ttk.LabelFrame(parent, text="Animation et affichage", padding=4)
        lf.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(lf, text="Animer", variable=self.animer).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(lf, text="Pas à pas", variable=self.pas_a_pas).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(lf, text="Détailler sous-arbres vides",
                        variable=self.details).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(lf, text="Colorier les feuilles", variable=self.colorier_feuilles,
                        command=self.dessiner).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(lf, text="Afficher niveau / hauteur", variable=self.show_info,
                        command=self.dessiner).grid(row=1, column=1, columnspan=2, sticky="w")
        v = ttk.Frame(lf)
        v.grid(row=2, column=0, columnspan=3, sticky="ew", pady=3)
        ttk.Label(v, text="Lent").pack(side="left")
        ttk.Scale(v, from_=1, to=10, variable=self.vitesse).pack(side="left", fill="x",
                                                                    expand=True, padx=4)
        ttk.Label(v, text="Rapide").pack(side="left")
        b = ttk.Frame(lf)
        b.grid(row=3, column=0, columnspan=3, sticky="ew")
        self.btn_pause = ttk.Button(b, text="⏸ Pause", command=self.bouton_pause)
        self.btn_pause.pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(b, text="⏭ Suivant", command=self.bouton_suivant).pack(
            side="left", expand=True, fill="x", padx=1)
        ttk.Button(b, text="⏩ Terminer", command=self.bouton_terminer).pack(
            side="left", expand=True, fill="x", padx=1)
        ttk.Button(b, text="Effacer couleurs", command=self.effacer_couleurs).pack(
            side="left", expand=True, fill="x", padx=1)
        ttk.Button(lf, text="↺ Réinitialiser la disposition des nœuds",
                   command=self.reset_positions).grid(row=4, column=0, columnspan=3,
                                                       sticky="ew", pady=(3, 0))
        ttk.Checkbutton(lf, text="Afficher les fils absents en pointillés",
                        variable=self.afficher_manquants,
                        command=self.dessiner).grid(row=5, column=0, columnspan=3, sticky="w")

    # ==================================================================
    #  DESSIN
    # ==================================================================

    def calculer_positions(self):
        """Calcule les coordonnées du dessin et ajoute les décalages de l'utilisateur."""
        self.positions = {}
        self.infos = {}
        if self.racine is None:
            return 0, 0
        compteur = [0]
        brut = {}

        def rec(n, prof):
            if n is None:
                return -1
            rec_g = rec(n.gauche, prof + 1)
            brut[n] = (compteur[0], prof)
            compteur[0] += 1
            rec_d = rec(n.droite, prof + 1)
            h = 1 + max(rec_g, rec_d)
            self.infos[n] = (prof, h)
            return h
        rec(self.racine, 0)
        nb = compteur[0]
        hmax = max(p for _, p in brut.values())
        dx, dy, marge = 48, 78, 40
        largeur = 2 * marge + (nb - 1) * dx
        hauteur_px = 2 * marge + hmax * dy + 20
        cw = max(self.canvas.winfo_width(), 200)
        decalage = max(0, (cw - largeur) / 2)
        self.base = {}
        maxx = maxy = 0
        for n, (i, p) in brut.items():
            bx, by = decalage + marge + i * dx, marge + p * dy
            self.base[n] = (bx, by)
            ox, oy = self.decalages.get(n, (0, 0))
            self.positions[n] = (bx + ox, by + oy)
            maxx, maxy = max(maxx, bx + ox), max(maxy, by + oy)
        return max(largeur, cw - 4, maxx + marge), max(hauteur_px, 100, maxy + marge)

    def couleur(self, n):
        if n is self.courant:
            return C_COURANT
        k = self.marques.get(n)
        if k in COULEURS:
            return COULEURS[k]
        if self.colorier_feuilles.get() and est_feuille(n):
            return C_FEUILLE
        return C_NORMAL

    def dessiner(self):
        """Redessine l'arbre, les pointeurs, les cadres d'appel et les surlignages."""
        c = self.canvas
        self._enregistrer_historique()
        c.delete("all")
        self.emplacements_vides = []
        self.positions_vides_base = {}
        if self.racine is None:
            c.configure(scrollregion=(0, 0, 10, 10))
            c.create_text(max(c.winfo_width(), 300) // 2, 120, font=("Arial", 15),
                          fill="#888", text="Arbre vide\nCréez la racine, insérez une valeur\n"
                                            "ou chargez un exemple (onglet « Arbre »)")
            self.maj_selection()
            self._appliquer_zoom(320, 220)
            return
        w, h = self.calculer_positions()
        if self.vue_pointeurs.get():
            nodes = noeuds(self.racine, "RGD")
            table_h = 96 + len(nodes) * 34
            table_w, tree_w = 820, max(520, 250 * len(nodes))
            c.configure(scrollregion=(0, 0, table_w + tree_w + 40, table_h))
            x0, y0 = 24, 24
            c.create_text(x0, 0, anchor="nw", text="STRUCTURE MÉMOIRE · ADRESSES HEXADÉCIMALES",
                          font=("Arial", 15, "bold"), fill="#101828")
            y0 += 34
            c.create_rectangle(x0, y0, x0 + 820, y0 + 38, fill="#EFE4C7", outline="#D3BD83")
            for px, titre in ((x0 + 12, "ADRESSE DU NŒUD"), (x0 + 190, "VALEUR"),
                              (x0 + 310, "POINTEUR GAUCHE"), (x0 + 570, "POINTEUR DROIT")):
                c.create_text(px, y0 + 19, anchor="w", text=titre, font=("Arial", 10, "bold"), fill="#344054")
            for i, n in enumerate(nodes):
                y = y0 + 38 + i * 34
                c.create_rectangle(x0, y, x0 + 820, y + 34,
                                   fill="#DCEBFF" if n is self.selection else ("#FFFEFA" if i % 2 == 0 else "#F6F0E2"), outline="#E9DFC8")
                c.create_text(x0 + 12, y + 17, anchor="w", text=f"0x{id(n):016X}", font=("Consolas", 10), fill="#805B12")
                c.create_text(x0 + 190, y + 17, anchor="w", text=str(n.valeur), font=("Consolas", 11, "bold"), fill="#101828")
                c.create_text(x0 + 310, y + 17, anchor="w", text=(f"0x{id(n.gauche):016X}" if n.gauche else "NULL"), font=("Consolas", 10), fill="#175CD3")
                c.create_text(x0 + 570, y + 17, anchor="w", text=(f"0x{id(n.droite):016X}" if n.droite else "NULL"), font=("Consolas", 10), fill="#175CD3")
            c.create_text(x0, y0 + 44 + len(nodes) * 34, anchor="w",
                          text=f"Adresse de la racine : 0x{id(self.racine):016X}",
                          font=("Consolas", 10, "bold"), fill="#067647")
            # Vue de l'arbre à droite, ajustée à la hauteur de la table.
            tx = x0 + table_w + 28
            c.create_text(tx, 0, anchor="nw", text="ARBRE · VALEUR | GAUCHE | DROITE",
                          font=("Arial", 15, "bold"), fill="#101828")
            preorder = []
            def placer(n, depth=0):
                if n is None: return
                placer(n.gauche, depth + 1)
                preorder.append((n, depth))
                placer(n.droite, depth + 1)
            placer(self.racine)
            max_depth = max(d for _, d in preorder)
            gap_x = (tree_w - 90) / max(1, len(nodes))
            self._pointer_node_width = min(234, gap_x * 0.88)
            gap_y = max(48, (table_h - 92) / max(1, max_depth))
            self.positions = {}
            self.base = {}
            for i, (n, depth) in enumerate(preorder):
                bx, by = tx + 42 + i * gap_x, 65 + depth * gap_y
                self.base[n] = (bx, by)
                ox, oy = self.decalages.get(n, (0, 0))
                self.positions[n] = (bx + ox, by + oy)
            for n, (x, y) in self.positions.items():
                for child, side in ((n.gauche, "g"), (n.droite, "d")):
                    if child in self.positions:
                        fx, fy = self.positions[child]
                        largeur_case = self._pointer_node_width / 3
                        # Le pointeur gauche part de sa case centrale, le droit de sa case droite.
                        depart_x = x if side == "g" else x + largeur_case
                        c.create_line(depart_x, y + 21, fx, fy - 21,
                                      arrow="last", arrowshape=(10, 12, 4),
                                      width=2, fill="#475467")
            for n, (x, y) in self.positions.items():
                self.dessiner_noeud_pointeurs(c, n, x, y, self._pointer_node_width)
            self.maj_selection()
            self._appliquer_zoom(table_w + tree_w + 40, table_h)
            return
        if self.afficher_manquants.get():
            occupes = list(self.positions.values())
            for n, (x, y) in self.positions.items():
                if n.gauche is None:
                    cote, px, py = "gauche", max(24, x - 48), y + 78
                    while any((px - ox) ** 2 + (py - oy) ** 2 < 36 ** 2 for ox, oy in occupes):
                        if px > 24:
                            px = max(24, px - 36)
                        else:
                            py += 36
                    self.positions_vides_base[(n, cote)] = (px, py)
                    dx, dy = self.decalages_vides.get((n, cote), (0, 0))
                    px, py = px + dx, py + dy
                    self.emplacements_vides.append((n, cote, px, py))
                    occupes.append((px, py))
                if n.droite is None:
                    cote, px, py = "droite", x + 48, y + 78
                    while any((px - ox) ** 2 + (py - oy) ** 2 < 36 ** 2 for ox, oy in occupes):
                        px += 36
                    self.positions_vides_base[(n, cote)] = (px, py)
                    dx, dy = self.decalages_vides.get((n, cote), (0, 0))
                    px, py = px + dx, py + dy
                    self.emplacements_vides.append((n, cote, px, py))
                    occupes.append((px, py))
            if self.emplacements_vides:
                w = max(w, max(x + 24 for _, _, x, _ in self.emplacements_vides))
                h = max(h, max(y + 24 for _, _, _, y in self.emplacements_vides))
        c.configure(scrollregion=(0, 0, w, h))
        if self.selection is not None and self.selection not in self.positions:
            self.selection = None
        self.maj_selection()
        if self.en_cours and self.appels_recursifs:
            palette_appels = ("#A77B1B", "#765A32", "#397A65", "#7253A3", "#B35C40")
            for profondeur, racine_appel in enumerate(self.appels_recursifs):
                ns = noeuds(racine_appel)
                # Des points autour de chaque bulle produisent une enveloppe
                # arrondie qui épouse le groupe au lieu d'un cadre rectangulaire.
                directions = ((-1, 0), (-0.707, -0.707), (0, -1), (0.707, -0.707),
                              (1, 0), (0.707, 0.707), (0, 1), (-0.707, 0.707))
                points = []
                rayon_contour = RAYON + 20
                for n in ns:
                    nx, ny = self.positions[n]
                    points.extend((round(nx + dx * rayon_contour),
                                   round(ny + dy * rayon_contour)) for dx, dy in directions)
                contour = enveloppe_convexe(points)
                if len(contour) < 3:
                    continue
                x1 = min(x for x, _ in contour)
                y1 = min(y for _, y in contour)
                couleur = palette_appels[profondeur % len(palette_appels)]
                selectionne = profondeur == len(self.appels_recursifs) - 1
                coords = [coord for point in contour + [contour[0]] for coord in point]
                c.create_line(*coords, fill=couleur, width=3 if selectionne else 2,
                              dash=(3, 5), smooth=True, splinesteps=18,
                              capstyle="round", joinstyle="round")
                c.create_text(x1 + 8, y1 - 8, anchor="sw",
                              text=f"APPEL {profondeur + 1} · sous-arbre {racine_appel.valeur}",
                              font=("Arial", 9, "bold"), fill=couleur)
        # arêtes
        for n, (x, y) in self.positions.items():
            for f in (n.gauche, n.droite):
                if f is not None:
                    fx, fy = self.positions[f]
                    chemin = self.marques.get(n) == "path" and self.marques.get(f) == "path"
                    c.create_line(x, y, fx, fy, arrow="last", arrowshape=(10, 12, 4),
                                  width=4 if chemin else 2, capstyle="round",
                                  fill="#AF52DE" if chemin else "#8E8E93")
        # Les cercles pointillés représentent des liens NULL encore disponibles.
        for parent, cote, x, y in self.emplacements_vides:
            px, py = self.positions[parent]
            selectionne = parent is self.selection and self.dessin_cote.get() == cote
            couleur = "#D97706" if selectionne else "#98A2B3"
            c.create_line(px, py + RAYON, x, y - 15, fill=couleur, width=2,
                          dash=(3, 3), arrow="last", arrowshape=(8, 10, 4))
            c.create_oval(x - 15, y - 15, x + 15, y + 15, fill=C_FOND,
                          outline=couleur, width=2, dash=(3, 3))
            c.create_text(x, y, text="∅", fill=couleur, font=("Arial", 12, "bold"))
        # nœuds
        for n, (x, y) in self.positions.items():
            self.dessiner_noeud(c, n, x, y)
            if self.show_info.get():
                niv, hh = self.infos[n]
                c.create_text(x, y + RAYON + 9, text=f"n{niv} h{hh}", font=("Arial", 8),
                              fill="#555")
        self._appliquer_zoom(w, h)

    def dessiner_noeud_pointeurs(self, c, n, x, y, largeur=234):
        """Dessine les cases valeur/gauche/droite utilisées comme zones cliquables."""
        widths, h = (largeur / 3,) * 3, 42
        left = x - sum(widths) / 2
        vals = (str(n.valeur), f"0x{id(n.gauche):016X}" if n.gauche else "NULL",
                f"0x{id(n.droite):016X}" if n.droite else "NULL")
        labels = ("VALEUR", "GAUCHE", "DROITE")
        for i, width in enumerate(widths):
            x1 = left + sum(widths[:i])
            champ = ("valeur", "gauche", "droite")[i]
            cible = n if i == 0 else (n.gauche if i == 1 else n.droite)
            tag = f"champ_{id(n)}_{champ}"
            c.create_rectangle(x1, y - h/2, x1 + width, y + h/2,
                               fill="#DCEBFF" if n is self.selection else "#FFFDF7",
                               outline="#175CD3" if n is self.selection else "#667085", width=2 if n is self.selection else 1,
                               tags=(tag,))
            c.create_text(x1 + width/2, y - 11, text=labels[i], font=("Arial", 7, "bold"), fill="#475467", tags=(tag,))
            c.create_text(x1 + width/2, y + 9, text=vals[i], font=("Consolas", 8 if i else 9, "bold"), fill="#101828", tags=(tag,))
            c.tag_bind(tag, "<Button-1>", lambda ev, node=cible: self.selectionner_champ(node))

    def selectionner_champ(self, n):
        """Sélectionne la cible du champ cliqué dans la vue pointeurs."""
        self.selection = n
        self.drag = None
        self.maj_pourquoi(n)
        self.dessiner()
        return "break"

    def dessiner_noeud(self, c, n, x, y):
        """Dessine le nœud graphique selon sa sélection, son état et sa couleur."""
        r = RAYON + 1
        base = self.couleur(n)
        if getattr(n, "couleur_rn", "N") == "R": base = "#FF6961"
        elif getattr(n, "couleur_rn", "N") == "N" and getattr(self, "_rn_actif", False):
            base = "#30343B"
        # ombre portée (plusieurs ovales de plus en plus sombres)
        for k, col in enumerate(("#ECECF1", "#E2E2E8", "#D6D6DD", "#C8C8D0")):
            s = r + 3 - k
            c.create_oval(x - s, y + 3 - s, x + s, y + 3 + s, fill=col, outline="")
        # anneau de sélection bleu iOS
        if n is self.selection:
            c.create_oval(x - r - 4, y - r - 4, x + r + 4, y + r + 4, outline="#F0E2BD", width=7)
            c.create_oval(x - r - 4, y - r - 4, x + r + 4, y + r + 4, outline=C_OR, width=2)
        # corps : dégradé radial (ovales concentriques décalés vers le haut-gauche)
        sombre = melange(base, "#000000", 0.22)
        clair = melange(base, "#FFFFFF", 0.55)
        pas = 9
        for i in range(pas):
            u = i / (pas - 1)
            rr = r * (1 - 0.62 * u)
            cx, cy = x - 0.20 * r * u, y - 0.28 * r * u
            c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                          fill=melange(sombre, clair, u ** 0.8),
                          outline=melange(base, "#000000", 0.35) if i == 0 else "")
        # reflet brillant en haut (effet « verre »)
        c.create_oval(x - 0.62 * r, y - 0.92 * r, x + 0.62 * r, y - 0.18 * r,
                      fill=melange(base, "#FFFFFF", 0.50), outline="")
        c.create_oval(x - 0.50 * r, y - 0.86 * r, x + 0.50 * r, y - 0.30 * r,
                      fill=melange(base, "#FFFFFF", 0.75), outline="")
        # texte (légère gravure blanche dessous)
        police = ("Arial", 12, "bold")
        c.create_text(x, y + 1, text=str(n.valeur), font=police, fill=melange(base, "#FFFFFF", 0.8))
        couleur_texte = "white" if base == "#30343B" else "#1C1C1E"
        c.create_text(x, y, text=str(n.valeur), font=police, fill=couleur_texte)

    def noeud_en(self, x, y):
        """Trouve le nœud dont la zone dessinée contient le point du clic."""
        for n, (nx, ny) in self.positions.items():
            half_width = getattr(self, "_pointer_node_width", 234) / 2
            if self.vue_pointeurs.get() and nx - half_width <= x <= nx + half_width and ny - 22 <= y <= ny + 22:
                return n
            if (nx - x) ** 2 + (ny - y) ** 2 <= RAYON ** 2:
                return n
        return None

    def emplacement_vide_en(self, x, y):
        """Renvoie le parent et le côté de la bulle vide touchée, si présente."""
        for parent, cote, px, py in self.emplacements_vides:
            if (px - x) ** 2 + (py - y) ** 2 <= 18 ** 2:
                return parent, cote, px, py
        return None

    def clic(self, ev):
        """Gère le clic, la sélection d'un nœud et le début d'un déplacement."""
        x, y = self.canvas.canvasx(ev.x) / self.zoom, self.canvas.canvasy(ev.y) / self.zoom
        n = self.noeud_en(x, y)
        vide = self.emplacement_vide_en(x, y) if n is None else None
        if vide is not None:
            self.selection, cote, px, py = vide
            self.dessin_cote.set(cote)
            self.drag = None
            self.drag_emplacement = (self.selection, cote, px, py)
            self.drag_emplacement_deplace = False
            self.drag_depart = (x, y, 0, 0)
            self.canvas.config(cursor="fleur")
            self.maj_pourquoi(self.selection)
            self.dessiner()
            return
        if self.dessin_manuel.get() and n is None:
            self.ajouter_noeud_manuel(x, y)
            return
        self.selection = n
        self.drag = n
        self.maj_pourquoi(n)
        if n is not None:
            ox, oy = self.decalages.get(n, (0, 0))
            self.drag_depart = (x, y, ox, oy)
            self.canvas.config(cursor="fleur")
        self.dessiner()

    def ajouter_noeud_manuel(self, x, y):
        """Crée un nœud à l'endroit cliqué après validation du parent et du côté."""
        if self.racine is not None and self.selection is None:
            messagebox.showinfo("Choisir un parent", "Cliquez d'abord sur le nœud parent.")
            return
        if self.racine is not None and getattr(self.selection, self.dessin_cote.get()) is not None:
            messagebox.showinfo("Emplacement occupé", f"Le fils {self.dessin_cote.get()} existe déjà.")
            return
        try:
            valeur = int(self.dessin_valeur.get().strip())
        except ValueError:
            messagebox.showwarning("Valeur invalide", "Saisissez un entier avant de placer un nœud.")
            return
        self.preparer()
        n = Noeud(valeur)
        if self.racine is None:
            self.racine = n
        else:
            parent = self.selection
            cote = self.dessin_cote.get()
            setattr(parent, cote, n)
        self.selection = n
        self.decalages.pop(n, None)
        self.dessiner()
        bx, by = self.base[n]
        self.decalages[n] = (x - bx, y - by)
        self.dessiner()
        self._montrer_code_arbre()
        self.res_notebook.select(self.tab_code)

    def activer_dessin_manuel(self):
        """Bascule vers le dessin libre sur le canevas principal."""
        if self.dessin_manuel.get():
            self.vue_pointeurs.set(False)
            self.afficher_manquants.set(True)
        self.dessiner()

    def deplacer(self, ev):
        """Actualise le décalage du nœud saisi, sans déplacer ses enfants."""
        if self.drag_emplacement is not None:
            parent, cote, px, py = self.drag_emplacement
            x, y = self.canvas.canvasx(ev.x) / self.zoom, self.canvas.canvasy(ev.y) / self.zoom
            x0, y0, _, _ = self.drag_depart
            dx, dy = x - x0, y - y0
            if dx * dx + dy * dy > 16:
                self.drag_emplacement_deplace = True
                bx, by = self.positions_vides_base[(parent, cote)]
                self.decalages_vides[(parent, cote)] = (px + dx - bx, py + dy - by)
                self.dessiner()
            return
        n = self.drag
        if n is None or n not in self.base:
            return
        x, y = self.canvas.canvasx(ev.x) / self.zoom, self.canvas.canvasy(ev.y) / self.zoom
        x0, y0, ox, oy = self.drag_depart
        bx, by = self.base[n]
        if self.vue_pointeurs.get():
            nx = max(24, bx + ox + (x - x0))
            ny = max(46, by + oy + (y - y0))
        else:
            nx = max(RAYON + 2, bx + ox + (x - x0))
            ny = max(RAYON + 2, by + oy + (y - y0))
        self.decalages[n] = (nx - bx, ny - by)
        self.dessiner()

    def relacher(self, ev):
        if self.drag_emplacement is not None:
            parent, cote, px, py = self.drag_emplacement
            if self.dessin_manuel.get() and not self.drag_emplacement_deplace:
                self.selection = parent
                self.dessin_cote.set(cote)
                self.ajouter_noeud_manuel(px, py)
            self.drag_emplacement = None
            self.drag_emplacement_deplace = False
            self.drag = None
            self.canvas.config(cursor="")
            return
        self.drag = None
        self.canvas.config(cursor="")

    def reset_positions(self):
        self.decalages = {}
        self.decalages_vides = {}
        self.dessiner()

    def reinitialiser_disposition(self):
        """Efface les déplacements manuels et recalcule les positions automatiques."""
        self.decalages = {}
        self.decalages_vides = {}
        self.positions = {}
        self.base = {}
        self.infos = {}
        self.dessiner()

    def maj_selection(self):
        if self.selection is None:
            self.lbl_sel.config(text="Aucun nœud sélectionné (cliquez sur un nœud)")
        else:
            n = self.selection
            self.lbl_sel.config(text=f"Nœud sélectionné : valeur={n.valeur} | gauche={n.gauche.valeur if n.gauche else 'NULL'} | droite={n.droite.valeur if n.droite else 'NULL'}")

    def menu_contextuel(self, ev):
        """Affiche les actions liées au nœud, au lien vide ou au canevas."""
        x, y = self.canvas.canvasx(ev.x) / self.zoom, self.canvas.canvasy(ev.y) / self.zoom
        n = self.noeud_en(x, y)
        vide = self.emplacement_vide_en(x, y) if n is None else None
        if vide is not None:
            parent, cote, _, _ = vide
            self.selection = parent
            self.dessin_cote.set(cote)
        else:
            self.selection = n
        self.dessiner()

        m = tk.Menu(self, tearoff=0)
        if vide is not None:
            _, cote, _, _ = vide
            libelle = "gauche" if cote == "gauche" else "droit"
            m.add_command(label=f"Ajouter un fils {libelle}", command=lambda: self.ajouter_fils(cote))
        elif n is None:
            if self.racine is None:
                m.add_command(label="Créer la racine", command=self.creer_racine)
            else:
                m.add_command(label="Aucun nœud sous le pointeur", state="disabled")
        else:
            if n.gauche is None:
                m.add_command(label="Ajouter un fils gauche", command=lambda: self.ajouter_fils("gauche"))
            if n.droite is None:
                m.add_command(label="Ajouter un fils droit", command=lambda: self.ajouter_fils("droite"))
            m.add_command(label="Modifier la valeur…", command=self.modifier_valeur)
            m.add_command(label="Copier la valeur", command=lambda: self.copier_valeur_noeud(n))
            m.add_separator()
            m.add_command(label="Informations sur ce nœud", command=self.infos_noeud)
            m.add_command(label="Successeur infixé (ABR)", command=lambda: self.voisin_abr("succ"))
            m.add_command(label="Prédécesseur infixé (ABR)", command=lambda: self.voisin_abr("pred"))
            m.add_command(label="Miroir de l’arbre", command=self.miroir)
            m.add_separator()
            m.add_command(label="Supprimer ce nœud (ABR)", command=lambda: self.supprimer_abr(n.valeur))
            m.add_command(label="Supprimer ce sous-arbre", command=self.supprimer_sous_arbre)

        depart_parcours = vide[0] if vide is not None else n if n is not None else self.racine
        if depart_parcours is not None:
            menu_parcours = tk.Menu(m, tearoff=0)
            menu_parcours.add_command(
                label="Préfixé — RGD",
                command=lambda r=depart_parcours: self.parcours("RGD", "Parcours préfixé (RGD)", "prefixe", r))
            menu_parcours.add_command(
                label="Infixé — GRD",
                command=lambda r=depart_parcours: self.parcours("GRD", "Parcours infixé (GRD)", "infixe", r))
            menu_parcours.add_command(
                label="Postfixé — GDR",
                command=lambda r=depart_parcours: self.parcours("GDR", "Parcours postfixé (GDR)", "postfixe", r))
            menu_parcours.add_command(
                label="Infixé inversé — DRG",
                command=lambda r=depart_parcours: self.parcours("DRG", "Parcours infixé inversé (DRG)", "inverse", r))
            menu_parcours.add_command(
                label="En largeur — niveaux",
                command=lambda r=depart_parcours: self.parcours_largeur(r))
            m.add_cascade(label="Parcours", menu=menu_parcours)

        if m.index("end") is not None:
            m.add_separator()
        m.add_command(label="Annuler", command=self.annuler,
                      state="normal" if self.historique_index > 0 else "disabled")
        m.add_command(label="Rétablir", command=self.retablir,
                      state="normal" if self.historique_index < len(self.historique) - 1 else "disabled")
        zoom = tk.Menu(m, tearoff=0)
        zoom.add_command(label="Agrandir", command=lambda: self.modifier_zoom(1.15))
        zoom.add_command(label="Réduire", command=lambda: self.modifier_zoom(1 / 1.15))
        zoom.add_command(label="Réinitialiser le zoom", command=self.zoom_initial)
        m.add_cascade(label="Zoom", menu=zoom)
        m.add_command(label="Réinitialiser la disposition", command=self.reinitialiser_disposition)
        m.add_checkbutton(label="Vue valeur / pointeurs", variable=self.vue_pointeurs,
                          command=self.dessiner)
        m.add_checkbutton(label="Afficher les fils absents", variable=self.afficher_manquants,
                          command=self.dessiner)
        m.add_separator()
        m.add_command(label="Plein écran", command=self.ouvrir_plein_ecran)
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    # ==================================================================
    #  TEXTES (résultat, trace, algorithme, séquence)
    # ==================================================================

    def vider_texte(self, t):
        t.config(state="normal")
        t.delete("1.0", "end")
        t.config(state="disabled")

    def ecrire(self, t, texte, tag=None):
        t.config(state="normal")
        t.insert("end", texte, tag) if tag else t.insert("end", texte)
        t.see("end")
        t.config(state="disabled")

    def log(self, msg):
        self.ecrire(self.txt_trace, msg + "\n")

    def afficher_resultat(self, titre, lignes, valeur=None):
        """Remplace le panneau de résultat par un titre et ses explications."""
        self.vider_texte(self.txt_res)
        self.ecrire(self.txt_res, titre + "\n", "titre")
        for l in lignes:
            if isinstance(l, tuple):
                self.ecrire(self.txt_res, l[0] + "\n", l[1])
            else:
                self.ecrire(self.txt_res, l + "\n")
        if valeur is not None:
            self.ecrire(self.txt_res, "\n" + str(valeur) + "\n", "res")
        self.txt_res.see("1.0")

    def afficher_algo(self, cle=None):
        """Affiche le pseudo-code, Python ou C de l'opération active."""
        if cle is None:
            cle = self.algo_courant
        if cle is None:
            return
        self.algo_courant = cle
        titre, texte = ALGOS[cle]
        if self.mode_code.get() == "python":
            texte = ALGOS_PY.get(cle, texte)
            titre += "   —   Python"
        elif self.mode_code.get() == "c":
            texte = STRUCT_C + "\n\n" + ALGOS_C.get(cle, "// (version C non disponible)")
            titre += "   —   C"
        self.vider_texte(self.txt_algo)
        self.ecrire(self.txt_algo, titre + "\n\n", "titre")
        self.ecrire(self.txt_algo, texte)
        self.colorier_code()
        self.txt_algo.see("1.0")

    def colorier_code(self):
        """Coloration syntaxique simple du panneau « Algorithme »."""
        t = self.txt_algo
        mode = self.mode_code.get()
        mots = {"python": PY_MOTS, "c": C_MOTS}.get(mode, PSEUDO_MOTS)
        marqueur = "#" if mode == "python" else "//"
        motif = re.compile(r"\b(" + "|".join(re.escape(m) for m in mots) + r")\b")
        nb = int(t.index("end-1c").split(".")[0])
        for i in range(3, nb + 1):
            ligne = t.get(f"{i}.0", f"{i}.end")
            k = ligne.find(marqueur)
            code = ligne if k < 0 else ligne[:k]
            for m in motif.finditer(code):
                t.tag_add("kw", f"{i}.{m.start()}", f"{i}.{m.end()}")
            for m in re.finditer(r"\b\d+\b", code):
                t.tag_add("num", f"{i}.{m.start()}", f"{i}.{m.end()}")
            if k >= 0:
                t.tag_add("com", f"{i}.{k}", f"{i}.end")

    def charger_logo(self):
        """Charge une image de logo locale, ou renvoie None si aucune image n'existe."""
        dossier = os.path.dirname(os.path.abspath(__file__))
        for nom in ("logo.png", "logo.gif", "logo.PNG"):
            chemin = os.path.join(dossier, nom)
            if os.path.exists(chemin):
                try:
                    img = tk.PhotoImage(file=chemin)
                    try:
                        self.iconphoto(True, img)
                    except tk.TclError:
                        pass
                    h = img.height()
                    if h > 64:
                        img = img.subsample(-(-h // 64))
                    return img
                except tk.TclError:
                    return None
        return None

    def maj_sequence(self):
        """Actualise la bande affichant les valeurs déjà produites par un parcours."""
        if self.sequence:
            self.lbl_seq.config(text=f"{self.titre_anim} :  " + "  →  ".join(map(str, self.sequence)))
        else:
            self.lbl_seq.config(text="")

    # ==================================================================
    #  MOTEUR D'ANIMATION
    # ==================================================================

    def delai(self):
        return int(2000 / max(1.0, self.vitesse.get()))

    def preparer(self):
        """Termine une animation précédente et efface les marques visuelles."""
        self.finir_en_cours()
        self.marques = {}
        self.courant = None
        self.appels_recursifs = []

    def finir_en_cours(self):
        if self.en_cours:
            self.terminer_rapide()

    def effacer_couleurs(self):
        self.finir_en_cours()
        self.marques = {}
        self.courant = None
        self.sequence = []
        self.maj_sequence()
        self.dessiner()

    def lancer(self, titre, events, on_finish=None, algo=None):
        """Lance une file d'événements en mode animé, pas à pas ou instantané."""
        self.preparer()
        self.titre_anim = titre
        self.events = events
        self.ev_i = 0
        self.on_finish = on_finish
        self.sequence = []
        self.maj_sequence()
        self.vider_texte(self.txt_trace)
        self.log(f"=== {titre} ===")
        if algo:
            self.afficher_algo(algo)
        self.en_cours = True
        if (not self.animer.get()) or not events:
            self.terminer_rapide()
            return
        self.pause = self.pas_a_pas.get()
        self.btn_pause.config(text="▶ Reprendre" if self.pause else "⏸ Pause")
        self.res_notebook.select(self.tab_trace)
        if self.pause:
            self.log("(mode pas à pas : cliquez sur ⏭ Suivant)")
        self.dessiner()
        if not self.pause:
            self._tick()

    def appliquer(self, ev):
        """Met à jour les couleurs, la pile récursive, la trace et la séquence."""
        n = ev.noeud
        if ev.kind == "call" and n is not None:
            self.appels_recursifs.append(n)
        elif ev.kind == "return" and n is not None:
            if self.appels_recursifs and self.appels_recursifs[-1] is n:
                self.appels_recursifs.pop()
            elif n in self.appels_recursifs:
                self.appels_recursifs.remove(n)
        if n is not None:
            self.courant = n
            if ev.kind in ("visit", "skip", "found", "bad", "path", "enter"):
                # un nœud « visité » ne redevient pas « enter »
                if not (ev.kind == "enter" and self.marques.get(n) not in (None, "enter")):
                    self.marques[n] = ev.kind
        if ev.out is not None:
            self.sequence.append(ev.out)
            self.maj_sequence()
        if ev.msg:
            self.log(ev.msg)
            if self.titre_anim.startswith("Calculatrice polonaise"):
                self.calcul_pile.set(ev.msg)
            if self.mode_pourquoi.get():
                raisons = {
                    "enter": "On examine ce nœud avant de choisir la suite.",
                    "visit": "Le nœud est traité à cette étape de l’algorithme.",
                    "found": "La condition de recherche est satisfaite ici.",
                    "skip": "Ce nœud ne répond pas au critère et est ignoré.",
                    "empty": "Un pointeur NULL marque la fin de cette branche.",
                    "bad": "Cette étape modifie ou signale la structure du nœud.",
                    "path": "Ce nœud appartient au chemin suivi dans l’arbre.",
                    "call": "Le cadre pointillé délimite le sous-arbre de cet appel récursif.",
                    "return": "L’appel se termine ; son cadre pointillé disparaît et l’algorithme remonte au parent.",
                }
                self.maj_pourquoi(evenement=f"{ev.msg}  {raisons.get(ev.kind, 'Observe le lien entre cette étape et la structure.')}")

    def pas(self):
        """Applique le prochain événement puis redessine le canevas."""
        ev = self.events[self.ev_i]
        self.ev_i += 1
        self.appliquer(ev)
        self.dessiner()

    def _tick(self):
        """Planifie l'étape d'animation suivante avec le délai courant."""
        self.job = None
        if not self.en_cours:
            return
        if self.ev_i < len(self.events):
            self.pas()
        if self.ev_i >= len(self.events):
            self.terminer()
            return
        if not self.pause:
            self.job = self.after(self.delai(), self._tick)

    def annuler_job(self):
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None

    def terminer_rapide(self):
        """Applique tous les événements restants sans temporisation."""
        self.annuler_job()
        while self.ev_i < len(self.events):
            self.appliquer(self.events[self.ev_i])
            self.ev_i += 1
        self.terminer()

    def terminer(self):
        """Réinitialise l'animation et exécute son action de finalisation."""
        self.annuler_job()
        self.en_cours = False
        self.courant = None
        self.appels_recursifs = []
        self.log("— fin —")
        cb, self.on_finish = self.on_finish, None
        if cb:
            cb()
        self.res_notebook.select(self.tab_res)
        self.btn_pause.config(text="⏸ Pause")
        self.dessiner()

    def bouton_pause(self):
        if not self.en_cours:
            return
        if self.pause:
            self.pause = False
            self.btn_pause.config(text="⏸ Pause")
            self._tick()
        else:
            self.pause = True
            self.annuler_job()
            self.btn_pause.config(text="▶ Reprendre")

    def bouton_suivant(self):
        if not self.en_cours:
            return
        self.pause = True
        self.annuler_job()
        self.btn_pause.config(text="▶ Reprendre")
        if self.ev_i < len(self.events):
            self.pas()
        if self.ev_i >= len(self.events):
            self.terminer()

    def bouton_terminer(self):
        if self.en_cours:
            self.terminer_rapide()

    # ==================================================================
    #  UTILITAIRES
    # ==================================================================

    def exiger_arbre(self):
        if self.racine is None:
            messagebox.showinfo("Arbre vide", "L'arbre est vide : construisez-en un d'abord.")
            return False
        return True

    def exiger_selection(self):
        if self.selection is None or self.selection not in self.positions:
            messagebox.showinfo("Aucune sélection", "Cliquez d'abord sur un nœud de l'arbre.")
            return False
        return True

    def lire_entier(self):
        s = self.valeur_var.get().strip()
        try:
            return int(s)
        except ValueError:
            messagebox.showwarning("Valeur invalide",
                                   "Saisissez un nombre entier dans le champ « Valeur ».")
            self.entry_valeur.focus_set()
            return None

    def remplacer(self, parent, ancien, nouveau):
        if parent is None:
            self.racine = nouveau
        elif parent.gauche is ancien:
            parent.gauche = nouveau
        else:
            parent.droite = nouveau

    def ouvrir_plein_ecran(self):
        """Affiche le canevas de l’arbre dans une fenêtre plein écran."""
        if self._plein_ecran_window is not None:
            try:
                self._plein_ecran_window.lift()
                return
            except tk.TclError:
                self._plein_ecran_window = None
        fen = tk.Toplevel(self)
        fen.title("TreeLab — Arbre en plein écran")
        fen.attributes("-fullscreen", True)
        self._canvas_normal = self.canvas
        self._plein_ecran_window = fen
        fen.protocol("WM_DELETE_WINDOW", self.fermer_plein_ecran)
        fen.bind("<Escape>", lambda _ev: self.fermer_plein_ecran())

        barre = ttk.Frame(fen, padding=(8, 5))
        barre.pack(fill="x")
        ttk.Label(barre, text="Glisser le bouton du milieu pour déplacer · Ctrl + molette pour zoomer").pack(side="left")
        ttk.Button(barre, text="Quitter le plein écran  (Échap)",
                   command=self.fermer_plein_ecran).pack(side="right")

        cadre = ttk.Frame(fen)
        cadre.pack(fill="both", expand=True)
        cadre.rowconfigure(0, weight=1)
        cadre.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(cadre, bg=C_FOND, highlightthickness=1,
                                highlightbackground="#D8C89F")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        sbx = ttk.Scrollbar(cadre, orient="horizontal", command=self.canvas.xview)
        sby = ttk.Scrollbar(cadre, orient="vertical", command=self.canvas.yview)
        sbx.grid(row=1, column=0, sticky="ew")
        sby.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=sbx.set, yscrollcommand=sby.set)
        self.canvas.bind("<Button-1>", self.clic)
        self.canvas.bind("<B1-Motion>", self.deplacer)
        self.canvas.bind("<ButtonRelease-1>", self.relacher)
        self.canvas.bind("<Button-3>", self.menu_contextuel)
        self.canvas.bind("<ButtonPress-2>", self.commencer_pan)
        self.canvas.bind("<B2-Motion>", self.deplacer_pan)
        self.canvas.bind("<ButtonRelease-2>", self.fin_pan)
        self.canvas.bind("<Control-MouseWheel>", self.zoom_roulette)
        self.canvas.bind("<MouseWheel>", self.roulette_canvas)
        self.canvas.bind("<Configure>", lambda _ev: self.dessiner())
        fen.update_idletasks()
        self.dessiner()

    def fermer_plein_ecran(self):
        """Ferme la vue plein écran et reprend le canevas de la fenêtre principale."""
        fen = self._plein_ecran_window
        if fen is None:
            return
        self._plein_ecran_window = None
        self.drag = None
        self.drag_emplacement = None
        if self._canvas_normal is not None:
            self.canvas = self._canvas_normal
        self._canvas_normal = None
        try:
            fen.destroy()
        except tk.TclError:
            pass
        self.dessiner()

    def copier_valeur_noeud(self, n):
        """Copie la valeur du nœud sélectionné dans le presse-papiers."""
        self.clipboard_clear()
        self.clipboard_append(str(n.valeur))

    def _donnees_arbre(self, n):
        """Convertit l’arbre en données simples pour l’historique et les fichiers."""
        if n is None:
            return None
        return {"v": n.valeur, "g": self._donnees_arbre(n.gauche),
                "d": self._donnees_arbre(n.droite),
                "c": getattr(n, "couleur_rn", "N")}

    def _creer_depuis_donnees(self, data, profondeur=0, compteur=None):
        """Reconstruit un arbre depuis les données validées."""
        if compteur is None:
            compteur = [0]
        if data is None:
            return None
        if profondeur > 500 or compteur[0] >= 5000:
            raise ValueError("L’arbre dépasse la taille maximale autorisée.")
        if not isinstance(data, dict) or not {"v", "g", "d"}.issubset(data):
            raise ValueError("Structure de nœud invalide dans le fichier.")
        valeur = data["v"]
        if not isinstance(valeur, (int, float, str)) or (
                isinstance(valeur, float) and not math.isfinite(valeur)):
            raise ValueError("Les valeurs des nœuds doivent être des nombres ou du texte.")
        compteur[0] += 1
        n = Noeud(valeur)
        n.couleur_rn = data.get("c", "N") if data.get("c", "N") in ("R", "N") else "N"
        n.gauche = self._creer_depuis_donnees(data["g"], profondeur + 1, compteur)
        n.droite = self._creer_depuis_donnees(data["d"], profondeur + 1, compteur)
        return n

    def _enregistrer_historique(self):
        """Ajoute un point d’annulation lorsqu’une structure d’arbre change."""
        if self._suspendre_historique:
            return
        etat = self._donnees_arbre(self.racine)
        if etat == self.historique[self.historique_index]:
            return
        del self.historique[self.historique_index + 1:]
        self.historique.append(etat)
        self.historique_index = len(self.historique) - 1
        self._maj_boutons_historique()
        self.maj_notations_arbre()

    def _maj_boutons_historique(self):
        if hasattr(self, "btn_annuler"):
            self.btn_annuler.config(state="normal" if self.historique_index > 0 else "disabled")
            self.btn_retablir.config(
                state="normal" if self.historique_index < len(self.historique) - 1 else "disabled")

    def _restaurer_historique(self, index):
        if not 0 <= index < len(self.historique):
            return
        self.historique_index = index
        self._suspendre_historique = True
        try:
            self.racine = self._creer_depuis_donnees(self.historique[index])
        finally:
            self._suspendre_historique = False
        self.selection = None
        self.decalages = {}
        self.decalages_vides = {}
        self._rn_actif = any(getattr(n, "couleur_rn", "N") == "R"
                             for n in noeuds(self.racine))
        self.dessiner()
        self._montrer_code_arbre()
        self._maj_boutons_historique()
        self.maj_notations_arbre()

    def annuler(self):
        """Restaure l’état d’arbre précédent."""
        if self.historique_index > 0:
            self._restaurer_historique(self.historique_index - 1)

    def retablir(self):
        """Restaure l’état d’arbre suivant dans l’historique."""
        if self.historique_index < len(self.historique) - 1:
            self._restaurer_historique(self.historique_index + 1)

    def _arbre_fichier(self, n, chemin="R", disposition=None):
        if n is None:
            return None
        decalage = self.decalages.get(n, (0, 0))
        disposition[chemin] = [decalage[0], decalage[1]]
        return {"v": n.valeur, "g": self._arbre_fichier(n.gauche, chemin + "G", disposition),
                "d": self._arbre_fichier(n.droite, chemin + "D", disposition),
                "c": getattr(n, "couleur_rn", "N")}

    def _noeud_chemin(self, chemin, racine=None):
        if not chemin or chemin[0] != "R":
            return None
        n = self.racine if racine is None else racine
        for direction in chemin[1:]:
            if n is None:
                return None
            n = n.gauche if direction == "G" else n.droite if direction == "D" else None
        return n

    def sauvegarder_arbre(self):
        """Enregistre l’arbre et sa disposition dans un fichier JSON."""
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer l’arbre TreeLab", defaultextension=".json",
            filetypes=(("Arbre TreeLab (JSON)", "*.json"), ("Tous les fichiers", "*.*")))
        if not chemin:
            return
        disposition = {}
        donnees = {"format": "TreeLab", "version": 1,
                   "rouge_noir": getattr(self, "_rn_actif", False),
                   "arbre": self._arbre_fichier(self.racine, disposition=disposition),
                   "disposition": disposition}
        try:
            with open(chemin, "w", encoding="utf-8") as fichier:
                json.dump(donnees, fichier, ensure_ascii=False, indent=2, allow_nan=False)
        except (OSError, TypeError, ValueError) as erreur:
            messagebox.showerror("Enregistrement impossible", str(erreur))

    def ouvrir_arbre(self):
        """Ouvre un arbre TreeLab depuis un fichier JSON."""
        chemin = filedialog.askopenfilename(
            title="Ouvrir un arbre TreeLab",
            filetypes=(("Arbre TreeLab (JSON)", "*.json"), ("Tous les fichiers", "*.*")))
        if not chemin:
            return
        try:
            with open(chemin, "r", encoding="utf-8") as fichier:
                donnees = json.load(fichier)
            if not isinstance(donnees, dict) or donnees.get("format") != "TreeLab" or donnees.get("version") != 1:
                raise ValueError("Ce fichier n’est pas un arbre TreeLab reconnu.")
            nouvelle_racine = self._creer_depuis_donnees(donnees.get("arbre"))
            disposition = donnees.get("disposition", {})
            if not isinstance(disposition, dict):
                raise ValueError("La disposition de l’arbre est invalide.")
            nouveaux_decalages = {}
            for chemin_noeud, xy in disposition.items():
                if not isinstance(chemin_noeud, str) or not isinstance(xy, list) or len(xy) != 2:
                    raise ValueError("Une position de nœud est invalide.")
                if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in xy):
                    raise ValueError("Une position de nœud contient une coordonnée invalide.")
                n = self._noeud_chemin(chemin_noeud, nouvelle_racine)
                if n is not None:
                    nouveaux_decalages[n] = (float(xy[0]), float(xy[1]))
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as erreur:
            messagebox.showerror("Ouverture impossible", str(erreur))
            return
        self.preparer()
        self.racine = nouvelle_racine
        self.decalages = nouveaux_decalages
        self.decalages_vides = {}
        self.selection = None
        self._rn_actif = bool(donnees.get("rouge_noir", False))
        self.dessiner()
        self._montrer_code_arbre()

    def _appliquer_zoom(self, largeur, hauteur):
        """Met à l’échelle les objets, le texte et la zone de défilement du canevas."""
        if abs(self.zoom - 1.0) > 0.001:
            self.canvas.scale("all", 0, 0, self.zoom, self.zoom)
        for item in self.canvas.find_all():
            try:
                texte = self.canvas.itemcget(item, "font")
                if not texte:
                    continue
                police = tkfont.Font(root=self, font=texte)
                actual = police.actual()
                taille = max(1, round(abs(int(actual["size"])) * self.zoom))
                self.canvas.itemconfigure(
                    item, font=(actual["family"], taille, actual["weight"], actual["slant"],
                               actual["underline"], actual["overstrike"]))
            except (tk.TclError, ValueError, TypeError):
                continue
        self.canvas.configure(scrollregion=(0, 0, max(100, int(largeur * self.zoom)),
                                             max(100, int(hauteur * self.zoom))))

    def modifier_zoom(self, facteur, ev=None):
        """Zoome autour du pointeur ou du centre visible du canevas."""
        ancien = self.zoom
        nouveau = max(0.5, min(2.5, ancien * facteur))
        if abs(nouveau - ancien) < 0.001:
            return
        px = ev.x if ev is not None else max(1, self.canvas.winfo_width() // 2)
        py = ev.y if ev is not None else max(1, self.canvas.winfo_height() // 2)
        x = self.canvas.canvasx(px)
        y = self.canvas.canvasy(py)
        self.zoom = nouveau
        self.dessiner()
        self.update_idletasks()
        region = [float(v) for v in self.canvas.cget("scrollregion").split()]
        largeur = max(1.0, region[2] - region[0])
        hauteur = max(1.0, region[3] - region[1])
        self.canvas.xview_moveto(max(0.0, (x * nouveau / ancien - px) / largeur))
        self.canvas.yview_moveto(max(0.0, (y * nouveau / ancien - py) / hauteur))

    def zoom_initial(self):
        self.modifier_zoom(1.0 / self.zoom)

    def zoom_roulette(self, ev):
        self.modifier_zoom(1.15 if ev.delta > 0 else 1 / 1.15, ev)
        return "break"

    def roulette_canvas(self, ev):
        if ev.state & 0x0004:
            return self.zoom_roulette(ev)
        self.canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units")
        return "break"

    def commencer_pan(self, ev):
        self.canvas.scan_mark(ev.x, ev.y)
        self.canvas.config(cursor="fleur")
        return "break"

    def deplacer_pan(self, ev):
        self.canvas.scan_dragto(ev.x, ev.y, gain=1)
        return "break"

    def fin_pan(self, _ev):
        self.canvas.config(cursor="")
        return "break"

    # ==================================================================
    #  CONSTRUCTION
    # ==================================================================

    def creer_racine(self):
        """Crée la racine vide à partir de la valeur saisie par l'utilisateur."""
        self.preparer()
        if self.racine is not None:
            messagebox.showinfo("Racine existante", "L'arbre a déjà une racine "
                                "(videz-le ou modifiez sa valeur).")
            return
        x = self.lire_entier()
        if x is None:
            return
        self.racine = Noeud(x)
        self.selection = self.racine
        self.dessiner()
        self._montrer_code_arbre()

    def ajouter_fils(self, cote):
        """Ajoute un enfant gauche ou droit au nœud actuellement sélectionné."""
        self.preparer()
        if self.racine is None:
            self.creer_racine()
            return
        if not self.exiger_selection():
            return
        p = self.selection
        if getattr(p, cote) is not None:
            messagebox.showinfo("Emplacement occupé",
                                f"Le nœud {p.valeur} a déjà un fils {cote.replace('droite', 'droit')}.")
            return
        x = self.lire_entier()
        if x is None:
            return
        setattr(p, cote, Noeud(x))
        self.dessiner()
        self._montrer_code_arbre()

    def modifier_valeur(self):
        """Remplace la valeur du nœud sélectionné sans modifier ses liens."""
        self.preparer()
        if not self.exiger_selection():
            return
        x = self.lire_entier()
        if x is None:
            return
        self.selection.valeur = x
        self.dessiner()
        self._montrer_code_arbre()

    def supprimer_sous_arbre(self):
        """Détache le nœud sélectionné et libère son sous-arbre par référence."""
        self.preparer()
        if not self.exiger_selection():
            return
        n = self.selection
        nb = taille(n)
        self.remplacer(parent_de(self.racine, n), n, None)
        self.selection = None
        self.dessiner()
        self._montrer_code_arbre()
        self.afficher_resultat("Suppression d'un sous-arbre",
                               [f"{nb} nœud(s) supprimé(s) avec le sous-arbre."])

    def vider(self):
        """Réinitialise l'arbre courant et toutes les informations d'affichage."""
        self.preparer()
        self.racine = None
        self.decalages = {}
        self.decalages_vides = {}
        self.selection = None
        self.sequence = []
        self.maj_sequence()
        self.dessiner()
        self._montrer_code_arbre()

    def inserer_silencieux(self, x):
        """Insère x dans l'ABR courant sans produire d'animation ni de message."""
        if self.racine is None:
            self.racine = Noeud(x)
            return
        n = self.racine
        while True:
            if x == n.valeur:
                return
            cote = "gauche" if x < n.valeur else "droite"
            s = getattr(n, cote)
            if s is None:
                setattr(n, cote, Noeud(x))
                return
            n = s

    def lire_n(self):
        try:
            n = int(self.n_var.get())
        except ValueError:
            n = 10
        return max(1, min(n, 99))

    def generer_abr(self, n):
        """Produit un ABR de n valeurs aléatoires distinctes."""
        self.racine = None
        for v in random.sample(range(1, 100), n):
            self.inserer_silencieux(v)
        self.selection = None

    def generer_quelconque(self, n):
        """Construit un arbre binaire quelconque avec n valeurs générées."""
        vals = random.sample(range(1, 100), n)
        self.racine = Noeud(vals[0])
        for v in vals[1:]:
            libres = [(x, c) for x in noeuds(self.racine) for c in ("gauche", "droite")
                      if getattr(x, c) is None]
            x, c = random.choice(libres)
            setattr(x, c, Noeud(v))
        self.selection = None

    def aleatoire_abr(self):
        self.preparer()
        self.generer_abr(self.lire_n())
        self.dessiner()
        self._montrer_code_arbre()

    def aleatoire_quelconque(self):
        self.preparer()
        self.generer_quelconque(self.lire_n())
        self.dessiner()
        self._montrer_code_arbre()

    def depuis_liste(self):
        """Reconstruit un ABR par insertions successives des valeurs saisies."""
        self.preparer()
        try:
            vals = [int(x) for x in re.findall(r"-?\d+", self.liste_var.get())]
        except ValueError:
            vals = []
        if not vals:
            messagebox.showwarning("Liste vide", "Entrez des entiers séparés par des virgules.")
            return
        self.racine = None
        for v in vals:
            self.inserer_silencieux(v)
        self.selection = None
        self.dessiner()
        self._montrer_code_arbre()
        self.afficher_resultat("ABR construit par insertions successives",
                               [f"Ordre d'insertion : {vals}",
                                f"Hauteur obtenue : {hauteur(self.racine)}",
                                "L'ordre d'insertion change la forme de l'arbre !"])

    def charger_exemple(self):
        """Charge l'exemple choisi dans la liste intégrée aux cours."""
        self.preparer()
        self.decalages = {}
        self.decalages_vides = {}
        genre, data = EXEMPLES[self.exemple_var.get()]
        if genre == "liste":
            self.racine = None
            for v in data:
                self.inserer_silencieux(v)
        else:
            self.racine = depuis_tuple(data)
        self.selection = None
        self.sequence = []
        self.maj_sequence()
        self.dessiner()
        self._montrer_code_arbre()

    def miroir(self):
        """Anime le parcours puis échange les deux enfants de chaque nœud."""
        if not self.exiger_arbre():
            return
        events = []

        def rec(n, d):
            if n is None:
                return
            pad = "   " * d
            events.append(Ev(n, "call", f"{pad}Appel récursif sur le sous-arbre de {n.valeur}"))
            events.append(Ev(n, "enter", f"{pad}Miroir({n.valeur})"))
            rec(n.gauche, d + 1)
            rec(n.droite, d + 1)
            events.append(Ev(n, "visit", f"{pad}échanger les fils de {n.valeur}"))
            events.append(Ev(n, "return", f"{pad}Retour de Miroir({n.valeur})"))
        rec(self.racine, 0)

        def fin():
            for x in noeuds(self.racine):
                x.gauche, x.droite = x.droite, x.gauche
            self._montrer_code_arbre()
            self.afficher_resultat("Miroir", [
                "Les fils gauche et droit de chaque nœud ont été échangés.",
                "Le parcours préfixé du miroir est le parcours « RDG » de l'original.",
                "Attention : un ABR devient un ABR « inversé » (plus un ABR classique)."])
        self.lancer("Miroir", events, fin, "miroir")

    # ==================================================================
    #  PARCOURS
    # ==================================================================

    def parcours(self, ordre, nom, algo, racine_depart=None):
        """Prépare un parcours récursif selon l'ordre donné par les lettres R/G/D."""
        if not self.exiger_arbre():
            return
        depart = self.racine if racine_depart is None else racine_depart
        titre = nom if depart is self.racine else f"{nom} — sous-arbre {depart.valeur}"
        events = []
        details = self.details.get()

        def rec(n, d, parent=None, cote=""):
            pad = "   " * d
            if n is None:
                if details and parent is not None:
                    events.append(Ev(parent, "empty",
                                     f"{pad}sous-arbre {cote} de {parent.valeur} vide (NIL) → retour"))
                return
            events.append(Ev(n, "call", f"{pad}Appel récursif sur le sous-arbre de {n.valeur}"))
            events.append(Ev(n, "enter", f"{pad}{nom.split(' (')[0]}({n.valeur})"))
            for lettre in ordre:
                if lettre == "R":
                    events.append(Ev(n, "visit", f"{pad}   ► TRAITER la racine {n.valeur}", out=n.valeur))
                elif lettre == "G":
                    rec(n.gauche, d + 1, n, "gauche")
                else:
                    rec(n.droite, d + 1, n, "droit")
            events.append(Ev(n, "return", f"{pad}Retour de {nom.split(' (')[0]}({n.valeur})"))
        rec(depart, 0)
        seq = [e.out for e in events if e.out is not None]

        def fin():
            self.afficher_resultat(titre, [
                f"Ordre de visite : {' → '.join(map(str, seq))}",
                "",
                f"Nombre de nœuds visités : {len(seq)}",
            ], "  ".join(map(str, seq)))
        self.lancer(titre, events, fin, algo)

    def parcours_largeur(self, racine_depart=None):
        """Parcourt l'arbre par niveaux à l'aide d'une file FIFO."""
        if not self.exiger_arbre():
            return
        depart = self.racine if racine_depart is None else racine_depart
        titre = "Parcours en largeur" if depart is self.racine else f"Parcours en largeur — sous-arbre {depart.valeur}"
        events = []
        file = [depart]
        niv = {depart: 0}
        while file:
            n = file.pop(0)
            ajouts = [f for f in (n.gauche, n.droite) if f is not None]
            for f in ajouts:
                niv[f] = niv[n] + 1
            file.extend(ajouts)
            events.append(Ev(n, "visit",
                             f"Défiler {n.valeur} (niveau {niv[n]}) → traité ; "
                             f"enfiler {[f.valeur for f in ajouts]} ; "
                             f"file = {[x.valeur for x in file]}", out=n.valeur))
        seq = [e.out for e in events]

        def fin():
            lignes = [f"Ordre de visite : {' → '.join(map(str, seq))}", ""]
            for k, lv in enumerate(niveaux(depart)):
                lignes.append(f"Niveau {k} : {[x.valeur for x in lv]}")
            self.afficher_resultat(titre, lignes, "  ".join(map(str, seq)))
        self.lancer(titre, events, fin, "largeur")

    def tous_parcours(self):
        """Affiche les quatre parcours en profondeur et le parcours en largeur."""
        if not self.exiger_arbre():
            return
        self.preparer()
        lignes = []
        for nom, ordre in (("Préfixé  (RGD)", "RGD"), ("Infixé   (GRD)", "GRD"),
                           ("Postfixé (GDR)", "GDR"), ("Inversé  (DRG)", "DRG")):
            lignes.append(f"{nom} : {valeurs(self.racine, ordre)}")
        lignes.append("Largeur         : " +
                      str([x.valeur for lv in niveaux(self.racine) for x in lv]))
        lignes.append("")
        if est_abr(self.racine):
            lignes.append("L'arbre est un ABR : le parcours infixé est trié (croissant),")
            lignes.append("et le parcours infixé inversé est décroissant.")
        self.afficher_resultat("Les cinq parcours", lignes)
        self.res_notebook.select(self.tab_res)
        self.dessiner()

    # ==================================================================
    #  MESURES  (« fold » récursif animé)
    # ==================================================================

    def fold(self, titre, vide, combiner, message, final, algo, kind=None):
        """Factorise les mesures récursives en calculant puis combinant les résultats.

        vide est la valeur d'un sous-arbre nul ; combiner calcule la valeur d'un
        nœud à partir de ses deux enfants ; message produit l'explication affichée.
        """
        if not self.exiger_arbre():
            return
        events = []
        details = self.details.get()

        def rec(n, d, parent=None, cote=""):
            pad = "   " * d
            if n is None:
                if details and parent is not None:
                    events.append(Ev(parent, "empty",
                                     f"{pad}sous-arbre {cote} vide → {fmt(vide)}"))
                return vide
            events.append(Ev(n, "call", f"{pad}Appel récursif sur le sous-arbre de {n.valeur}"))
            events.append(Ev(n, "enter", f"{pad}appel sur le nœud {n.valeur}"))
            vg = rec(n.gauche, d + 1, n, "gauche")
            vd = rec(n.droite, d + 1, n, "droit")
            r = combiner(n, vg, vd)
            k = kind(n) if kind else "visit"
            events.append(Ev(n, k, f"{pad}{message(n, vg, vd, r)}"))
            events.append(Ev(n, "return", f"{pad}Retour de l’appel sur {n.valeur}"))
            return r
        res = rec(self.racine, 0)
        self.lancer(titre, events, lambda: final(res), algo)

    def op_nb_noeuds(self):
        self.fold("Nombre de nœuds", 0, lambda n, g, d: 1 + g + d,
                  lambda n, g, d, r: f"N({n.valeur}) = 1 + {g} + {d} = {r}",
                  lambda r: self.afficher_resultat("Nombre de nœuds", [
                      "N(A) = 0                          si A est vide",
                      "N(A) = 1 + N(gauche) + N(droit)   sinon"], f"{r} nœud(s)"),
                  "nb_noeuds")

    def op_feuilles(self):
        def comb(n, g, d):
            return 1 if est_feuille(n) else g + d

        def msg(n, g, d, r):
            return (f"{n.valeur} est une FEUILLE → 1" if est_feuille(n)
                    else f"F({n.valeur}) = {g} + {d} = {r}")
        self.fold("Nombre de feuilles", 0, comb, msg,
                  lambda r: self.afficher_resultat("Nombre de feuilles", [
                      "Une feuille = nœud sans fils (gauche = droit = NIL)."], f"{r} feuille(s)"),
                  "feuilles", kind=lambda n: "visit" if est_feuille(n) else "skip")

    def op_internes(self):
        def comb(n, g, d):
            return 0 if est_feuille(n) else 1 + g + d

        def msg(n, g, d, r):
            return (f"{n.valeur} est une feuille → 0" if est_feuille(n)
                    else f"I({n.valeur}) = 1 + {g} + {d} = {r}")

        def fin(r):
            self.afficher_resultat("Nœuds internes", [
                f"Nœuds internes = nœuds − feuilles = {taille(self.racine)} − "
                f"{nb_feuilles(self.racine)} = {r}"], f"{r} nœud(s) interne(s)")
        self.fold("Nombre de nœuds internes", 0, comb, msg, fin, "internes",
                  kind=lambda n: "skip" if est_feuille(n) else "visit")

    def op_un_fils(self):
        self.fold("Nœuds à un seul fils", 0,
                  lambda n, g, d: (1 if nb_fils(n) == 1 else 0) + g + d,
                  lambda n, g, d, r: f"{n.valeur} a {nb_fils(n)} fils → cumul = {r}",
                  lambda r: self.afficher_resultat("Nœuds à un seul fils", [
                      "Un arbre sans aucun nœud à un fils est « localement complet »."],
                      f"{r} nœud(s)"),
                  "un_fils", kind=lambda n: "visit" if nb_fils(n) == 1 else "skip")

    def op_deux_fils(self):
        def fin(r):
            self.afficher_resultat("Nœuds à deux fils", [
                f"Vérification : feuilles = nœuds à 2 fils + 1  →  "
                f"{nb_feuilles(self.racine)} = {r} + 1"], f"{r} nœud(s)")
        self.fold("Nœuds à deux fils", 0,
                  lambda n, g, d: (1 if nb_fils(n) == 2 else 0) + g + d,
                  lambda n, g, d, r: f"{n.valeur} a {nb_fils(n)} fils → cumul = {r}",
                  fin, "deux_fils", kind=lambda n: "visit" if nb_fils(n) == 2 else "skip")

    def op_hauteur(self):
        def fin(r):
            n = taille(self.racine)
            self.afficher_resultat("Hauteur de l'arbre", [
                f"Hauteur (en arêtes, feuille = 0) : {r}",
                f"Nombre de niveaux : {r + 1}   (hauteur en nœuds si feuille = 1)",
                "",
                f"Pour n = {n} nœuds :  ⌊log2 n⌋ = {n.bit_length() - 1}  ≤  h  ≤  n − 1 = {n - 1}",
            ], f"h = {r}")
        self.fold("Hauteur", -1, lambda n, g, d: 1 + max(g, d),
                  lambda n, g, d, r: f"h({n.valeur}) = 1 + max({g}, {d}) = {r}", fin, "hauteur")

    def op_somme(self):
        self.fold("Somme des valeurs", 0, lambda n, g, d: n.valeur + g + d,
                  lambda n, g, d, r: f"S({n.valeur}) = {n.valeur} + {g} + {d} = {r}",
                  lambda r: self.afficher_resultat("Somme", [
                      "S(A) = 0 si A est vide ; sinon valeur + S(gauche) + S(droit)"], f"Somme = {r}"),
                  "somme")

    def op_moyenne(self):
        def fin(r):
            s, c = r
            self.afficher_resultat("Moyenne", [
                f"Somme = {s}", f"Nombre de nœuds = {c}",
                f"Moyenne = {s} / {c}"], f"Moyenne = {fmt(s / c)}")
        self.fold("Moyenne des valeurs", (0, 0),
                  lambda n, g, d: (n.valeur + g[0] + d[0], 1 + g[1] + d[1]),
                  lambda n, g, d, r: f"({n.valeur}) → somme = {r[0]}, nombre = {r[1]}",
                  fin, "somme")

    def _extreme(self, nom, f, algo):
        def fin(r):
            for x in noeuds(self.racine):
                if x.valeur == r:
                    self.marques[x] = "found"
            self.afficher_resultat(nom, [
                "Dans un arbre quelconque, il faut examiner TOUS les nœuds.",
                "Dans un ABR : descendre à gauche (min) ou à droite (max)."], f"{nom} = {r}")
        self.fold(nom, None, lambda n, g, d: f([x for x in (n.valeur, g, d) if x is not None]),
                  lambda n, g, d, r: f"{nom[:3].lower()}({n.valeur}, {fmt(g)}, {fmt(d)}) = {r}",
                  fin, algo)

    def op_min(self):
        self._extreme("Minimum", min, "min")

    def op_max(self):
        self._extreme("Maximum", max, "max")

    def op_occurrences(self):
        x = self.lire_entier()
        if x is None:
            return
        self.fold(f"Occurrences de {x}", 0,
                  lambda n, g, d: (1 if n.valeur == x else 0) + g + d,
                  lambda n, g, d, r: f"{n.valeur} {'=' if n.valeur == x else '≠'} {x} → cumul = {r}",
                  lambda r: self.afficher_resultat(f"Occurrences de {x}", [], f"{r} occurrence(s)"),
                  "occurrences", kind=lambda n: "found" if n.valeur == x else "skip")

    def op_parite(self):
        def fin(r):
            self.afficher_resultat("Valeurs paires / impaires", [
                f"Paires : {r[0]}", f"Impaires : {r[1]}"],
                f"{r[0]} paire(s), {r[1]} impaire(s)")
        self.fold("Valeurs paires / impaires", (0, 0),
                  lambda n, g, d: ((1 if n.valeur % 2 == 0 else 0) + g[0] + d[0],
                                   (1 if n.valeur % 2 != 0 else 0) + g[1] + d[1]),
                  lambda n, g, d, r: f"{n.valeur} est {'pair' if n.valeur % 2 == 0 else 'impair'} → "
                                     f"(pairs, impairs) = {r}",
                  fin, "parite", kind=lambda n: "visit" if n.valeur % 2 == 0 else "skip")

    def op_nb_pairs(self):
        """Compte séparément les valeurs paires et anime le cumul récursif."""
        self.fold("Nombre de valeurs paires", 0,
                  lambda n, g, d: (1 if n.valeur % 2 == 0 else 0) + g + d,
                  lambda n, g, d, r: f"{n.valeur} est {'pair' if n.valeur % 2 == 0 else 'impair'} → cumul pair = {r}",
                  lambda r: self.afficher_resultat("Nombre de valeurs paires", [
                      "Une valeur est paire si elle est divisible par 2.",
                      "Les occurrences répétées sont comptées séparément."], f"{r} valeur(s) paire(s)"),
                  "parite", kind=lambda n: "found" if n.valeur % 2 == 0 else "skip")

    def op_paires(self):
        """Recherche toutes les valeurs paires en parcourant l'arbre."""
        def combiner(n, g, d):
            return ([n.valeur] if n.valeur % 2 == 0 else []) + g + d

        def message(n, g, d, r):
            decision = "ajoutée à la liste" if n.valeur % 2 == 0 else "ignorée"
            return f"{n.valeur} est {'pair' if n.valeur % 2 == 0 else 'impair'} → {decision} ; cumul = {r}"

        def fin(r):
            self.afficher_resultat("Valeurs paires", [
                "Parcours préfixé : les valeurs sont listées dans l'ordre de visite.",
                f"Nombre de valeurs paires : {len(r)}"], f"Paires : {r}")

        self.fold("Recherche des valeurs paires", [], combiner, message, fin, "parite",
                  kind=lambda n: "found" if n.valeur % 2 == 0 else "skip")

    def op_nb_premiers(self):
        """Compte les nombres premiers contenus dans les nœuds de l'arbre."""
        self.fold("Nombre de nombres premiers", 0,
                  lambda n, g, d: (1 if est_premier(n.valeur) else 0) + g + d,
                  lambda n, g, d, r: f"{n.valeur} {'est premier' if est_premier(n.valeur) else 'n’est pas premier'} → cumul = {r}",
                  lambda r: self.afficher_resultat("Nombre de nombres premiers", [
                      "Un nombre premier est un entier supérieur à 1 qui n'a que deux diviseurs positifs : 1 et lui-même.",
                      "Les valeurs répétées sont comptées à chaque nœud."], f"{r} nombre(s) premier(s)"),
                  "premiers", kind=lambda n: "found" if est_premier(n.valeur) else "skip")

    def op_premiers(self):
        """Recherche et liste les nombres premiers de l'arbre."""
        def combiner(n, g, d):
            return ([n.valeur] if est_premier(n.valeur) else []) + g + d

        def message(n, g, d, r):
            decision = "ajoutée à la liste" if est_premier(n.valeur) else "ignorée"
            return f"{n.valeur} {'est premier' if est_premier(n.valeur) else 'n’est pas premier'} → {decision} ; cumul = {r}"

        def fin(r):
            self.afficher_resultat("Nombres premiers", [
                "Les valeurs sont affichées dans l'ordre préfixé de l'arbre.",
                f"Nombre de nombres premiers : {len(r)}"], f"Premiers : {r}")

        self.fold("Recherche des nombres premiers", [], combiner, message, fin, "premiers",
                  kind=lambda n: "found" if est_premier(n.valeur) else "skip")

    def op_multiples(self):
        """Filtre et liste les valeurs divisibles par x, sans division par zéro."""
        x = self.lire_entier()
        if x is None:
            return
        if x == 0:
            messagebox.showwarning("Diviseur invalide", "Saisissez une valeur non nulle pour rechercher ses multiples.")
            return

        def combiner(n, g, d):
            return ([n.valeur] if n.valeur % x == 0 else []) + g + d

        def fin(r):
            self.afficher_resultat(f"Multiples de {x}", [
                f"Critère : valeur MOD {x} = 0.",
                f"Nombre trouvé : {len(r)}"], f"Multiples : {r}")

        self.fold(f"Recherche des multiples de {x}", [], combiner,
                  lambda n, g, d, r: f"{n.valeur} {'est' if n.valeur % x == 0 else 'n’est pas'} divisible par {x} → cumul = {r}",
                  fin, "parite", kind=lambda n: "found" if n.valeur % x == 0 else "skip")

    def op_largeur(self):
        if not self.exiger_arbre():
            return
        events = []
        niv = niveaux(self.racine)
        for k, lv in enumerate(niv):
            for i, x in enumerate(lv, 1):
                events.append(Ev(x, "visit", f"niveau {k} : nœud {x.valeur} (compteur du niveau = {i})"))
        larg = max(len(lv) for lv in niv)

        def fin():
            lignes = [f"Niveau {k} : {len(lv)} nœud(s)  (max possible 2^{k} = {2 ** k})"
                      for k, lv in enumerate(niv)]
            self.afficher_resultat("Largeur de l'arbre", lignes,
                                   f"Largeur = {larg}")
        self.lancer("Largeur (nœuds par niveau)", events, fin, "largeur_niv")

    def op_recherche(self):
        """Recherche une valeur dans un arbre quelconque en explorant les deux fils."""
        if not self.exiger_arbre():
            return
        x = self.lire_entier()
        if x is None:
            return
        events = []

        def rec(n, d):
            if n is None:
                return None
            pad = "   " * d
            events.append(Ev(n, "call", f"{pad}Appel récursif sur le sous-arbre de {n.valeur}"))
            if n.valeur == x:
                events.append(Ev(n, "found", f"{pad}{n.valeur} = {x} → TROUVÉ"))
                events.append(Ev(n, "return", f"{pad}Retour de recherche({n.valeur})"))
                return n
            events.append(Ev(n, "enter", f"{pad}{n.valeur} ≠ {x} → chercher à gauche puis à droite"))
            r = rec(n.gauche, d + 1)
            if r:
                events.append(Ev(n, "return", f"{pad}Retour de recherche({n.valeur}) avec le résultat trouvé"))
                return r
            r = rec(n.droite, d + 1)
            events.append(Ev(n, "return", f"{pad}Retour de recherche({n.valeur})"))
            return r
        r = rec(self.racine, 0)
        comparaisons = len(events)

        def fin():
            if r:
                ch = chemin_vers(self.racine, r)
                self.afficher_resultat(f"Recherche de {x}", [
                    f"Trouvé ! Chemin depuis la racine : {[p.valeur for p in ch]}",
                    f"Niveau du nœud : {len(ch) - 1}",
                    f"Comparaisons : {comparaisons}"], "TROUVÉ")
            else:
                self.afficher_resultat(f"Recherche de {x}", [
                    f"Les {comparaisons} nœuds ont été examinés : {x} est absent."], "ABSENT")
        self.lancer(f"Recherche de {x}", events, fin, "recherche")

    def infos_noeud(self):
        if not self.exiger_arbre() or not self.exiger_selection():
            return
        n = self.selection
        ch = chemin_vers(self.racine, n)
        events = [Ev(p, "path", f"{'   ' * i}{p.valeur}") for i, p in enumerate(ch)]
        p = ch[-2] if len(ch) >= 2 else None
        frere = None
        if p is not None:
            frere = p.droite if p.gauche is n else p.gauche

        def fin():
            nature = ("racine" if p is None else "") + \
                     (" + " if p is None and est_feuille(n) else "") + \
                     ("feuille" if est_feuille(n) else ("" if p is None else "nœud interne"))
            self.afficher_resultat(f"Infos sur le nœud {n.valeur}", [
                f"Nature : {nature or 'nœud interne'}",
                f"Père : {p.valeur if p else '—'}",
                f"Fils gauche : {n.gauche.valeur if n.gauche else '—'}   "
                f"Fils droit : {n.droite.valeur if n.droite else '—'}",
                f"Frère : {frere.valeur if frere else '—'}",
                f"Degré (nombre de fils) : {nb_fils(n)}",
                f"Niveau = profondeur : {len(ch) - 1}",
                f"Hauteur du nœud : {hauteur(n)}",
                f"Ancêtres : {[a.valeur for a in ch[:-1]]}",
                f"Descendants : {taille(n) - 1}  (taille du sous-arbre : {taille(n)})",
                f"Chemin racine → nœud : {' → '.join(str(a.valeur) for a in ch)}"])
        self.lancer(f"Chemin racine → {n.valeur}", events, fin, "infos")

    # ==================================================================
    #  TESTS DE PROPRIÉTÉS
    # ==================================================================

    def test_local(self, titre, cond, algo, phrase_ok, phrase_ko):
        """Évalue une propriété nœud par nœud et mémorise les contre-exemples."""
        if not self.exiger_arbre():
            return
        events, mauvais = [], []

        def rec(n, d):
            if n is None:
                return
            pad = "   " * d
            events.append(Ev(n, "call", f"{pad}Appel récursif sur le sous-arbre de {n.valeur}"))
            events.append(Ev(n, "enter", f"{pad}examiner {n.valeur}"))
            rec(n.gauche, d + 1)
            rec(n.droite, d + 1)
            ok, msg = cond(n)
            events.append(Ev(n, "visit" if ok else "bad", f"{pad}{msg}"))
            if not ok:
                mauvais.append(n)
            events.append(Ev(n, "return", f"{pad}Retour de vérification({n.valeur})"))
        rec(self.racine, 0)

        def fin():
            if mauvais:
                self.afficher_resultat(titre, [
                    (f"NON : {phrase_ko}", "ko"),
                    f"Nœud(s) fautif(s) : {[x.valeur for x in mauvais]}"], "NON ✗")
            else:
                self.afficher_resultat(titre, [(f"OUI : {phrase_ok}", "ok")], "OUI ✓")
        self.lancer(titre, events, fin, algo)

    def test_strict(self):
        self.test_local("Arbre localement complet ?",
                        lambda n: (nb_fils(n) != 1,
                                   f"{n.valeur} a {nb_fils(n)} fils → "
                                   f"{'OK' if nb_fils(n) != 1 else 'ERREUR (1 seul fils)'}"),
                        "strict", "tout nœud a 0 ou 2 fils.",
                        "certains nœuds n'ont qu'un seul fils.")

    def test_degenere(self):
        self.test_local("Arbre dégénéré ?",
                        lambda n: (nb_fils(n) <= 1,
                                   f"{n.valeur} a {nb_fils(n)} fils → "
                                   f"{'OK' if nb_fils(n) <= 1 else 'ERREUR (2 fils)'}"),
                        "degenere", "chaque nœud a au plus un fils (hauteur = n − 1).",
                        "certains nœuds ont deux fils.")

    def test_equilibre(self):
        def cond(n):
            hg, hd = hauteur(n.gauche), hauteur(n.droite)
            ok = abs(hg - hd) <= 1
            return ok, f"{n.valeur} : h(G) = {hg}, h(D) = {hd}, écart = {abs(hg - hd)} → " \
                       f"{'OK' if ok else 'DÉSÉQUILIBRÉ'}"
        self.test_local("Arbre équilibré (AVL) ?", cond, "equilibre",
                        "l'écart de hauteur est ≤ 1 en chaque nœud.",
                        "au moins un nœud a un écart de hauteur > 1.")

    def test_parfait(self):
        if not self.exiger_arbre():
            return
        niv = niveaux(self.racine)
        events, ok = [], True
        for k, lv in enumerate(niv):
            plein = len(lv) == 2 ** k
            ok = ok and plein
            for x in lv:
                events.append(Ev(x, "visit" if plein else "bad",
                                 f"niveau {k} : {len(lv)} nœud(s) pour {2 ** k} possible(s) → "
                                 f"{'plein' if plein else 'INCOMPLET'}"))

        def fin():
            n, h = taille(self.racine), hauteur(self.racine)
            lignes = [f"n = {n}, h = {h} → 2^(h+1) − 1 = {2 ** (h + 1) - 1}"]
            lignes.append(("OUI : tous les niveaux sont pleins." if ok else
                           "NON : au moins un niveau n'est pas plein.", "ok" if ok else "ko"))
            self.afficher_resultat("Arbre parfait ?", lignes, "OUI ✓" if ok else "NON ✗")
        self.lancer("Arbre parfait ?", events, fin, "parfait")

    def test_complet(self):
        if not self.exiger_arbre():
            return
        events = []
        file = [(self.racine, None, "")]
        vu_vide, ok = False, True
        while file:
            n, p, c = file.pop(0)
            if n is None:
                if not vu_vide:
                    vu_vide = True
                    events.append(Ev(p, "empty", f"emplacement vide ({c} de {p.valeur}) : "
                                                 f"plus aucun nœud ne doit suivre"))
            else:
                if vu_vide:
                    ok = False
                    events.append(Ev(n, "bad", f"{n.valeur} apparaît APRÈS un emplacement vide ✗"))
                else:
                    events.append(Ev(n, "visit", f"{n.valeur} ✓"))
                file.append((n.gauche, n, "gauche"))
                file.append((n.droite, n, "droit"))

        def fin():
            self.afficher_resultat("Arbre complet ?", [
                ("OUI : niveaux pleins sauf le dernier, rempli de gauche à droite." if ok else
                 "NON : un nœud apparaît après un emplacement vide (parcours en largeur).",
                 "ok" if ok else "ko")], "OUI ✓" if ok else "NON ✗")
        self.lancer("Arbre complet ?", events, fin, "complet")

    def test_abr(self):
        """Vérifie si le parcours infixé est strictement croissant."""
        if not self.exiger_arbre():
            return
        liste = noeuds(self.racine, "GRD")
        events, ok, mauvais = [], True, []
        for i, x in enumerate(liste):
            if i > 0 and not liste[i - 1].valeur < x.valeur:
                ok = False
                mauvais.append(x)
                events.append(Ev(x, "bad", f"{liste[i - 1].valeur} ≥ {x.valeur} ✗ (pas croissant)",
                                 out=x.valeur))
            else:
                events.append(Ev(x, "visit", f"{x.valeur} (précédent : "
                                             f"{liste[i - 1].valeur if i else '—'}) ✓", out=x.valeur))

        def fin():
            seq = [x.valeur for x in liste]
            self.afficher_resultat("Est-ce un ABR ?", [
                f"Parcours infixé : {seq}",
                ("OUI : strictement croissant → c'est un ABR." if ok else
                 f"NON : l'ordre est rompu en {[m.valeur for m in mauvais]}.", "ok" if ok else "ko")],
                "OUI ✓" if ok else "NON ✗")
        self.lancer("Parcours infixé (test ABR)", events, fin, "est_abr")

    def diagnostic(self):
        """Rassemble les principales propriétés de forme et d'ordre de l'arbre."""
        if not self.exiger_arbre():
            return
        self.preparer()
        r = self.racine
        n, h, f = taille(r), hauteur(r), nb_feuilles(r)
        niv = niveaux(r)
        v = valeurs(r)

        def oui(b):
            return ("OUI ✓", "ok") if b else ("NON ✗", "ko")
        lignes = [
            "— MESURES —",
            f"Nombre de nœuds        : {n}",
            f"Nombre de feuilles     : {f}",
            f"Nœuds internes         : {n - f}",
            f"  dont à 1 fils        : {sum(1 for x in noeuds(r) if nb_fils(x) == 1)}",
            f"  dont à 2 fils        : {sum(1 for x in noeuds(r) if nb_fils(x) == 2)}",
            f"Hauteur (feuille = 0)  : {h}   ({h + 1} niveaux)",
            f"Largeur maximale       : {max(len(lv) for lv in niv)}",
            f"Somme / Moyenne        : {sum(v)} / {fmt(sum(v) / n)}",
            f"Minimum / Maximum      : {min(v)} / {max(v)}",
            "",
            "— PARCOURS —",
            f"Préfixé  (RGD) : {valeurs(r, 'RGD')}",
            f"Infixé   (GRD) : {valeurs(r, 'GRD')}",
            f"Postfixé (GDR) : {valeurs(r, 'GDR')}",
            f"Largeur        : {[x.valeur for lv in niv for x in lv]}",
            "",
            "— PROPRIÉTÉS —",
        ]
        self.vider_texte(self.txt_res)
        self.ecrire(self.txt_res, "Diagnostic complet\n", "titre")
        for l in lignes:
            self.ecrire(self.txt_res, l + "\n")
        for nom, b in (("ABR", est_abr(r)), ("Localement complet", est_strict(r)),
                       ("Parfait", est_parfait(r)), ("Complet (tas)", est_presque_complet(r)),
                       ("Dégénéré", est_degenere(r)), ("Équilibré (AVL)", est_equilibre(r))):
            t, tag = oui(b)
            self.ecrire(self.txt_res, f"{nom:<20}: ")
            self.ecrire(self.txt_res, t + "\n", tag)
        self.txt_res.see("1.0")
        self.res_notebook.select(self.tab_res)
        self.dessiner()

    # ==================================================================
    #  OPÉRATIONS SUR ABR
    # ==================================================================

    def insertion_guidee(self):
        """Montre les comparaisons successives qui déterminent une insertion ABR."""
        """Active l'animation et la pause après chaque comparaison ABR."""
        self.animer.set(True)
        self.pas_a_pas.set(True)
        self.inserer_abr()

    def verifier_invariants(self):
        """Vérifie les règles ABR et, si applicable, les propriétés rouge-noir."""
        if not self.exiger_arbre():
            return
        events, fautifs = [], []

        def verifier_abr(n, bas=None, haut=None):
            if n is None:
                return True
            ok = (bas is None or bas < n.valeur) and (haut is None or n.valeur < haut)
            events.append(Ev(n, "visit" if ok else "bad",
                             f"ABR : {bas if bas is not None else '−∞'} < {n.valeur} < "
                             f"{haut if haut is not None else '+∞'} → {'OK' if ok else 'VIOLATION'}"))
            if not ok:
                fautifs.append(n)
            gauche_ok = verifier_abr(n.gauche, bas, n.valeur)
            droite_ok = verifier_abr(n.droite, n.valeur, haut)
            return ok and gauche_ok and droite_ok

        ok_abr = verifier_abr(self.racine)
        est_rn = getattr(self, "_rn_actif", False)
        rb_fautifs = []
        ok_rn = None
        if est_rn:
            def verifier_rn(n, chemin_noir=0):
                if n is None:
                    return chemin_noir + 1
                noir = chemin_noir + (1 if n.couleur_rn == "N" else 0)
                local_ok = True
                if n is self.racine and n.couleur_rn != "N":
                    local_ok = False
                    events.append(Ev(n, "bad", "Rouge-noir : la racine doit être noire."))
                if n.couleur_rn == "R" and any(f is not None and f.couleur_rn == "R"
                                                 for f in (n.gauche, n.droite)):
                    local_ok = False
                    events.append(Ev(n, "bad", f"Rouge-noir : {n.valeur} rouge a un enfant rouge."))
                if not local_ok:
                    rb_fautifs.append(n)
                hg = verifier_rn(n.gauche, noir)
                hd = verifier_rn(n.droite, noir)
                if hg != hd:
                    rb_fautifs.append(n)
                    events.append(Ev(n, "bad", f"Rouge-noir : chemins noirs différents sous {n.valeur} ({hg} ≠ {hd})."))
                elif local_ok:
                    events.append(Ev(n, "visit", f"Rouge-noir : {n.valeur} ({'noir' if n.couleur_rn == 'N' else 'rouge'}), hauteur noire {hg} → OK"))
                return min(hg, hd)
            ok_rn = verifier_rn(self.racine)

        def fin():
            lignes = [("ABR : ordre strict respecté." if ok_abr else
                       f"ABR : ordre violé sur {[n.valeur for n in fautifs]}.", "ok" if ok_abr else "ko")]
            if est_rn:
                lignes += [("Rouge-noir : racine noire, pas de rouge consécutif et même hauteur noire." if not rb_fautifs else
                            f"Rouge-noir : invariants violés sur {[n.valeur for n in rb_fautifs]}.",
                            "ok" if not rb_fautifs else "ko")]
            else:
                lignes.append("Rouge-noir : non applicable — utilisez « Générer un rouge-noir » pour créer un arbre étiqueté.")
            self.afficher_resultat("Vérification des invariants", lignes)
        self.lancer("Vérification ABR / rouge-noir", events, fin, "test_abr")

    def inserer_abr(self):
        """Insère une valeur en suivant les comparaisons de l'ABR, avec animation."""
        x = self.lire_entier()
        if x is None:
            return
        self.preparer()
        if self.racine is None:
            self.racine = Noeud(x)
            self.marques[self.racine] = "found"
            self.dessiner()
            self._montrer_code_arbre()
            self.afficher_resultat("Insertion", [f"{x} devient la racine de l'arbre vide."])
            return
        events, cible, n, d = [], None, self.racine, 0
        while True:
            pad = "   " * d
            if x == n.valeur:
                events.append(Ev(n, "bad", f"{pad}{x} = {n.valeur} → déjà présent : pas d'insertion"))
                break
            cote = "gauche" if x < n.valeur else "droite"
            signe = "<" if x < n.valeur else ">"
            suivant = getattr(n, cote)
            if suivant is None:
                events.append(Ev(n, "enter", f"{pad}{x} {signe} {n.valeur} et pas de fils {cote} "
                                             f"→ INSÉRER ICI"))
                cible = (n, cote)
                break
            events.append(Ev(n, "enter", f"{pad}{x} {signe} {n.valeur} → aller à {cote}"))
            n, d = suivant, d + 1

        def fin():
            if cible:
                nouveau = Noeud(x)
                setattr(cible[0], cible[1], nouveau)
                self.marques[nouveau] = "found"
                self._montrer_code_arbre()
                self.afficher_resultat("Insertion dans un ABR", [
                    f"{x} inséré comme fils {cible[1].replace('droite', 'droit')} de {cible[0].valeur}.",
                    f"Une nouvelle valeur est toujours insérée comme FEUILLE.",
                    f"Nouvelle hauteur : {hauteur(self.racine)}"])
            else:
                self.afficher_resultat("Insertion dans un ABR", [f"{x} existe déjà : rien à faire."])
        self.lancer(f"Insertion de {x}", events, fin, "insertion")

    def supprimer_abr(self, x=None):
        """Supprime une valeur d'ABR en traitant séparément 0, 1 ou 2 enfants."""
        if x is None:
            x = self.lire_entier()
        if x is None:
            return
        if not self.exiger_arbre():
            return
        self.preparer()
        events, parent, n = [], None, self.racine
        while n is not None and n.valeur != x:
            cote = "gauche" if x < n.valeur else "droite"
            signe = "<" if x < n.valeur else ">"
            events.append(Ev(n, "enter", f"{x} {signe} {n.valeur} → aller à {cote}"))
            parent, n = n, getattr(n, cote)
        if n is None:
            events.append(Ev(parent, "empty", f"{x} est absent de l'arbre : rien à supprimer"))
            self.lancer(f"Suppression de {x}", events, lambda: self.afficher_resultat(
                "Suppression dans un ABR", [f"{x} est absent."]), "suppression")
            return
        cible, k = n, nb_fils(n)
        s = sp = None
        if k == 0:
            events.append(Ev(n, "bad", f"{x} trouvé : c'est une FEUILLE → on la retire simplement"))
        elif k == 1:
            events.append(Ev(n, "bad", f"{x} trouvé : UN seul fils → le fils prend sa place"))
        else:
            events.append(Ev(n, "bad", f"{x} trouvé : DEUX fils → on le remplace par son "
                                       f"successeur infixé (min du sous-arbre droit)"))
            sp, s = n, n.droite
            events.append(Ev(s, "enter", "aller à droite"))
            while s.gauche is not None:
                sp, s = s, s.gauche
                events.append(Ev(s, "enter", "puis à gauche tant que possible"))
            events.append(Ev(s, "found", f"successeur = {s.valeur} : sa valeur remplace {x}"))

        def fin():
            if k == 0:
                self.remplacer(parent, cible, None)
                txt = "Feuille supprimée."
            elif k == 1:
                self.remplacer(parent, cible, cible.gauche if cible.gauche else cible.droite)
                txt = "Nœud à un fils supprimé : son fils le remplace."
            else:
                cible.valeur = s.valeur
                if sp is cible:
                    cible.droite = s.droite
                else:
                    sp.gauche = s.droite
                self.marques[cible] = "found"
                txt = f"Nœud à deux fils : sa valeur est remplacée par {s.valeur}, " \
                      f"puis l'ancien nœud {s.valeur} est supprimé."
            self.selection = None
            self._montrer_code_arbre()
            self.afficher_resultat("Suppression dans un ABR", [
                f"Suppression de {x} : cas à {k} fils.", txt,
                f"L'arbre reste un ABR. Nouvelle hauteur : {hauteur(self.racine)}"])
        self.lancer(f"Suppression de {x}", events, fin, "suppression")

    def chercher_abr(self):
        """Recherche une valeur dans un ABR en éliminant un sous-arbre par étape."""
        if not self.exiger_arbre():
            return
        x = self.lire_entier()
        if x is None:
            return
        events, n, dernier, trouve = [], self.racine, None, None
        while n is not None:
            dernier = n
            if x == n.valeur:
                events.append(Ev(n, "found", f"{x} = {n.valeur} → TROUVÉ"))
                trouve = n
                break
            cote = "gauche" if x < n.valeur else "droite"
            signe = "<" if x < n.valeur else ">"
            events.append(Ev(n, "enter", f"{x} {signe} {n.valeur} → aller à {cote}"))
            n = getattr(n, cote)
        if trouve is None:
            events.append(Ev(dernier, "empty", f"sous-arbre vide atteint → {x} est ABSENT"))
        comp = sum(1 for e in events if e.kind in ("enter", "found"))

        def fin():
            h = hauteur(self.racine)
            self.afficher_resultat(f"Recherche de {x} dans l'ABR", [
                f"Comparaisons effectuées : {comp}",
                f"Hauteur de l'arbre : {h}  (maximum {h + 1} comparaisons)",
                "Un ABR équilibré donne O(log n), un ABR dégénéré O(n)."],
                "TROUVÉ" if trouve else "ABSENT")
        self.lancer(f"Recherche de {x} (ABR)", events, fin, "recherche_abr")

    def extreme_abr(self, quoi):
        if not self.exiger_arbre():
            return
        cote = "gauche" if quoi == "min" else "droite"
        mot = "Minimum" if quoi == "min" else "Maximum"
        events, n = [], self.racine
        while True:
            suivant = getattr(n, cote)
            if suivant is None:
                events.append(Ev(n, "found", f"{n.valeur} n'a pas de fils {cote.replace('droite', 'droit')} "
                                             f"→ c'est le {mot.lower()}"))
                break
            events.append(Ev(n, "enter", f"{n.valeur} a un fils {cote.replace('droite', 'droit')} → continuer"))
            n = suivant
        res = n
        ok = est_abr(self.racine)

        def fin():
            lignes = [f"Étapes : {len(events)} (au plus hauteur + 1 = {hauteur(self.racine) + 1})"]
            if not ok:
                lignes.append(("Attention : l'arbre n'est PAS un ABR, ce résultat n'est pas fiable !", "ko"))
            self.afficher_resultat(f"{mot} de l'ABR", lignes, f"{mot} = {res.valeur}")
        self.lancer(f"{mot} de l'ABR", events, fin, "min_abr" if quoi == "min" else "max_abr")

    def voisin_abr(self, sens):
        """Trouve le successeur ou le prédécesseur infixé d'un nœud sélectionné."""
        if not self.exiger_arbre() or not self.exiger_selection():
            return
        if not est_abr(self.racine):
            messagebox.showwarning("Pas un ABR", "Cette opération suppose un ABR "
                                                 "(voir « Est-ce un ABR ? »).")
            return
        n = self.selection
        succ = sens == "succ"
        proche, loin = ("droite", "gauche") if succ else ("gauche", "droite")
        nom = "Successeur" if succ else "Prédécesseur"
        events, res = [], None
        if getattr(n, proche) is not None:
            events.append(Ev(n, "enter", f"{n.valeur} a un fils {proche.replace('droite', 'droit')} → "
                                         f"{nom.lower()} = {'min' if succ else 'max'} de ce sous-arbre"))
            p = getattr(n, proche)
            events.append(Ev(p, "enter", f"aller à {proche}"))
            while getattr(p, loin) is not None:
                p = getattr(p, loin)
                events.append(Ev(p, "enter", f"puis à {loin} tant que possible"))
            res = p
        else:
            events.append(Ev(n, "enter", f"{n.valeur} n'a pas de fils {proche.replace('droite', 'droit')} → "
                                         f"on remonte : on cherche depuis la racine"))
            cand, p = None, self.racine
            while p is not n:
                vers_loin = (n.valeur < p.valeur) if succ else (n.valeur > p.valeur)
                if vers_loin:
                    cand = p
                    events.append(Ev(p, "path", f"{n.valeur} {'<' if succ else '>'} {p.valeur} → "
                                                f"{p.valeur} devient candidat, aller à {loin}"))
                    p = getattr(p, loin)
                else:
                    events.append(Ev(p, "enter", f"{n.valeur} {'>' if succ else '<'} {p.valeur} → "
                                                 f"aller à {proche}"))
                    p = getattr(p, proche)
            res = cand
        if res is not None:
            events.append(Ev(res, "found", f"{nom} = {res.valeur}"))

        def fin():
            if res is None:
                self.afficher_resultat(f"{nom} infixé de {n.valeur}", [
                    f"{n.valeur} est le {'plus grand' if succ else 'plus petit'} élément : "
                    f"pas de {nom.lower()}."])
            else:
                lst = valeurs(self.racine, "GRD")
                self.afficher_resultat(f"{nom} infixé de {n.valeur}", [
                    f"Parcours infixé : {lst}",
                    f"{nom} = voisin {'suivant' if succ else 'précédent'} dans cette liste."],
                    f"{nom} = {res.valeur}")
        self.lancer(f"{nom} de {n.valeur}", events, fin, "successeur")

    def equilibrer(self):
        """Reconstruit un ABR équilibré à partir de ses valeurs en ordre infixé."""
        if not self.exiger_arbre():
            return
        self.preparer()
        if not est_abr(self.racine):
            messagebox.showwarning("Pas un ABR", "Seul un ABR peut être rééquilibré "
                                                 "par cette méthode.")
            return
        h0 = hauteur(self.racine)
        vals = valeurs(self.racine, "GRD")
        self.racine = construire_equilibre(vals)
        self.selection = None
        self.afficher_algo("equilibrer")
        self.dessiner()
        self._montrer_code_arbre()
        self.afficher_resultat("ABR équilibré", [
            f"Valeurs triées : {vals}",
            f"Hauteur avant : {h0}   →   après : {hauteur(self.racine)}",
            f"Hauteur minimale possible pour n = {len(vals)} : {len(vals).bit_length() - 1}"])

    # ==================================================================
    #  QUIZ
    # ==================================================================

    def quiz_nouvelle(self):
        """Choisit une question et, selon le réglage, génère un nouvel arbre."""
        self.preparer()
        if self.quiz_nouvel_arbre.get() or self.racine is None:
            n = random.randint(5, 9)
            if random.random() < 0.5:
                self.generer_abr(n)
            else:
                self.generer_quelconque(n)
            self.dessiner()
        self.quiz_idx = random.randrange(len(self.QUIZ))
        self.quiz_repondu = False
        self.lbl_question.config(text=self.QUIZ[self.quiz_idx][0])
        self.quiz_rep.set("")
        self.lbl_feedback.config(text="", foreground="black")

    def quiz_verifier(self):
        """Compare la réponse saisie à la solution calculée sur l'arbre courant."""
        if self.quiz_idx is None or self.racine is None:
            messagebox.showinfo("Quiz", "Cliquez d'abord sur « Nouvelle question ».")
            return
        attendu = self.QUIZ[self.quiz_idx][1](self.racine)
        attendu = attendu if isinstance(attendu, list) else [attendu]
        rep = [int(x) for x in re.findall(r"-?\d+", self.quiz_rep.get())]
        ok = rep == attendu
        if not self.quiz_repondu:
            self.quiz_repondu = True
            self.score[1] += 1
            self.score[0] += 1 if ok else 0
            self.lbl_score.config(text=f"Score : {self.score[0]} / {self.score[1]}")
        if ok:
            self.lbl_feedback.config(text="✓ Bravo, c'est correct !", foreground="#1E8E3E")
        else:
            self.lbl_feedback.config(
                text="✗ Pas tout à fait. Réessayez, ou cliquez sur « Voir la correction animée ».",
                foreground="#C5221F")

    def quiz_correction(self):
        """Affiche la solution puis lance l'animation correspondant à la question."""
        if self.quiz_idx is None or self.racine is None:
            return
        if not self.quiz_repondu:
            self.quiz_repondu = True
            self.score[1] += 1
            self.lbl_score.config(text=f"Score : {self.score[0]} / {self.score[1]}")
        attendu = self.QUIZ[self.quiz_idx][1](self.racine)
        self.lbl_feedback.config(text=f"Réponse attendue : "
                                      f"{' '.join(map(str, attendu)) if isinstance(attendu, list) else attendu}",
                                 foreground="#0B5394")
        self.QUIZ[self.quiz_idx][2]()


if __name__ == "__main__":
    Application().mainloop()








