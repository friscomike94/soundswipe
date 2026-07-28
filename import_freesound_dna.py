#!/usr/bin/env python3
import datetime, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

SB_URL='https://tfoilkjyuzayxcedcmwo.supabase.co'
SB_KEY='sb_publishable_F4kidHmHAymbnwOWcK22dw_NkbNrNT4'
SB_HEADERS={'apikey':SB_KEY,'Authorization':'Bearer '+SB_KEY,'Content-Type':'application/json'}
API='https://freesound.org/apiv2/search/text/'
KEY=os.environ.get('FREESOUND_API_KEY','').strip()
LIMIT=int(os.environ.get('LIMIT_PER_QUERY') or '5')
DRY=(os.environ.get('DRY_RUN','false').lower()=='true')
if not KEY:
    raise SystemExit('Missing GitHub secret FREESOUND_API_KEY')

QUERIES=[
 ('dna_rhythm','drum_pocket','tight boom-bap drums','boom bap drum loop',2,12),
 ('dna_rhythm','drum_pocket','UK garage snare swing','uk garage drum loop snare swing',2,12),
 ('dna_rhythm','hi_hat_feel','crisp swung hi-hats','swung hi hat loop crisp',1,8),
 ('dna_rhythm','snare_feel','garage offbeat snare','garage snare offbeat loop',1,8),
 ('dna_rhythm','groove_body','dusty swung drums','dusty swung hip hop drums loop',2,12),
 ('dna_bass','bass_type','warm upright bass','upright bass loop warm',2,12),
 ('dna_bass','bass_type','808 sub bass','808 sub bass one shot',0.2,4),
 ('dna_bass','bass_type','live bass guitar','live bass guitar loop',2,12),
 ('dna_bass','bass_feeling','distorted bass pulse','distorted bass pulse loop',1,8),
 ('dna_bass','bass_motion','syncopated bass bounce','syncopated bass loop bounce',2,12),
 ('dna_vocal','vocal_texture','intimate dry rap vocal','dry rap vocal phrase',1,10),
 ('dna_vocal','vocal_texture','breathy vocal phrase','breathy vocal phrase',1,10),
 ('dna_vocal','vocal_emotion','gritty male adlib','gritty male vocal adlib',0.5,8),
 ('dna_vocal','vocal_layering','layered call and response','call response vocal',1,12),
 ('dna_vocal','vocal_distance','distant ghost vocal','distant ghost vocal',1,12),
 ('dna_hook','hook_instrument','chopped brass hook','brass stab loop hook',0.5,8),
 ('dna_hook','hook_instrument','muted guitar riff','muted guitar riff loop',1,10),
 ('dna_hook','hook_instrument','vocal chop lead','vocal chop lead loop',1,10),
 ('dna_hook','hook_instrument','felt piano motif','felt piano motif loop',1,10),
 ('dna_hook','motif_shape','short repeated phrase','short repeated musical phrase loop',1,8),
 ('dna_chord','chord_instrument','warm Rhodes pads','Rhodes chord loop warm',2,12),
 ('dna_chord','chord_instrument','minor piano loop','minor piano loop',2,12),
 ('dna_chord','chord_instrument','dark guitar chords','dark guitar chord loop',2,12),
 ('dna_chord','harmony_mood','bittersweet harmony','bittersweet chord loop',2,12),
 ('dna_chord','chord_rhythm','syncopated chord stabs','syncopated chord stabs loop',1,8),
 ('dna_mix','mix_texture','tape saturation','tape saturation texture loop',1,12),
 ('dna_mix','noise_layer','vinyl crackle','vinyl crackle loop',2,15),
 ('dna_mix','reverb_space','dry close mic','dry close mic sound',0.5,8),
 ('dna_mix','reverb_space','small room ambience','small room ambience',2,15),
 ('dna_mix','stereo_width','wide chorus space','wide stereo ambience',2,15),
 ('dna_mood','mood_scene','late-night city mood','late night city ambience',2,15),
 ('dna_mood','mood_scene','smoky club','smoky club ambience',2,15),
 ('dna_mood','mood_scene','rainy street','rainy street ambience',2,15),
 ('dna_mood','emotional_direction','emotional uplift','uplifting emotional musical loop',2,12),
 ('dna_mood','social_feeling','intimate two-person scene','intimate room ambience',2,15),
 ('dna_wild','wild_texture','strange but attractive texture','strange musical texture loop',1,12),
 ('dna_wild','wild_texture','mechanical emotional pulse','mechanical pulse loop',1,10),
 ('dna_wild','wild_texture','ghostly melodic fragment','ghostly melodic fragment',1,10),
 ('dna_wild','wild_texture','broken machine rhythm','broken machine rhythm loop',1,10),
]

def slug(s):
    return re.sub(r'[^a-z0-9]+','_',s.lower()).strip('_')[:70]

def req_json(url, headers=None, data=None, method='GET', timeout=60):
    req=urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body=r.read().decode('utf-8')
        return json.loads(body) if body else None

def search(query, lo, hi):
    params={
        'query': query,
        'filter': f'license:"Creative Commons 0" duration:[{lo} TO {hi}]',
        'fields': 'id,name,tags,description,license,username,duration,previews,url,avg_rating,num_ratings,created',
        'sort': 'score',
        'page_size': str(LIMIT),
    }
    url=API+'?'+urllib.parse.urlencode(params)
    return req_json(url, headers={'Authorization':'Token '+KEY})

def make_row(x, category, axis, token, query, batch):
    fid=str(x.get('id'))
    previews=x.get('previews') or {}
    preview=previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3') or previews.get('preview-hq-ogg') or previews.get('preview-lq-ogg') or ''
    meta={
        'freesound_id': fid,
        'query': query,
        'axis': axis,
        'token': token,
        'tags': (x.get('tags') or [])[:30],
        'duration': x.get('duration'),
        'avg_rating': x.get('avg_rating'),
        'num_ratings': x.get('num_ratings'),
        'description': (x.get('description') or '')[:500],
    }
    return {
        'id': f'fs_{fid}_{slug(axis)}_{slug(token)}',
        'title': x.get('name') or f'Freesound {fid}',
        'full_name': f'{token} · {x.get("name") or fid}',
        'category': category,
        'instrument': token,
        'bpm': None,
        'batch': batch,
        'prompt': 'DNA_META '+json.dumps(meta, ensure_ascii=False, separators=(',',':')),
        'cdn': preview,
        'suno': None,
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'seek': None,
        'dur': x.get('duration'),
        'role': axis,
        'year': None,
        'source': 'Freesound',
        'source_url': x.get('url') or f'https://freesound.org/s/{fid}/',
        'license': x.get('license') or 'Creative Commons 0',
        'artist': x.get('username') or '',
    }

def upsert(rows):
    if not rows: return []
    data=json.dumps(rows,ensure_ascii=False).encode('utf-8')
    return req_json(SB_URL+'/rest/v1/ss_sounds', data=data, method='POST', headers={**SB_HEADERS,'Prefer':'resolution=merge-duplicates,return=representation'}) or []

batch='freesound_dna_'+datetime.datetime.now().strftime('%Y%m%d')
rows=[]
for category, axis, token, query, lo, hi in QUERIES:
    print(f'SEARCH {category} | {axis} | {token} | {query}')
    try:
        data=search(query, lo, hi)
        results=data.get('results') or []
    except urllib.error.HTTPError as e:
        print('HTTP_ERROR', e.code, e.read().decode('utf-8')[:300])
        continue
    cc0=[x for x in results if 'creative commons 0' in (x.get('license') or '').lower()]
    print('  results', len(results), 'cc0', len(cc0))
    rows.extend(make_row(x, category, axis, token, query, batch) for x in cc0)
    time.sleep(0.35)

dedup={r['id']:r for r in rows}
rows=list(dedup.values())
print(json.dumps({'candidate_rows':len(rows),'dry_run':DRY,'batch':batch}, indent=2))
if DRY:
    print(json.dumps(rows[:5], ensure_ascii=False, indent=2))
    sys.exit(0)
inserted=[]
for i in range(0,len(rows),100):
    inserted.extend(upsert(rows[i:i+100]))
print(json.dumps({'inserted_or_updated':len(inserted),'batch':batch}, indent=2))
