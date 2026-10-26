"""LPG T-Box 지표 계산. 사용법:
python3 schema_metrics.py <schema.json> [--generic Concept] [--hubs Event,Rule]
                          [--meta name,context,definition,provenance,text]
                          [--full-labels 250] [--full-pairs 331] [--contexts 26]

--generic, --hubs에 쓴 라벨 이름은 예시다. 모델마다 다르므로 평가 0단계에서 정해 넘긴다.
  범용 라벨: 특정 도메인 의미 없이 여러 종류의 개체를 담는 라벨
  허브: 여러 도메인 라벨에 가로로 연결되는 라벨(이벤트, 규칙, 로그 등)
둘 다 지정하지 않으면 '도메인 정보가 없는 관계' 계열 지표는 계산하지 않고 후보만 출력한다.
비교하는 모델에는 같은 기준으로 지정한다.
--meta: 도메인 속성에서 제외할 메타 속성 이름(기본값은 워크숍 모델의 관례).
"""
import argparse, json
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("schema")
ap.add_argument("--hubs", default="")
ap.add_argument("--generic", default="")
ap.add_argument("--meta", default="name,context,definition,provenance,text")
ap.add_argument("--full-labels", type=int)
ap.add_argument("--full-pairs", type=int)
ap.add_argument("--contexts", type=int)
a = ap.parse_args()


def names(text):
    return {x.strip() for x in text.split(",") if x.strip()}


tb = json.load(open(a.schema, encoding="utf-8"))["tbox"]
ents, rels = tb["entities"], tb["relations"]
hubs, generic, META = names(a.hubs), names(a.generic), names(a.meta)
unknown = (hubs | generic) - set(ents)
if unknown:
    ap.error(f"모델에 없는 라벨: {sorted(unknown)} (모델의 라벨: {sorted(ents)})")
if hubs & generic:
    ap.error(f"범용 라벨과 허브에 함께 지정된 라벨: {sorted(hubs & generic)}")
special = hubs | generic

base = {r.get("base_type", k) for k, r in rels.items()}
pairs = [(r["src"], r["dst"], r.get("base_type", k), r.get("cardinality")) for k, r in rels.items()]
domain = [e for e in ents if e not in special]
print(f"노드 테이블(라벨): {len(ents)}  관계 종류: {len(base)}  노드 쌍: {len(pairs)}")

# 범용 라벨, 허브 후보: 이름이 아니라 구조로 찾는다. 최종 판단은 평가자가 한다.
cands = defaultdict(list)
with_ctx = [e for e in ents if ents[e].get("bounded_context")]
if with_ctx and len(with_ctx) < len(ents):
    for e in ents:
        if e not in with_ctx:
            cands[e].append("bounded_context 없음")
spread = defaultdict(lambda: defaultdict(set))
for s, d, b, _ in pairs:
    spread[(b, "출발")][s].add(d)
    spread[(b, "도착")][d].add(s)
for (b, side), by_label in spread.items():
    for label, others in by_label.items():
        if len(others) >= 3:
            cands[label].append(f"{b} 관계가 서로 다른 라벨 {len(others)}개로 퍼짐({side})")
for label, why in cands.items():
    if label not in special:
        print(f"[후보] 범용 라벨 또는 허브일 수 있는 라벨 {label}: {'; '.join(why)}")

if not special:
    print("[안내] --generic, --hubs가 없어 '도메인 정보가 없는 관계', 허브 의존도, 도메인 라벨 지표는 계산하지 않았다."
          " 0단계에서 범용 라벨과 허브를 정한 뒤 지정해 다시 실행한다.")
else:
    hub_adj = [p for p in pairs if p[0] in hubs or p[1] in hubs]
    no_hub = [p for p in pairs if p not in hub_adj]
    gen_both = [p for p in no_hub if p[0] in generic and p[1] in generic]
    gen_one = [p for p in no_hub if (p[0] in generic) != (p[1] in generic)]
    total = len(hub_adj) + len(gen_both) + len(gen_one)
    print(f"도메인 정보가 없는 관계(양 끝 중 한쪽이라도 범용 라벨이나 허브): {total}/{len(pairs)}")
    print(f"  허브 경유(=허브 의존도): {len(hub_adj)}/{len(pairs)}"
          f"  범용 라벨끼리: {len(gen_both)}  범용 라벨이 한쪽 끝: {len(gen_one)}")
    if domain:
        dd = [(s, d, b) for s, d, b, _ in pairs if s in domain and d in domain]
        linked = {x for s, d, _ in dd for x in (s, d)}
        print(f"도메인 라벨: {len(domain)}")
        print(f"도메인 라벨 간 직접 관계: {len(dd)} {dd}")
        iso = [e for e in domain if e not in linked]
        print(f"직접 관계가 없는 도메인 라벨: {len(iso)}/{len(domain)} {iso}")
        noattr = [e for e in domain if not set(ents[e].get("properties", {})) - META]
        print(f"도메인 속성이 없는 라벨: {len(noattr)}/{len(domain)} {noattr}")
        ctx = {e: ents[e].get("bounded_context") for e in ents}
        cross = defaultdict(int)
        for s, d, *_ in pairs:
            if ctx.get(s) != ctx.get(d):
                cross[tuple(sorted((str(ctx.get(s)), str(ctx.get(d)))))] += 1
        print(f"컨텍스트 간 연결(쌍 수): {dict(cross)}")

# 공통 린트
for k, e in ents.items():
    if e.get("label") and e["label"] != k:
        print(f"[린트] 키/라벨 불일치: {k} vs '{e['label']}'")
enum_props = defaultdict(dict)
for k, e in ents.items():
    for p, t in e.get("properties", {}).items():
        enum_props[p][k] = "enum" if isinstance(t, dict) and "enum" in t else "plain"
for p, m in enum_props.items():
    if len(set(m.values())) > 1:
        print(f"[린트] 열거형 불일치: {p} {m}")
for k, e in ents.items():
    ids = [p for p in e.get("properties", {}) if p.endswith("_id")]
    if ids and e.get("primary_key") not in ids:
        print(f"[린트] 기본 키({e.get('primary_key')})와 ID 속성 {ids} 공존: {k}")
for s, d, b, c in pairs:
    if c in ("N:1", "1:N", "1:1") and (s in generic or d in generic):
        print(f"[린트] 범용 라벨에 걸린 cardinality 제약: {b} {s}->{d} {c}")
mix = {r.get("base_type") is not None for r in rels.values()}
if len(mix) > 1:
    print("[린트] base_type 표기가 일부 관계에만 있음")
if a.full_labels and a.contexts:
    print(f"컨텍스트당 스키마 증가(전체 기준): 라벨 {a.full_labels / a.contexts:.1f}"
          + (f", 쌍 {a.full_pairs / a.contexts:.1f}" if a.full_pairs else ""))
