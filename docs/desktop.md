# App desktop — lancer le paquet

Ce document est pour qui a déjà un paquet `PortfolioCMS` (dossier ou zip) et
veut simplement le lancer. Pour le construire toi-même, voir
[builder.md](builder.md).

## C'est quoi

Un exécutable autonome (pas besoin de Python, de venv ni de terminal) qui
ouvre l'admin du CMS dans une fenêtre native. Pas d'authentification : ça
s'ouvre directement sur le tableau de bord.

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

Ou double-clic depuis le gestionnaire de fichiers. Certains gestionnaires
(Nautilus/GNOME notamment) demandent une confirmation de confiance la
première fois avant d'exécuter un binaire inconnu — normal, à accepter une
fois.

## Windows

⚠️ **Avant d'extraire le zip téléchargé**, débloque-le : clic droit dessus →
*Propriétés* → cocher **Débloquer** → OK (ou, une fois déjà extrait,
`Get-ChildItem -Recurse .\PortfolioCMS | Unblock-File` en PowerShell). Sans
ça, Windows marque le zip comme provenant d'internet (*Mark of the Web*) et
le pont .NET utilisé par pywebview refuse de s'initialiser au lancement
(`Failed to resolve Python.Runtime.Loader.Initialize`), même si le paquet
est parfaitement sain.

Le paquet n'étant pas signé (voir [builder.md](builder.md)), Windows
affichera un avertissement SmartScreen au premier lancement : « Informations
complémentaires » → « Exécuter quand même ».

Double-clic sur `PortfolioCMS.exe` pour lancer.

## macOS

Le paquet n'étant pas signé/notarisé, macOS bloquera via Gatekeeper au
premier lancement : clic droit sur `PortfolioCMS` → *Ouvrir* (plutôt qu'un
simple double-clic, qui refuserait silencieusement) → confirmer dans la
boîte de dialogue.

⚠️ Build macOS pas encore testé en conditions réelles (voir
[builder.md](builder.md)) — cette procédure est la procédure standard
Gatekeeper, à confirmer sur un vrai run.

## Ce n'est pas un outil de dev

Ce paquet est figé, destiné au partage — pas à l'itération. Pour
développer/tester des changements de code, voir [dev.md](dev.md)
(`flask --app cms.app run --debug` depuis les sources), pas via l'exécutable
packagé.
