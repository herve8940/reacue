"""Relire les régions du projet REAPER pour en faire la structure du morceau.

Quand l'utilisateur déplace, renomme, ajoute ou supprime des régions à la main dans REAPER, la
préparation suivante (même morceau, structure gardée) les reprend au lieu de les écraser :

- seul le DÉBUT de chaque région compte (une section va jusqu'au début de la suivante) ;
- début -> mesure la plus proche sur la grille du morceau (tolérance 1/4 de mesure ; au-delà, arrondi
  à la mesure la plus proche avec un avertissement) ;
- nom repris tel quel (le type de section, donc la couleur, l'annonce et le rôle dans le prompteur,
  est déduit du nom, en français ou en anglais) ;
- région avant la mesure 1, après la fin du morceau, ou à la même mesure qu'une autre : ignorée
  avec un avertissement.

Fonction pure (aucun accès à REAPER) : testable sans pont.
"""
from __future__ import annotations

from .i18n import t

TOLERANCE = 0.25          # fraction de mesure


def regions_to_sections(regions: list[dict], bar_times: list[float], count_in: int, n_bars: int,
                        old_sections=None, ignore_names: tuple[str, ...] = ()) -> tuple[list[dict], list[str]]:
    """regions : [{"start", "end", "name"}] (secondes de la timeline REAPER).
    bar_times : débuts des mesures sur la timeline, de la mesure -count_in à la mesure n_bars (fin).
    Renvoie (sections [{"start_bar": 1-based, "name", "label"}], avertissements). Liste vide = aucune
    région utilisable."""
    old_sections = list(old_sections or [])
    warnings: list[str] = []
    song = [float(x) for x in bar_times[count_in:count_in + n_bars + 1]]
    if len(song) < 2:
        return [], warnings

    def bar_len(k: int) -> float:
        k = min(max(k, 0), len(song) - 2)
        return song[k + 1] - song[k]

    picked: dict[int, str] = {}
    for r in sorted(regions or [], key=lambda r: float(r.get("start", 0.0))):
        name = str(r.get("name") or "").strip()
        if name and name in ignore_names:
            continue                                            # région « morceau entier » de ReaCue
        s = float(r.get("start", 0.0))
        label = name or "?"
        if s < song[0] - TOLERANCE * bar_len(0):
            warnings.append(t("region_before", name=label))
            continue
        if s > song[-1] - TOLERANCE * bar_len(n_bars - 1):
            warnings.append(t("region_after", name=label))
            continue
        k = min(range(n_bars), key=lambda j: abs(song[j] - s))
        if abs(song[k] - s) > TOLERANCE * bar_len(k):
            warnings.append(t("region_rounded", name=label, bar=k + 1))
        if k in picked:
            warnings.append(t("region_duplicate", name=label, bar=k + 1))
            continue
        if not name:
            old = next((o for o in old_sections if o.start_bar == k), None)
            name = old.name if old else t("region_unnamed", n=len(picked) + 1)
        picked[k] = name
    out = []
    for k in sorted(picked):
        name = picked[k]
        old = (next((o for o in old_sections if o.name == name), None)
               or next((o for o in old_sections if o.start_bar == k), None))
        out.append({"start_bar": k + 1, "name": name, "label": old.label if old else "?"})
    if out and out[0]["start_bar"] > 1:
        warnings.append(t("region_first", last=out[0]["start_bar"] - 1, name=out[0]["name"]))
    return out, warnings


def same_structure(new: list[dict], old_sections) -> bool:
    """La structure lue dans les régions est-elle celle enregistrée (débuts et noms) ?"""
    a = [(1 if i == 0 else d["start_bar"], d["name"]) for i, d in enumerate(new)]
    b = [(s.start_bar + 1, s.name) for s in old_sections]
    return a == b
