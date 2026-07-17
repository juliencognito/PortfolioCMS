# App desktop — lancer le paquet

Ce document est pour qui a déjà un paquet `PortfolioCMS` (dossier ou zip) et
veut simplement le lancer. Pour le construire toi-même, voir
[builder.md](builder.md).

## C'est quoi

Un exécutable autonome (pas besoin de Python ni de venv) qui démarre le
serveur admin et ouvre le tableau de bord dans ton navigateur par défaut —
pas d'authentification, ça s'ouvre directement dessus. Une petite fenêtre de
console reste ouverte pendant que le serveur tourne (elle affiche le journal
du serveur) : ferme-la ou fais **Ctrl+C** dedans pour quitter — fermer
l'onglet du navigateur ne suffit pas, le serveur continue de tourner tant
que cette fenêtre est ouverte.

Tout ce qui est propre à **un site** (base, uploads, site publié) vit dans
un dossier `project/` à côté de l'exécutable :

- pour **repartir d'un site vierge**, renomme ou retire ce dossier ;
- pour **changer de site**, remplace-le par un autre dossier `project/`
  exporté ailleurs (ou reçu de quelqu'un) ;
- pour **sauvegarder/partager un site**, c'est ce dossier-là qu'il faut
  zipper — le paquet applicatif lui-même (l'exécutable + `_internal/`) est
  générique, pas la peine de le sauvegarder avec.

## Où récupérer le paquet

Zip téléchargeable depuis l'onglet **Actions** du dépôt GitHub du projet
(section *Artifacts* d'un run *Build desktop package*), ou depuis les
**Releases** si un tag a été publié. Un paquet par OS (Linux, Windows,
macOS Intel, macOS ARM) — prends celui qui correspond à ta machine.

## Linux

```bash
cd PortfolioCMS/
./PortfolioCMS
```

Lancement **depuis un terminal recommandé** : c'est ce qui donne la fenêtre
de console (le journal du serveur, Ctrl+C pour quitter) décrite ci-dessus.
Un double-clic depuis le gestionnaire de fichiers lance aussi le serveur et
ouvre le navigateur, mais sans terminal attaché il n'y a alors aucune
fenêtre visible pour l'arrêter — il faut le tuer via le gestionnaire de
tâches. Certains gestionnaires (Nautilus/GNOME notamment) demandent aussi
une confirmation de confiance la première fois avant d'exécuter un binaire
inconnu — normal, à accepter une fois.

## Windows

Le paquet n'étant pas signé (voir [builder.md](builder.md)), Windows
affichera un avertissement SmartScreen au premier lancement : « Informations
complémentaires » → « Exécuter quand même ».

Double-clic sur `PortfolioCMS.exe` pour lancer — une fenêtre de console
s'ouvre automatiquement (le journal du serveur, Ctrl+C ou fermer la fenêtre
pour quitter).

⚠️ **Piège vécu et corrigé** : un build produit par une version antérieure de
`desktop.spec` pouvait échouer avec `Failed to load Python DLL
'...\_internal\python313.dll' — LoadLibrary: Le module spécifié est
introuvable`, `python313.dll` étant **réellement absent** de `_internal/`
(pas un souci runtime/antivirus — voir CLAUDE.md pour la cause exacte, déjà
corrigée dans `desktop.spec`). Si tu retombes sur cette erreur, télécharge
un zip généré par un run récent de `build-desktop-windows.yml` plutôt que
de réutiliser un ancien zip.

## macOS

Le paquet n'étant pas signé/notarisé, macOS bloquera via Gatekeeper au
premier lancement : clic droit sur `PortfolioCMS` → *Ouvrir* (plutôt qu'un
simple double-clic, qui refuserait silencieusement) → confirmer dans la
boîte de dialogue. Comme sur Linux, lancer depuis un Terminal est ce qui
donne la fenêtre de console pour arrêter le serveur proprement.

⚠️ Build macOS pas encore testé en conditions réelles (voir
[builder.md](builder.md)) — cette procédure est la procédure standard
Gatekeeper, à confirmer sur un vrai run.

## Ce n'est pas un outil de dev

Ce paquet est figé, destiné au partage — pas à l'itération. Pour
développer/tester des changements de code, voir [dev.md](dev.md)
(`flask --app cms.app run --debug` depuis les sources), pas via l'exécutable
packagé.
