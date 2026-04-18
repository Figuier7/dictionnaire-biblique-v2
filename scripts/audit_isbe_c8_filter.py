#!/usr/bin/env python3
"""Affine le filtrage C8 : exclut les mots FR=EN identiques et les noms propres."""
import json
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "work" / "audit"
IN_JSON = AUDIT_DIR / "isbe-c8-cat-a.json"
OUT_JSON = AUDIT_DIR / "isbe-c8-cat-a-filtered.json"
OUT_MD = AUDIT_DIR / "isbe-c8-cat-a-filtered.md"

# Mots français = anglais (orthographe identique, sens identique)
# Il ne faut PAS les traiter — leur label est déjà correct en français
IDENTICAL_FR_EN = {
    # -tion / -sion (la plupart des mots FR en -tion sont identiques EN)
    'compassion', 'conclusion', 'confusion', 'consolation', 'consumption',
    'division', 'expression', 'extortion', 'invention', 'mansion', 'mention',
    'occasion', 'opposition', 'oppression', 'ordination', 'pension',
    'persecution', 'possession', 'precaution', 'prediction', 'pretension',
    'prevention', 'production', 'promotion', 'promulgation', 'proportion',
    'proposition', 'prosecution', 'prostitution', 'prostration', 'protection',
    'protestation', 'province', 'reception', 'recession', 'reclamation',
    'recognition', 'recommendation', 'reconciliation', 'recrimination',
    'rectification', 'reduction', 'reelection', 'reflection', 'reformation',
    'refraction', 'refutation', 'regeneration', 'region', 'relation',
    'relaxation', 'religion', 'remonstration', 'renovation', 'reparation',
    'repetition', 'replication', 'representation', 'repression', 'repudiation',
    'reputation', 'requisition', 'reservation', 'resignation', 'resistance',
    'resolution', 'respiration', 'restitution', 'restoration', 'restriction',
    'resurrection', 'retention', 'retribution', 'revelation', 'reverberation',
    'reverence', 'reversion', 'revision', 'revocation', 'revolution',
    'satisfaction', 'science', 'section', 'seduction', 'selection', 'sensation',
    'separation', 'session', 'silence', 'simulation', 'situation', 'solution',
    'sommation', 'station', 'subjection', 'subjugation', 'submersion',
    'submission', 'subordination', 'subscription', 'substitution', 'subtraction',
    'succession', 'suggestion', 'superstition', 'supervision', 'supposition',
    'suppression', 'suspension', 'temptation', 'tension', 'termination',
    'torture', 'tradition', 'translation', 'transmission', 'transportation',
    'traction', 'trepidation', 'tuition', 'ulceration', 'unification', 'union',
    'variation', 'vegetation', 'veneration', 'version', 'vexation', 'vibration',
    'violation', 'vision', 'vocation', 'absolution', 'abstinence',
    'affection', 'affliction', 'alliance', 'allusion', 'ambition', 'apparition',
    'application', 'approbation', 'ascension', 'aspersion', 'assassination',
    'association', 'attention', 'audience', 'benevolence', 'benediction',
    'cessation', 'circulation', 'cogitation', 'competition', 'composition',
    'compression', 'compulsion', 'conception', 'concession', 'concordance',
    'condensation', 'confidence', 'confiscation', 'confrontation', 'congregation',
    'conjuration', 'connection', 'consanguinity', 'consecration', 'consent',
    'conservation', 'consideration', 'conspiration', 'constellation',
    'consternation', 'construction', 'consultation', 'consummation',
    'contemplation', 'contestation', 'contradiction', 'contribution',
    'contrition', 'convention', 'conversion', 'conviction', 'convocation',
    'cooperation', 'coronation', 'correction', 'correlation', 'correspondence',
    'corroboration', 'corruption', 'cremation', 'crisis', 'deception',
    'declaration', 'dedication', 'defection', 'definition', 'demonstration',
    'denomination', 'denunciation', 'deportation', 'deposition', 'deprivation',
    'description', 'designation', 'destination', 'destruction', 'determination',
    'detestation', 'devotion', 'digestion', 'dilapidation', 'diminution',
    'direction', 'discretion', 'discussion', 'disputation', 'dissipation',
    'distance', 'distinction', 'distraction', 'distribution', 'divination',
    'domination', 'donation', 'edification', 'education', 'election',
    'emancipation', 'emulation', 'erudition', 'evaluation', 'evocation',
    'evolution', 'exaltation', 'examination', 'exception', 'exclusion',
    'execution', 'exhibition', 'exhortation', 'expansion', 'experience',
    'exploration', 'explosion', 'exposition', 'expulsion', 'extermination',
    'extinction', 'fabrication', 'formation', 'fortification', 'foundation',
    'fraction', 'function', 'generation', 'germination', 'gradation',
    'gratification', 'habitation', 'hesitation', 'humiliation', 'identification',
    'illumination', 'illusion', 'imagination', 'imitation', 'immersion',
    'immigration', 'immolation', 'importation', 'imposition', 'impression',
    'inauguration', 'incarnation', 'incineration', 'incision', 'inclination',
    'incorporation', 'indication', 'indignation', 'induction', 'infection',
    'infiltration', 'inflammation', 'inflation', 'information', 'inhalation',
    'initiation', 'injection', 'injunction', 'insertion', 'inspection',
    'inspiration', 'installation', 'instauration', 'institution', 'instruction',
    'insurrection', 'integration', 'intention', 'interaction', 'intercession',
    'interdiction', 'intermission', 'interpretation', 'interrogation',
    'interruption', 'intersection', 'intervention', 'intimidation', 'introduction',
    'intuition', 'inundation', 'invasion', 'investigation', 'invitation',
    'invocation', 'irrigation', 'irritation', 'jubilation', 'junction',
    'jurisdiction', 'justification', 'legislation', 'levitation', 'liberation',
    'limitation', 'liquidation', 'locomotion', 'lubrication', 'magnification',
    'malediction', 'manifestation', 'manipulation', 'mediation', 'medication',
    'meditation', 'migration', 'moderation', 'modification', 'mortification',
    'motivation', 'multiplication', 'mutation', 'narration', 'nation',
    'navigation', 'negation', 'nomination', 'notion', 'nutrition', 'obligation',
    'observation', 'obstruction', 'omission', 'operation', 'opinion', 'ordinance',
    'ordination', 'ornament', 'palpitation', 'participation', 'passion',
    'patience', 'penetration', 'perception', 'perdition', 'perfection',
    'permission', 'perpetration', 'perpetuation', 'persecution', 'petition',
    'plantation', 'pollution', 'population', 'portion', 'position', 'possession',
    'precipitation', 'prefiguration', 'premeditation', 'preoccupation',
    'preparation', 'prescription', 'presentation', 'preservation', 'prison',
    'procession', 'proclamation', 'procreation', 'production', 'profanation',
    'profession', 'profusion', 'prohibition', 'projection', 'prolongation',
    'promotion', 'promulgation', 'propagation', 'proportion', 'proposition',
    'prosecution', 'prosperity', 'prostitution', 'prostration', 'protection',
    'protestation', 'provocation', 'publication', 'punition', 'purification',
    'qualification', 'question', 'radiation', 'ramification', 'ratification',
    'realization', 'rebellion', 'recitation', 'reclamation', 'recognition',
    'reconciliation', 'rectification', 'redaction', 'reduction', 'reformation',
    'refraction', 'refutation', 'regeneration', 'region', 'regression',
    'regulation', 'rehabilitation', 'reincarnation', 'reiteration', 'rejection',
    'relation', 'relaxation', 'religion', 'renovation', 'renunciation',
    'reparation', 'repetition', 'replication', 'representation', 'reproduction',
    'reprobation', 'repudiation', 'reputation', 'requisition', 'reservation',
    'resignation', 'resistance', 'resolution', 'respiration', 'restitution',
    'restoration', 'restriction', 'resumption', 'resurrection', 'retention',
    'retribution', 'revelation', 'reverence', 'revision', 'revolution',
    'satisfaction', 'science', 'sedation', 'seduction', 'sensation',
    'separation', 'silence', 'simulation', 'solution', 'station',
    'stimulation', 'stipulation', 'subjection', 'submission', 'subordination',
    'subscription', 'substitution', 'subtraction', 'suction', 'suffocation',
    'suggestion', 'suggestion', 'supposition', 'suppression', 'suspension',
    'temptation', 'tension', 'torture', 'tradition', 'transaction',
    'transcription', 'transfiguration', 'transformation', 'transgression',
    'transition', 'translation', 'transmission', 'version', 'vibration',
    'violation', 'vision', 'vocation',
    # -ment (most are identical)
    'amendment', 'document', 'element', 'fragment', 'government', 'impediment',
    'instrument', 'lament', 'ligament', 'moment', 'monument', 'ornament',
    'raiment', 'sacrament', 'sediment', 'sentiment', 'testament', 'torment',
    # -ance / -ence mostly identical
    'abstinence', 'acceptance', 'allegiance', 'allowance', 'ambulance',
    'appearance', 'arrogance', 'assurance', 'audience', 'benevolence',
    'concordance', 'confidence', 'conscience', 'continuance', 'correspondence',
    'countenance', 'credence', 'defiance', 'dependance', 'difference',
    'disobedience', 'distance', 'divergence', 'eloquence', 'endurance',
    'essence', 'evidence', 'excellence', 'existence', 'experience', 'ignorance',
    'importance', 'impudence', 'indifference', 'indigence', 'indolence',
    'indulgence', 'influence', 'innocence', 'insolence', 'instance',
    'intelligence', 'interference', 'irreverence', 'magnificence', 'maintenance',
    'munificence', 'nuisance', 'obedience', 'observance', 'obstinance',
    'occurrence', 'offence', 'omnipotence', 'omnipresence', 'omniscience',
    'ordinance', 'patience', 'performance', 'pertinence', 'pestilence',
    'predominance', 'preeminence', 'preference', 'presence', 'prevalence',
    'providence', 'prudence', 'reference', 'remonstrance', 'remembrance',
    'repentance', 'reputation', 'reverence', 'romance', 'science', 'seance',
    'sentence', 'sequence', 'significance', 'silence', 'sufficience',
    'suspense', 'tolerance', 'transparence', 'vehemence', 'vengeance',
    'vigilance', 'violence', 'virulence',
    # -ous (mostly FR=EN)
    'ambitious', 'curious', 'glorious', 'harmonious', 'melodious', 'precious',
    'religious', 'superstitious', 'victorious', 'virtuous',
    # Misc identical
    'ancestor', 'antipater',  # antipater = nom propre
    'aserer',  # nom propre
    'carabasion',  # nom propre
    'cogitation', 'commerce', 'compassion', 'comportement', 'composition',
    'conscience', 'conception', 'connection', 'constellation', 'constitution',
    'consultation', 'contamination', 'contraction', 'contradiction',
    'contribution', 'conversation', 'conversion', 'conviction', 'cooperation',
    'coronation', 'correction', 'corruption', 'creation', 'credulite',
    'cremation', 'definition', 'demonstration', 'description', 'deduction',
    'determination', 'direction', 'diversion', 'division', 'education',
    'emancipation', 'emulation', 'evacuation', 'exclusion', 'execution',
    'expression', 'faction', 'formation', 'function', 'habitation', 'immersion',
    'imagination', 'imitation', 'immersion', 'induction', 'infection',
    'insertion', 'instruction', 'intention', 'invention', 'invitation',
    'invocation', 'liaison', 'limitation', 'lotion', 'manifestation',
    'manipulation', 'medication', 'meditation', 'mention', 'migration',
    'moderation', 'monument', 'multiplication', 'nation', 'notion',
    'nutrition', 'observation', 'occasion', 'omission', 'operation', 'opinion',
    'organisation', 'passion', 'permission', 'petition', 'plantation',
    'portion', 'position', 'preparation', 'prevention', 'procession',
    'production', 'proposition', 'question', 'reception', 'redirection',
    'reduction', 'relation', 'religion', 'repetition', 'respiration',
    'resurrection', 'revolution', 'satisfaction', 'science', 'section',
    'sensation', 'separation', 'session', 'silence', 'situation',
    'station', 'submission', 'succession', 'suggestion', 'suppression',
    'tension', 'termination', 'tradition', 'translation', 'transmission',
    'vision', 'vocation',
}

# Noms propres bibliques (fausses détections)
PROPER_NOUNS = {
    'antipater', 'aserer', 'carabasion', 'cocker', 'ish', 'ithamar',
    'antipatris', 'belial', 'behemoth', 'leviathan', 'rehoboam',
    'jehoiakim', 'jeroboam', 'nebuchadnezzar', 'zerubbabel', 'zechariah',
    'malchiah', 'sennacherib', 'berachah', 'maher-shalal-hash-baz',
}


def main():
    with open(IN_JSON, encoding='utf-8') as f:
        d = json.load(f)

    real = []
    filtered_identical = []
    filtered_proper = []

    for s in d['items']:
        mot_lower = s['mot'].lower()
        if mot_lower in IDENTICAL_FR_EN:
            filtered_identical.append(s)
            continue
        if mot_lower in PROPER_NOUNS:
            filtered_proper.append(s)
            continue
        real.append(s)

    result = {
        'total_input': len(d['items']),
        'real_count': len(real),
        'filtered_identical_count': len(filtered_identical),
        'filtered_proper_count': len(filtered_proper),
        'real': real,
        'filtered_identical': filtered_identical,
        'filtered_proper': filtered_proper,
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # MD
    lines = [
        '# Audit C8 filtré — Category A épurée',
        '',
        f'- Total scan initial : **{len(d["items"])}**',
        f'- Mots FR=EN identiques (skip) : {len(filtered_identical)}',
        f'- Noms propres (skip) : {len(filtered_proper)}',
        f'- **À traiter : {len(real)}**',
        '',
        '## Liste à traiter',
        '',
        '| mot | concept_id | entry_id | def_preview |',
        '|---|---|---|---|',
    ]
    for s in real:
        prev = s['def_preview'].replace('|', '\\|')[:120]
        lines.append(f"| **{s['mot']}** | `{s['concept_id']}` | `{s['entry_id']}` | {prev} |")
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Total input        : {len(d["items"])}')
    print(f'Filtered identical : {len(filtered_identical)}')
    print(f'Filtered proper    : {len(filtered_proper)}')
    print(f'Real to translate  : {len(real)}')
    print(f'Output             : {OUT_JSON}')


if __name__ == '__main__':
    main()
