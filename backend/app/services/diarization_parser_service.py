from typing import Optional

def parse_diarization(raw_diarization: Optional[list]) -> Optional[list]:
    """
    Parse la réponse de diarisation Voxtral et retourne une liste de segments
    normalisés avec labels locuteurs lisibles.

    Format d'entrée Voxtral :
    [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 3.2, "text": "Bonjour..."},
        {"speaker": "SPEAKER_01", "start": 3.5, "end": 7.1, "text": "Merci..."},
    ]

    Format de sortie :
    [
        {"speaker": "Intervenant 1", "start": 0.0, "end": 3.2, "text": "Bonjour..."},
        {"speaker": "Intervenant 2", "start": 3.5, "end": 7.1, "text": "Merci..."},
    ]
    """
    if not raw_diarization:
        return None

    # Mapping SPEAKER_XX → Intervenant N
    speaker_map: dict[str, str] = {}
    counter = 1

    normalized = []
    for segment in raw_diarization:
        raw_speaker = segment.get("speaker", "SPEAKER_00")

        if raw_speaker not in speaker_map:
            speaker_map[raw_speaker] = f"Intervenant {counter}"
            counter += 1

        normalized.append({
            "speaker": speaker_map[raw_speaker],
            "start":   round(float(segment.get("start", 0.0)), 2),
            "end":     round(float(segment.get("end", 0.0)), 2),
            "text":    segment.get("text", "").strip()
        })

    # Tri chronologique
    normalized.sort(key=lambda s: s["start"])

    # Fusion des segments consécutifs du même locuteur
    merged = []
    for segment in normalized:
        if merged and merged[-1]["speaker"] == segment["speaker"]:
            merged[-1]["end"]   = segment["end"]
            merged[-1]["text"] += " " + segment["text"]
        else:
            merged.append(dict(segment))

    return merged


def get_speaker_summary(segments: list) -> dict:
    """
    Calcule la durée de parole par locuteur.
    Utile pour le frontend — afficher "Intervenant 1 : 3m42s".
    """
    summary: dict[str, float] = {}
    for segment in segments:
        speaker  = segment["speaker"]
        duration = segment["end"] - segment["start"]
        summary[speaker] = round(summary.get(speaker, 0.0) + duration, 2)
    return summary