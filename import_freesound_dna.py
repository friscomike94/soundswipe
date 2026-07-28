#!/usr/bin/env python3
import datetime, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

SB_URL='https://tfoilkjyuzayxcedcmwo.supabase.co'
SB_KEY='sb_publishable_F4kidHmHAymbnwOWcK22dw_NkbNrNT4'
SB_HEADERS={'apikey':SB_KEY,'Authorization':'Bearer '+SB_KEY,'Content-Type':'application/json'}
API='https://freesound.org/apiv2/search/text/'
KEY=os.environ.get('FREESOUND_API_KEY','').strip()
LIMIT=int(os.environ.get('LIMIT_PER_QUERY') or '8')
DRY=(os.environ.get('DRY_RUN','false').lower()=='true')
MAX_ROWS=int(os.environ.get('MAX_ROWS') or '800')
if not KEY:
    raise SystemExit('Missing GitHub secret FREESOUND_API_KEY')

# 50 non-sample prompt-DNA tokens. Historical/public-domain sample choice stays in the separate Sample tab.
# Each token has broad Freesound queries because precise genre-prompt phrases return too few CC0 results.
TOKENS=[
 # rhythm / drums, 8
 ('dna_rhythm','drum_pocket','tight boom-bap drums',['boom bap drums','hip hop drum loop','drum break loop'],2,14),
 ('dna_rhythm','drum_pocket','uk garage snare swing',['garage drum loop','2 step drum loop','shuffle drum loop'],2,14),
 ('dna_rhythm','hi_hat_feel','crisp swung hi-hats',['hi hat loop','swing hi hat','closed hi hat rhythm'],0.5,8),
 ('dna_rhythm','snare_feel','dry snare crack',['dry snare','snare hit','snare drum one shot'],0.1,4),
 ('dna_rhythm','kick_feel','soft deep kick',['deep kick','soft kick drum','low kick one shot'],0.1,4),
 ('dna_rhythm','percussion','organic hand percussion',['hand percussion loop','shaker loop','tambourine loop'],1,12),
 ('dna_rhythm','groove_body','lazy off-grid groove',['lazy drum loop','lofi drums loop','offbeat rhythm loop'],2,14),
 ('dna_rhythm','drum_density','minimal sparse drums',['minimal drum loop','sparse beat','simple drum loop'],2,14),
 # bass, 6
 ('dna_bass','bass_type','warm upright bass',['upright bass loop','double bass loop','jazz bass loop'],1,14),
 ('dna_bass','bass_type','round electric bass',['electric bass loop','bass guitar loop','funk bass loop'],1,14),
 ('dna_bass','bass_type','clean sub bass',['sub bass','sine bass','808 bass'],0.2,8),
 ('dna_bass','bass_motion','syncopated bass bounce',['syncopated bass','bouncy bass loop','bass groove loop'],1,14),
 ('dna_bass','bass_texture','distorted bass grit',['distorted bass','dirty bass','fuzz bass'],0.5,10),
 ('dna_bass','bass_space','short bass stab',['bass stab','short bass hit','bass one shot'],0.1,5),
 # vocal, 7
 ('dna_vocal','vocal_texture','intimate dry vocal',['dry vocal','spoken vocal','close voice'],0.5,12),
 ('dna_vocal','vocal_texture','breathy soft vocal',['breathy vocal','soft vocal','female vocal phrase'],0.5,12),
 ('dna_vocal','vocal_texture','gritty rap adlib',['rap vocal','vocal adlib','male vocal shout'],0.3,10),
 ('dna_vocal','vocal_layering','call and response vocals',['call response vocal','vocal response','group vocal'],0.8,14),
 ('dna_vocal','vocal_distance','ghostly distant vocal',['distant vocal','ghost vocal','reverb vocal'],1,15),
 ('dna_vocal','vocal_chop','vocal chop texture',['vocal chop','chopped vocal','vocal sample'],0.3,10),
 ('dna_vocal','human_noise','breath and mouth noise',['breath sound','mouth noise','human breath'],0.2,8),
 # hook / lead, 7
 ('dna_hook','hook_instrument','chopped brass hook',['brass stab','trumpet riff','horn loop'],0.3,10),
 ('dna_hook','hook_instrument','muted guitar riff',['muted guitar riff','guitar riff loop','clean guitar loop'],1,14),
 ('dna_hook','hook_instrument','felt piano motif',['piano motif','soft piano loop','felt piano'],1,14),
 ('dna_hook','hook_instrument','vocal chop lead',['vocal lead loop','vocal chop melody','voice melody'],0.5,12),
 ('dna_hook','hook_instrument','synth pluck motif',['synth pluck','pluck melody','synth riff'],0.5,12),
 ('dna_hook','motif_shape','short repeated motif',['short melody loop','repeated motif','music box loop'],0.5,12),
 ('dna_hook','motif_shape','one-note memorable stab',['music stab','single note hit','orchestral stab'],0.1,5),
 # chord / harmony, 6
 ('dna_chord','chord_instrument','warm rhodes chords',['rhodes chords','electric piano loop','warm keys loop'],1,14),
 ('dna_chord','chord_instrument','minor piano loop',['minor piano loop','dark piano loop','sad piano loop'],1,14),
 ('dna_chord','chord_instrument','dark guitar chords',['dark guitar chords','guitar chord loop','minor guitar loop'],1,14),
 ('dna_chord','harmony_mood','bittersweet harmony',['bittersweet loop','emotional chord loop','sad hopeful music'],1,14),
 ('dna_chord','chord_rhythm','syncopated chord stabs',['chord stabs','syncopated chords','stab loop'],0.5,10),
 ('dna_chord','pad_floor','soft ambient pad',['ambient pad','soft pad loop','warm drone'],2,20),
 # mix / texture / space, 8
 ('dna_mix','mix_texture','tape saturation',['tape noise','tape hiss','cassette noise'],1,20),
 ('dna_mix','noise_layer','vinyl crackle',['vinyl crackle','record crackle','vinyl noise'],1,20),
 ('dna_mix','reverb_space','dry close mic',['dry sound','close mic','room tone close'],0.5,12),
 ('dna_mix','reverb_space','small room ambience',['small room ambience','room tone','indoor ambience'],2,25),
 ('dna_mix','stereo_width','wide stereo ambience',['wide ambience','stereo ambience','spacious pad'],2,25),
 ('dna_mix','lofi_texture','lofi dusty texture',['lofi texture','dusty texture','old tape loop'],1,18),
 ('dna_mix','transient_feel','crisp transient hits',['click hit','crisp percussion','sharp hit'],0.1,5),
 ('dna_mix','background_motion','subtle moving texture',['moving texture','background texture','evolving ambience'],2,25),
 # mood / scene, 5
 ('dna_mood','mood_scene','late night city',['night city ambience','city night','urban ambience'],2,25),
 ('dna_mood','mood_scene','smoky club room',['club ambience','bar ambience','crowd room'],2,25),
 ('dna_mood','mood_scene','rainy street',['rain street','rain ambience','wet street'],2,25),
 ('dna_mood','emotional_direction','emotional uplift',['uplifting loop','hopeful music loop','emotional melody'],1,15),
 ('dna_mood','emotional_direction','lonely but warm',['lonely ambience','warm sad music','melancholic loop'],1,18),
 # wild / contrast, 3
 ('dna_wild','wild_texture','strange attractive texture',['strange texture','weird sound','experimental texture'],0.5,18),
 ('dna_wild','wild_texture','mechanical emotional pulse',['mechanical rhythm','machine pulse','industrial loop'],0.5,15),
 ('dna_wild','wild_texture','broken machine rhythm',['broken rhythm','glitch loop','broken machine'],0.5,15),
]
assert len(TOKENS)==50, len(TOKENS)

def slug(s):
    return re.sub(r'[^a-z0-9]+','_',s.lower()).strip('_')[:70]

def req_json(url, headers=None, data=None, method='GET', timeout=60):
    req=urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body=r.read().decode('utf-8')
        return json.loads(body) if body else None

def is_cc0(item):
    lic=(item.get('license') or '').lower()
    return ('creative commons 0' in lic) or ('publicdomain/zero' in lic) or ('zero/1.0' in lic) or ('cc0' in lic)

def search(query, lo, hi, page=1):
    params={
        'query': query,
        'filter': f'license:"Creative Commons 0" duration:[{lo} TO {hi}]',
        'fields': 'id,name,tags,description,license,username,duration,previews,url,avg_rating,num_ratings,created',
        'sort': 'score',
        'page_size': str(LIMIT),
        'page': str(page),
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
        'test_design': '50_non_sample_prompt_dna_tokens_multi_query',
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

batch='freesound_dna50_'+datetime.datetime.now().strftime('%Y%m%d')
rows=[]
per_token_counts={}
seen=set()
for category, axis, token, queries, lo, hi in TOKENS:
    token_rows=[]
    for query in queries:
        if len(rows) >= MAX_ROWS:
            break
        print(f'SEARCH {category} | {axis} | {token} | {query}')
        try:
            data=search(query, lo, hi)
            results=data.get('results') or []
        except urllib.error.HTTPError as e:
            print('HTTP_ERROR', e.code, e.read().decode('utf-8')[:300])
            continue
        cc0=[x for x in results if is_cc0(x)]
        print('  results', len(results), 'cc0', len(cc0))
        for x in cc0:
            row=make_row(x, category, axis, token, query, batch)
            if row['id'] not in seen:
                seen.add(row['id'])
                rows.append(row)
                token_rows.append(row)
                if len(rows) >= MAX_ROWS:
                    break
        time.sleep(0.22)
    per_token_counts[token]=len(token_rows)
    if len(rows) >= MAX_ROWS:
        break

print(json.dumps({'candidate_rows':len(rows),'tokens':len(TOKENS),'dry_run':DRY,'batch':batch,'per_token_counts':per_token_counts}, ensure_ascii=False, indent=2))
if DRY:
    print(json.dumps(rows[:8], ensure_ascii=False, indent=2))
    sys.exit(0)
inserted=[]
for i in range(0,len(rows),100):
    inserted.extend(upsert(rows[i:i+100]))
print(json.dumps({'inserted_or_updated':len(inserted),'batch':batch}, indent=2))
