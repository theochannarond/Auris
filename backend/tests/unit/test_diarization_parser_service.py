import pytest
from app.services.diarization_parser_service import parse_diarization, get_speaker_summary

# ─── Données de test ───
TWO_SPEAKERS = [
    {"speaker": "SPEAKER_00", "start": 0.0,  "end": 3.2,  "text": "Bonjour tout le monde."},
    {"speaker": "SPEAKER_01", "start": 3.5,  "end": 7.1,  "text": "Merci de me recevoir."},
    {"speaker": "SPEAKER_00", "start": 7.5,  "end": 10.0, "text": "Commençons la réunion."},
]

CONSECUTIVE_SAME_SPEAKER = [
    {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.0, "text": "Première phrase."},
    {"speaker": "SPEAKER_00", "start": 2.1, "end": 4.0, "text": "Deuxième phrase."},
]

UNSORTED = [
    {"speaker": "SPEAKER_01", "start": 5.0, "end": 8.0, "text": "Je parle en second."},
    {"speaker": "SPEAKER_00", "start": 0.0, "end": 4.0, "text": "Je parle en premier."},
]

# ─── Tests parse_diarization ───

def test_none_retourne_none():
    """Sans diarisation, on retourne None"""
    assert parse_diarization(None) is None

def test_liste_vide_retourne_none():
    """Liste vide → None"""
    assert parse_diarization([]) is None

def test_deux_locuteurs_labels_lisibles():
    """SPEAKER_00 → Intervenant 1, SPEAKER_01 → Intervenant 2"""
    result = parse_diarization(TWO_SPEAKERS)
    speakers = {s["speaker"] for s in result}
    assert "Intervenant 1" in speakers
    assert "Intervenant 2" in speakers
    assert "SPEAKER_00" not in speakers
    assert "SPEAKER_01" not in speakers

def test_ordre_chronologique():
    """Les segments sont triés par start même si Voxtral les envoie dans le désordre"""
    result = parse_diarization(UNSORTED)
    starts = [s["start"] for s in result]
    assert starts == sorted(starts)

def test_fusion_segments_consecutifs_meme_locuteur():
    """Deux segments consécutifs du même locuteur sont fusionnés en un seul"""
    result = parse_diarization(CONSECUTIVE_SAME_SPEAKER)
    assert len(result) == 1
    assert result[0]["text"] == "Première phrase. Deuxième phrase."
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 4.0

def test_pas_de_fusion_locuteurs_differents():
    """Deux locuteurs différents alternés ne sont pas fusionnés"""
    result = parse_diarization(TWO_SPEAKERS)
    assert len(result) == 3  # SPEAKER_00, SPEAKER_01, SPEAKER_00 — non fusionnables

def test_texte_nettoye():
    """Les espaces autour du texte sont supprimés"""
    segments = [{"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0, "text": "  Texte  "}]
    result = parse_diarization(segments)
    assert result[0]["text"] == "Texte"

def test_timestamps_arrondis():
    """Les timestamps sont arrondis à 2 décimales"""
    segments = [{"speaker": "SPEAKER_00", "start": 0.123456, "end": 3.987654, "text": "Test"}]
    result = parse_diarization(segments)
    assert result[0]["start"] == 0.12
    assert result[0]["end"] == 3.99

def test_segment_sans_speaker_utilise_defaut():
    """Un segment sans clé speaker ne plante pas"""
    segments = [{"start": 0.0, "end": 1.0, "text": "Texte sans speaker"}]
    result = parse_diarization(segments)
    assert result is not None
    assert len(result) == 1

# ─── Tests get_speaker_summary ───

def test_duree_parole_par_locuteur():
    """La durée de parole est correctement calculée par locuteur"""
    segments = parse_diarization(TWO_SPEAKERS)
    summary = get_speaker_summary(segments)
    assert "Intervenant 1" in summary
    assert "Intervenant 2" in summary
    assert summary["Intervenant 2"] == round(7.1 - 3.5, 2)

def test_summary_locuteur_unique():
    """Avec un seul locuteur, le summary ne contient qu'une entrée"""
    segments = parse_diarization(CONSECUTIVE_SAME_SPEAKER)
    summary = get_speaker_summary(segments)
    assert len(summary) == 1